# LeetSave

LeetSave is a Chrome extension and FastAPI backend that syncs your **accepted LeetCode solutions** to a single GitHub repository, with optional AI-generated explanations.

## What it does

1. Sign up / log in with GitHub (extension popup or onboarding page).
2. Solve LeetCode problems normally in the browser.
3. When a submission result becomes **Accepted**, the extension sends your code to the backend.
4. The backend generates an explanation (OpenAI or Gemini via LangChain), then commits solution files to one repo per user.

GitHub OAuth tokens stay on the backend. The extension only stores a backend-issued session JWT.

---

## Project structure

```text
.
├── app/                    # FastAPI backend
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   ├── services/
│   ├── api/
│   ├── static/             # onboarding pages
│   ├── alembic/
│   └── requirements.txt
├── Extension/              # Chrome MV3 extension
├── docker-compose.yml      # PostgreSQL
└── readme.md
```

---

## Local setup

### 1. PostgreSQL

```bash
docker compose up -d
```

Default connection:

`postgresql+psycopg://leetsave:leetsave@localhost:5432/leetcode_github_sync`

### 2. Backend

```bash
cd app
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
python generate_secret.py     # generate JWT + encryption keys
```

Fill in `.env`:

- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` from a GitHub OAuth App
- `GITHUB_REDIRECT_URI=http://localhost:8000/api/v1/auth/github/callback`
- `CHROME_EXTENSION_ID` from `chrome://extensions` after loading the extension
- `TOKEN_ENCRYPTION_KEY` and `JWT_SECRET_KEY`
- `OPENAI_API_KEY` or `GEMINI_API_KEY` depending on `LLM_PROVIDER`

Run migrations and start the API:

```bash
alembic upgrade head
uvicorn main:app --reload
```

Health check: [http://localhost:8000/health](http://localhost:8000/health)

Onboarding page: [http://localhost:8000/onboarding](http://localhost:8000/onboarding)

### 3. GitHub OAuth App (not GitHub App)

Create an **OAuth App** at https://github.com/settings/developers → **OAuth Apps** → New OAuth App.

Do **not** use a GitHub App for local setup — GitHub Apps cause `Resource not accessible by integration` errors with this project.

Use:

- Homepage URL: `http://localhost:8000`
- Callback URL: `http://localhost:8000/api/v1/auth/github/callback`

Copy Client ID and Client Secret into `app/.env`.

If you previously authorized a GitHub App version of LeetSave, revoke **both** entries at https://github.com/settings/applications before logging in again.

### 4. Chrome extension

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select the `Extension/` folder
4. Copy the extension ID into `CHROME_EXTENSION_ID` and `CORS_ALLOWED_ORIGINS` in `.env`
5. Restart the backend after updating CORS

Open the extension popup → **Continue with GitHub** → authorize → success page stores the backend session token.

### 5. Test the flow

1. Log in through the extension popup.
2. Open a LeetCode problem page, e.g. `https://leetcode.com/problems/two-sum/`
3. Submit your solution manually.
4. When the UI shows **Accepted**, the extension sends the payload to `POST /api/v1/submissions/leetcode`.
5. Check your `leetcode-problems` repo on GitHub for:

```text
easy/two-sum/solution.py
easy/two-sum/explanation.md
easy/two-sum/metadata.json
```

---

## API overview

| Endpoint | Description |
|---|---|
| `GET /health` | Health check |
| `GET /api/v1/auth/github/login` | Start GitHub OAuth |
| `GET /api/v1/auth/github/callback` | OAuth callback |
| `GET /api/v1/me` | Current user (Bearer token) |
| `POST /api/v1/auth/logout` | Revoke session |
| `POST /api/v1/submissions/leetcode` | Sync accepted submission |
| `GET /api/v1/submissions` | Submission history |
| `POST /api/v1/github/ensure-repo` | Create/use single repo |
| `POST /api/v1/github/sync/{id}` | Retry failed GitHub push |

---

## LLM provider switch

Set in `.env` only:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=...

# or

LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-1.5-flash
GEMINI_API_KEY=...
```

If explanation generation fails, the backend still saves the submission and uses a fallback `explanation.md`.

---

## Tests

```bash
cd app
pytest
```

---

## Safety notes

- The extension only runs on `leetcode.com/problems/*`.
- It observes UI state for Accepted results; it does not modify LeetCode requests.
- It does not auto-submit solutions or collect LeetCode credentials.
- Duplicate accepted solutions are deduplicated by `user + problem_slug + language + code_hash`.

---

## Troubleshooting

- **OAuth blocked / `ERR_BLOCKED_BY_CLIENT`**: the backend now redirects to `http://localhost:8000/onboarding/success#token=...` and the extension captures the token from that tab. Reload the extension and restart the backend after changing `.env`.
- **CORS errors**: include `chrome-extension://<id>` in `CORS_ALLOWED_ORIGINS`.
- **GitHub push failed / 403 Forbidden**: your GitHub token is missing `public_repo` or `repo` scope. Revoke LeetSave at [GitHub Applications](https://github.com/settings/applications), log out from the extension, log in again, and approve repository access. Then retry with `POST /api/v1/github/sync/{submission_id}`.
- **Database errors**: ensure Docker Postgres is running and migrations are applied.
