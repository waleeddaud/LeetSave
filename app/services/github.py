import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from config import get_settings
from models.github_connection import UserGitHubConnection
from models.submission import LeetCodeSubmission
from models.user import User
from services.encryption import decrypt_token

settings = get_settings()

LANGUAGE_EXTENSIONS = {
    "python": "solution.py",
    "python3": "solution.py",
    "cpp": "solution.cpp",
    "c++": "solution.cpp",
    "java": "Solution.java",
    "javascript": "solution.js",
    "typescript": "solution.ts",
    "go": "solution.go",
    "rust": "solution.rs",
    "c": "solution.c",
    "csharp": "Solution.cs",
    "c#": "Solution.cs",
}


def solution_filename(language: str) -> str:
    return LANGUAGE_EXTENSIONS.get(language.lower().strip(), "solution.txt")


def difficulty_folder(difficulty: str | None) -> str:
    if not difficulty:
        return "unknown"
    normalized = difficulty.lower().strip()
    if normalized in {"easy", "medium", "hard"}:
        return normalized
    return "unknown"


def compute_code_hash(code: str, language: str, problem_slug: str) -> str:
    payload = f"{code}{language}{problem_slug}"
    return hashlib.sha256(payload.encode()).hexdigest()


def github_token_kind(access_token: str) -> str:
    if access_token.startswith("ghu_"):
        return "github_app_user"
    if access_token.startswith("gho_"):
        return "oauth_app"
    if access_token.startswith("github_pat_"):
        return "fine_grained_pat"
    return "classic_oauth"


def _github_headers(access_token: str) -> dict[str, str]:
    if access_token.startswith(("gho_", "ghu_")):
        authorization = f"Bearer {access_token}"
    else:
        authorization = f"token {access_token}"
    return {
        "Authorization": authorization,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_access_token(connection: UserGitHubConnection) -> str:
    if not connection.access_token_encrypted:
        raise ValueError("GitHub access token is missing for user")
    return decrypt_token(connection.access_token_encrypted)


def parse_github_scopes(scope_value: str | None) -> set[str]:
    if not scope_value:
        return set()
    normalized = scope_value.replace(",", " ")
    return {part.strip() for part in normalized.split() if part.strip()}


def has_repo_scope(scopes: set[str]) -> bool:
    return bool(scopes & {"public_repo", "repo"})


async def fetch_github_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.github.com/user",
            headers=_github_headers(access_token),
        )
        response.raise_for_status()
        return response.json()


async def inspect_github_token(
    access_token: str, token_scope: str | None = None
) -> dict[str, Any]:
    kind = github_token_kind(access_token)
    scopes = parse_github_scopes(token_scope)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.github.com/user",
            headers=_github_headers(access_token),
        )
        response.raise_for_status()
        header_scopes = parse_github_scopes(response.headers.get("X-OAuth-Scopes", ""))
        accepted_scopes = parse_github_scopes(response.headers.get("X-Accepted-OAuth-Scopes", ""))

    if not scopes:
        scopes = header_scopes

    return {
        "kind": kind,
        "scopes": scopes,
        "header_scopes": header_scopes,
        "accepted_scopes": accepted_scopes,
        "login": response.json().get("login"),
    }


async def resolve_granted_scopes(access_token: str, token_scope: str | None) -> set[str]:
    inspection = await inspect_github_token(access_token, token_scope)
    return inspection["scopes"]


def validate_github_token_for_repo_sync(
    access_token: str, granted_scopes: set[str], client_id_suffix: str
) -> str | None:
    kind = github_token_kind(access_token)
    if kind == "github_app_user":
        return (
            "GitHub returned a GitHub App user token (ghu_), not an OAuth App token. "
            f"Your backend is using client_id ending in …{client_id_suffix}. "
            "Copy the Client ID/Secret from your leetBridge OAuth App (Developer settings → OAuth Apps, not GitHub Apps) "
            "into app/.env, restart uvicorn, revoke all LeetSave authorizations at "
            "https://github.com/settings/applications, then log in again."
        )

    if granted_scopes and not has_repo_scope(granted_scopes):
        return (
            f"GitHub granted scopes {sorted(granted_scopes)} but LeetSave needs public_repo or repo. "
            "Revoke the app at https://github.com/settings/applications and authorize again."
        )

    if not granted_scopes:
        return (
            "GitHub returned no OAuth scopes (stored as 'unknown'). "
            f"Backend client_id ends with …{client_id_suffix}. "
            "This usually means .env still points at a GitHub App or an old OAuth app, not leetBridge. "
            "Update GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in app/.env to match leetBridge exactly, "
            "restart the backend, revoke old authorizations, and log in again."
        )

    return None


