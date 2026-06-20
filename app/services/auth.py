import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from sqlalchemy.orm import Session

from config import get_settings
from models.session import UserSession
from models.user import User
from services.encryption import encrypt_token

settings = get_settings()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session_token(db: Session, user: User) -> str:
    jti = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.session_expire_minutes)
    payload = {
        "sub": str(user.id),
        "jti": jti,
        "exp": int(expires_at.timestamp()),
        "iat": int(now.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(jti),
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    return token


def decode_session_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def get_user_from_token(db: Session, token: str) -> User | None:
    try:
        payload = decode_session_token(token)
    except jwt.PyJWTError:
        return None

    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        return None

    session = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == hash_token(jti),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    if not session:
        return None

    return db.query(User).filter(User.id == UUID(user_id)).first()


def revoke_session(db: Session, token: str) -> bool:
    try:
        payload = decode_session_token(token)
    except jwt.PyJWTError:
        return False

    jti = payload.get("jti")
    if not jti:
        return False

    session = db.query(UserSession).filter(UserSession.token_hash == hash_token(jti)).first()
    if not session:
        return False

    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True


def store_github_token(
    db: Session, user: User, access_token: str, scope: str | None, token_kind: str | None = None
) -> None:
    from models.github_connection import UserGitHubConnection

    connection = user.github_connection
    encrypted = encrypt_token(access_token)
    if connection:
        connection.access_token_encrypted = encrypted
        connection.scope = scope
        connection.token_type = token_kind or "classic_oauth"
        connection.repo_full_name = None
        connection.repo_id = None
        connection.repo_name = settings.github_default_repo_name
    else:
        connection = UserGitHubConnection(
            user_id=user.id,
            access_token_encrypted=encrypted,
            scope=scope,
            token_type=token_kind or "classic_oauth",
            repo_name=settings.github_default_repo_name,
            default_branch=settings.github_default_branch,
        )
        db.add(connection)
    db.commit()
