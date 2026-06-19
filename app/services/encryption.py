import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from config import get_settings

settings = get_settings()


def _get_fernet() -> Fernet:
    key = settings.token_encryption_key
    if not key:
        raise ValueError("TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # Allow raw 32-byte url-safe base64 key generation helper output
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        return Fernet(derived)


def encrypt_token(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_token(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt stored token") from exc