async def exchange_oauth_code(code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            description = payload.get("error_description") or payload.get("error")
            raise ValueError(f"GitHub token exchange failed: {description}")
        return payload


def upsert_user_from_github(db: Session, profile: dict[str, Any]) -> User:
    github_id = str(profile["id"])
    user = db.query(User).filter(User.github_id == github_id).first()
    if user:
        user.github_username = profile.get("login", user.github_username)
        user.email = profile.get("email")
        user.avatar_url = profile.get("avatar_url")
    else:
        user = User(
            github_id=github_id,
            github_username=profile.get("login", ""),
            email=profile.get("email"),
            avatar_url=profile.get("avatar_url"),
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _github_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"

    message = payload.get("message", "")
    errors = payload.get("errors")
    if errors:
        return f"{message} ({errors})"
    return message or f"HTTP {response.status_code}"


async def ensure_repo(db: Session, user: User) -> UserGitHubConnection:
    connection = user.github_connection
    if not connection:
        raise ValueError("GitHub connection not found for user")

    access_token = get_access_token(connection)
    repo_name = connection.repo_name or settings.github_default_repo_name
    branch = connection.default_branch or settings.github_default_branch

    async with httpx.AsyncClient(timeout=30) as client:
        profile = await fetch_github_user(access_token)
        owner = profile["login"]

        get_resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo_name}",
            headers=_github_headers(access_token),
        )

        if get_resp.status_code == 404:
            create_resp = await client.post(
                "https://api.github.com/user/repos",
                headers=_github_headers(access_token),
                json={
                    "name": repo_name,
                    "description": "LeetCode accepted solutions synced by LeetSave",
                    "private": False,
                    "auto_init": True,
                },
            )
            if create_resp.status_code == 403:
                scope = connection.scope or "unknown"
                detail = _github_error_detail(create_resp)
                token_kind = github_token_kind(access_token)
                raise ValueError(
                    "GitHub denied repository creation (403). "
                    f"Stored scope: '{scope}', token kind: '{token_kind}'. "
                    f"Backend client_id ends with …{settings.github_client_id_suffix}. "
                    "LeetSave needs a GitHub OAuth App (Developer settings → OAuth Apps), not a GitHub App. "
                    "Put leetBridge Client ID/Secret in app/.env, restart uvicorn, revoke all old authorizations "
                    "at https://github.com/settings/applications, log out from the extension, and log in again. "
                    f"GitHub says: {detail}"
                )
            create_resp.raise_for_status()
            repo = create_resp.json()
        elif get_resp.status_code == 200:
            repo = get_resp.json()
        else:
            get_resp.raise_for_status()
            repo = get_resp.json()

        connection.repo_name = repo["name"]
        connection.repo_full_name = repo["full_name"]
        connection.repo_id = str(repo["id"])
        connection.default_branch = repo.get("default_branch", branch)
        db.commit()
        db.refresh(connection)
        return connection


