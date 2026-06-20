from urllib.parse import quote, urlencode
import logging

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from api.deps import get_current_user
from config import get_settings
from database import get_db
from models.user import User
from schemas.auth import MeResponse
from services.auth import create_session_token, revoke_session, store_github_token
from services.github import (
    exchange_oauth_code,
    fetch_github_user,
    inspect_github_token,
    upsert_user_from_github,
    validate_github_token_for_repo_sync,
)

router = APIRouter()
settings = get_settings()
logger = logging.getLogger("leetsave")


@router.get("/github/login")
async def github_login():
    logger.info("Auth → GitHub (app …%s)", settings.github_client_id_suffix)
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": settings.github_oauth_scope_normalized,
    }
    url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url, status_code=302)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    try:
        token_data = await exchange_oauth_code(code)
        access_token = token_data.get("access_token")
        token_scope = token_data.get("scope", "")
        if not access_token:
            error = token_data.get("error", "missing_token")
            logger.warning(
                "Auth FAIL no token (%s) — check .env app …%s",
                error,
                settings.github_client_id_suffix,
            )
            if error in {"incorrect_client_credentials", "bad_verification_code", "redirect_uri_mismatch"}:
                return RedirectResponse(
                    f"{settings.backend_base_url}/onboarding/error?reason={error}"
                )
            return RedirectResponse(f"{settings.backend_base_url}/onboarding/error?reason=missing_token")

        inspection = await inspect_github_token(access_token, token_scope)
        granted_scopes = inspection["scopes"]

        validation_error = validate_github_token_for_repo_sync(
            access_token,
            granted_scopes,
            settings.github_client_id_suffix,
        )
        if validation_error:
            logger.warning("Auth FAIL %s — %s", inspection["login"], validation_error.split(".")[0])
            reason = "github_app_token" if inspection["kind"] == "github_app_user" else "wrong_oauth_app"
            return RedirectResponse(
                f"{settings.backend_base_url}/onboarding/error?reason={reason}"
            )

        scope_to_store = token_scope or ",".join(sorted(granted_scopes))

        profile = await fetch_github_user(access_token)
        user = upsert_user_from_github(db, profile)
        store_github_token(db, user, access_token, scope_to_store, inspection["kind"])
        session_token = create_session_token(db, user)
        logger.info("Auth OK %s (scopes: %s)", user.github_username, scope_to_store or "none")

        success_url = settings.extension_success_url
        return RedirectResponse(
            f"{success_url}?leetsave_token={quote(session_token, safe='')}",
            status_code=302,
        )
    except ValueError as exc:
        message = str(exc)
        logger.warning("Auth FAIL %s", message.split(":")[0] if ":" in message else message[:80])
        if "incorrect_client_credentials" in message:
            reason = "incorrect_client_credentials"
        elif "bad_verification_code" in message:
            reason = "bad_verification_code"
        elif "redirect_uri_mismatch" in message:
            reason = "redirect_uri_mismatch"
        else:
            reason = "auth_failed"
        return RedirectResponse(f"{settings.backend_base_url}/onboarding/error?reason={reason}")
    except Exception:
        logger.exception("Auth FAIL unexpected error")
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
        github_scope=connection.scope if connection else None,
        github_token_kind=connection.token_type if connection else None,
        github_client_id_suffix=settings.github_client_id_suffix,
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
