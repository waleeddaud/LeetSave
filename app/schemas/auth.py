from typing import Optional

from pydantic import BaseModel


class MeResponse(BaseModel):
    id: str
    github_id: str
    github_username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    github_connected: bool
    repo_full_name: Optional[str] = None
    repo_name: Optional[str] = None
    github_scope: Optional[str] = None
    github_token_kind: Optional[str] = None
    github_client_id_suffix: Optional[str] = None