async def _get_file_sha(
    client: httpx.AsyncClient, access_token: str, repo_full_name: str, path: str, branch: str
) -> str | None:
    response = await client.get(
        f"https://api.github.com/repos/{repo_full_name}/contents/{path}",
        headers=_github_headers(access_token),
        params={"ref": branch},
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json().get("sha")


async def _put_file(
    client: httpx.AsyncClient,
    access_token: str,
    repo_full_name: str,
    path: str,
    content: str,
    message: str,
    branch: str,
    sha: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message": message,
        "content": content,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    response = await client.put(
        f"https://api.github.com/repos/{repo_full_name}/contents/{path}",
        headers=_github_headers(access_token),
        json=payload,
    )
    response.raise_for_status()
    return response.json()


async def ensure_readme(
    client: httpx.AsyncClient,
    access_token: str,
    repo_full_name: str,
    branch: str,
    submission: LeetCodeSubmission,
) -> None:
    path = "README.md"
    existing_sha = await _get_file_sha(client, access_token, repo_full_name, path, branch)
    row = (
        f"| {submission.problem_title} | {submission.difficulty or 'unknown'} | "
        f"{submission.language} | `{difficulty_folder(submission.difficulty)}/{submission.problem_slug}/` |"
    )

    if existing_sha:
        get_resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/{path}",
            headers=_github_headers(access_token),
            params={"ref": branch},
        )
        get_resp.raise_for_status()
        import base64

        current = base64.b64decode(get_resp.json()["content"]).decode()
        if submission.problem_slug in current:
            return
        content = current.rstrip() + "\n" + row + "\n"
        header = "# LeetCode Solutions\n\n| Problem | Difficulty | Language | Path |\n|---|---|---|---|\n"
        if "| Problem |" not in current:
            content = header + row + "\n"
        else:
            content = current.rstrip() + "\n" + row + "\n"
    else:
        content = (
            "# LeetCode Solutions\n\n"
            "Accepted LeetCode solutions synced automatically by LeetSave.\n\n"
            "| Problem | Difficulty | Language | Path |\n|---|---|---|---|\n"
            f"{row}\n"
        )

    import base64

    encoded = base64.b64encode(content.encode()).decode()
    await _put_file(
        client,
        access_token,
        repo_full_name,
        path,
        encoded,
        "Update LeetCode solutions index",
        branch,
        existing_sha,
    )


async def push_submission_files(db: Session, user: User, submission: LeetCodeSubmission) -> str:
    connection = await ensure_repo(db, user)
    access_token = get_access_token(connection)
    repo_full_name = connection.repo_full_name
    branch = connection.default_branch or settings.github_default_branch

    folder = f"{difficulty_folder(submission.difficulty)}/{submission.problem_slug}"
    code_path = f"{folder}/{solution_filename(submission.language)}"
    explanation_path = f"{folder}/explanation.md"
    metadata_path = f"{folder}/metadata.json"

    metadata = {
        "problem_title": submission.problem_title,
        "problem_slug": submission.problem_slug,
        "difficulty": submission.difficulty,
        "language": submission.language,
        "leetcode_url": submission.leetcode_url,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }

    import base64

    commit_message = (
        f"Add LeetCode solution: {submission.problem_title} [{submission.language}]"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        code_sha = await _get_file_sha(client, access_token, repo_full_name, code_path, branch)
        explanation_sha = await _get_file_sha(
            client, access_token, repo_full_name, explanation_path, branch
        )
        metadata_sha = await _get_file_sha(client, access_token, repo_full_name, metadata_path, branch)

        code_result = await _put_file(
            client,
            access_token,
            repo_full_name,
            code_path,
            base64.b64encode(submission.code_text.encode()).decode(),
            commit_message,
            branch,
            code_sha,
        )
        await _put_file(
            client,
            access_token,
            repo_full_name,
            explanation_path,
            base64.b64encode((submission.llm_explanation or "").encode()).decode(),
            commit_message,
            branch,
            explanation_sha,
        )
        await _put_file(
            client,
            access_token,
            repo_full_name,
            metadata_path,
            base64.b64encode(json.dumps(metadata, indent=2).encode()).decode(),
            commit_message,
            branch,
            metadata_sha,
        )
        await ensure_readme(client, access_token, repo_full_name, branch, submission)

    commit_sha = code_result.get("commit", {}).get("sha", "")
    submission.github_path_code = code_path
    submission.github_path_explanation = explanation_path
    submission.github_commit_sha = commit_sha
    submission.pushed_at = datetime.now(timezone.utc)
    submission.sync_status = "synced"
    db.commit()
    return commit_sha
