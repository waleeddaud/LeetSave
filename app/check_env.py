import os
from pathlib import Path

from config import get_settings

env_file: dict[str, str] = {}
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        key, value = line.split("=", 1)
        env_file[key.strip()] = value.strip()


def mask(value: str) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return value[:2] + "…"
    return value[:4] + "…" + value[-4:]


def kind(prefix: str) -> str:
    if prefix.startswith("Iv23"):
        return "GitHub App (Iv23)"
    if prefix.startswith("Ov23"):
        return "OAuth App (Ov23)"
    return "unknown"


for key in ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_REDIRECT_URI", "SCOPE"]:
    file_val = env_file.get(key, "")
    os_val = os.environ.get(key, "")
    print(f"{key}:")
    print(f"  .env file: {mask(file_val)}")
    if key == "GITHUB_CLIENT_ID" and file_val:
        print(f"    type: {kind(file_val[:4])}")
    print(f"  OS env:    {mask(os_val)}")
    if key == "GITHUB_CLIENT_ID" and os_val:
        print(f"    type: {kind(os_val[:4])}")
    if file_val and os_val and file_val != os_val:
        print("  *** MISMATCH: OS environment variable overrides .env ***")
    print()

get_settings.cache_clear()
settings = get_settings()
loaded_id = settings.github_client_id
print("What backend actually loads:")
print(f"  client_id: {mask(loaded_id)}")
print(f"  type: {kind(loaded_id[:4]) if loaded_id else 'unset'}")
print(f"  suffix: …{settings.github_client_id_suffix}")
print(f"  redirect_uri: {settings.github_redirect_uri}")
print(f"  oauth_scope: {settings.github_oauth_scope_normalized}")

if loaded_id and env_file.get("GITHUB_CLIENT_ID") and loaded_id != env_file["GITHUB_CLIENT_ID"]:
    print("\nPROBLEM: Backend is NOT using GITHUB_CLIENT_ID from .env file.")
    print("Fix: remove GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET from Windows user/system env vars,")
    print("or restart the terminal after editing .env only.")

if loaded_id.startswith("Iv23"):
    print("\nPROBLEM: Loaded client_id is a GitHub App (Iv23), not an OAuth App.")
    print("LeetSave needs OAuth Apps (usually Ov23). Use leetBridge credentials in .env only.")
