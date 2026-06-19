from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LeetCodeSubmissionCreate(BaseModel):
    problem_slug: str
    problem_title: str
    difficulty: Optional[str] = None
    language: str
    code: str
    status: str = "Accepted"
    leetcode_url: str
    timestamp: Optional[datetime] = None
    code_hash: Optional[str] = None


class SubmissionResponse(BaseModel):
    status: str
    message: str
    submission_id: Optional[str] = None
    commit_sha: Optional[str] = None


class UserInfo(BaseModel):
    id: UUID
    github_id: str
    github_username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    github_connected: bool = False
    repo_full_name: Optional[str] = None


class SubmissionListItem(BaseModel):
    id: UUID
    problem_slug: str
    problem_title: str
    difficulty: Optional[str] = None
    language: str
    status: str
    sync_status: str
    pushed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
