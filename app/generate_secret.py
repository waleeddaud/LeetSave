import secrets

from cryptography.fernet import Fernet

print("JWT_SECRET_KEY (example):", secrets.token_urlsafe(32))
print("TOKEN_ENCRYPTION_KEY (Fernet):", Fernet.generate_key().decode())
