# LeetSave

LeetSave is a **Chrome extension + FastAPI backend project** designed to help users automatically **push their LeetCode submissions to GitHub**, optionally with AI-generated explanations. It’s a full-stack project that combines browser extension development, backend API design, GitHub OAuth, and AI integration.  

---

## **Project Idea**

LeetSave allows a user to:  
1. **Log in with GitHub** via OAuth.  
2. **Intercept code submissions** on LeetCode directly from the browser.  
3. **Send the submission** securely to a FastAPI backend.  
4. **Store the GitHub access token** safely on the backend.  
5. **Push code** to the user’s GitHub repository.  
6. Optionally, generate **AI-powered explanations** for the code.  

This ensures that sensitive information like GitHub access tokens **never leaves the backend**, while the user enjoys a seamless workflow from LeetCode → GitHub.  

---

## **File Structure**
LeetSave/
├── app/                     # FastAPI backend
│   ├── main.py              # FastAPI app with endpoints
│   ├── utils.py             # Helper functions (e.g., fetch GitHub user info)
│   ├── .env                 # Environment variables (client IDs, secrets, etc.)
│   └── requirements.txt     # Python dependencies
│
├── Extension/               # Chrome extension
│   ├── manifest.json        # Extension manifest file
│   ├── popup.html           # Welcome / login page
│   ├── popup.js             # Handles login and OAuth flow
│   ├── background.js        # Intercepts LeetCode submissions
│   └── other_assets/        # Optional CSS, icons, etc.
│
└── README.md                # Project overview and setup instructions


---

## **Setup Instructions**

### 1. Backend (FastAPI)
1. Create a Python virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    .venv\Scripts\activate     # Windows
    ```
2. Install dependencies:
    ```bash
    pip install -r app/requirements.txt
    ```
3. Set environment variables in `.env`:
    ```
    GITHUB_CLIENT_ID=<your_client_id>
    GITHUB_CLIENT_SECRET=<your_client_secret>
    CALLBACK_URL=http://localhost:8000/github/callback
    CHROME_EXTENSION_ID=<your_extension_id>
    SECRET_KEY=<your_jwt_secret>
    ```
4. Run FastAPI backend:
    ```bash
    uvicorn app.main:app --reload
    ```

### 2. Chrome Extension
1. Open Chrome → `chrome://extensions/`.  
2. Enable **Developer Mode**.  
3. Click **Load unpacked** and select the `Extension/` folder.  
4. Click the extension icon to see the **welcome page**.  
5. Click **Login with GitHub** to authenticate via OAuth.  

---

## **Usage Flow**

1. User installs the Chrome extension.  
2. The extension shows a **welcome popup** with a login button.  
3. The user logs in via GitHub OAuth.  
4. FastAPI backend stores the GitHub access token securely and returns a **custom token**.  
5. User submits code on LeetCode.  
6. Extension intercepts the submission, sends it to the backend with the custom token.  
7. Backend pushes the code to the user’s GitHub repository.  
8. Optionally, AI-generated explanations are added as comments or separate files.  

---

## **Technologies Used**

- **Frontend**: Chrome Extension (HTML, JS)  
- **Backend**: FastAPI (Python)  
- **Authentication**: GitHub OAuth  
- **Database**: Any (PostgreSQL, SQLite, etc.) to store tokens & submissions  
- **AI Integration**: Optional (OpenAI / Gemini APIs)  
- **Security**: JWT custom tokens, CORS handling  

---

## **Notes**

- The GitHub client ID is public; sensitive access tokens are never exposed to the extension.  
- Custom tokens are short-lived or opaque and are used to authenticate requests between the extension and backend.  
- AI explanations are optional and can be disabled.  
