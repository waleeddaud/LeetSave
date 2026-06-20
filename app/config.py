from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = "development"
    backend_base_url: str = "http://localhost:8000"
    frontend_or_extension_success_url: str = ""
    chrome_extension_id: str = ""

    database_url: str = "postgresql+psycopg://user:password@localhost:5432/leetcode_github_sync"

    jwt_secret_key: str = Field(
        default="replace-me",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    session_expire_minutes: int = 10080

    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_scope: str = Field(
        default="public_repo user:email",
        validation_alias=AliasChoices("GITHUB_OAUTH_SCOPE", "SCOPE"),
    )
    github_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/github/callback",
        validation_alias=AliasChoices("GITHUB_REDIRECT_URI", "CALLBACK_URL"),
    )
    github_default_repo_name: str = "leetcode-problems"
    github_default_branch: str = "main"

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    token_encryption_key: str = ""

    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]
        if self.chrome_extension_id:
            origins.append(f"chrome-extension://{self.chrome_extension_id}")
        return origins

    @property
    def github_oauth_scope_normalized(self) -> str:
        normalized = self.github_oauth_scope.replace(",", " ").strip()
        parts = {part.strip() for part in normalized.split() if part.strip()}
        parts.add("user:email")
        return " ".join(sorted(parts, key=lambda value: (value != "user:email", value)))

    @property
    def github_client_id_suffix(self) -> str:
        client_id = self.github_client_id.strip()
        if len(client_id) < 6:
            return client_id or "unset"
        return client_id[-6:]

    @property
    def extension_success_url(self) -> str:
        if self.frontend_or_extension_success_url:
            return self.frontend_or_extension_success_url
        # Use backend success page so Chrome does not block http -> chrome-extension redirects.
        return f"{self.backend_base_url}/onboarding/success"


@lru_cache
def get_settings() -> Settings:
    return Settings()
