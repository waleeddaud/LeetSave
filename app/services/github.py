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


def _github_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_access_token(connection: UserGitHubConnection) -> str:
    if not connection.access_token_encrypted:
        raise ValueError("GitHub access token is missing for user")
    return decrypt_token(connection.access_token_encrypted)


async def fetch_github_user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.github.com/user",
            headers=_github_headers(access_token),
        )
        response.raise_for_status()
        return response.json()


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
        return response.json()


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
