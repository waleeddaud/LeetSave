from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from api.deps import get_current_user
from config import get_settings
from database import get_db
from models.user import User
from schemas.auth import MeResponse
from services.auth import create_session_token, revoke_session, store_github_token
from services.github import exchange_oauth_code, fetch_github_user, upsert_user_from_github

router = APIRouter()
settings = get_settings()


@router.get("/github/login")
async def github_login():
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "repo user:email",
    }
    url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    try:
        token_data = await exchange_oauth_code(code)
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse(f"{settings.backend_base_url}/onboarding/error?reason=missing_token")

        profile = await fetch_github_user(access_token)
        user = upsert_user_from_github(db, profile)
        store_github_token(db, user, access_token, token_data.get("scope"))
        session_token = create_session_token(db, user)

        success_url = settings.extension_success_url
        return RedirectResponse(f"{success_url}#token={session_token}")
    except Exception:
        return RedirectResponse(f"{settings.backend_base_url}/onboarding/error?reason=auth_failed")


@router.get("/me", response_model=MeResponse)
def get_me(user: User = Depends(get_current_user)):
    connection = user.github_connection
    return MeResponse(
        id=str(user.id),
        github_id=user.github_id,
        github_username=user.github_username,
        email=user.email,
        avatar_url=user.avatar_url,
        github_connected=bool(connection and connection.access_token_encrypted),
        repo_full_name=connection.repo_full_name if connection else None,
        repo_name=connection.repo_name if connection else None,
    )


@router.post("/logout")
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        revoke_session(db, token)
    return {"status": "ok", "message": "Logged out"}
