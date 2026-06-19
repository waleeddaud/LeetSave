from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from database import get_db
from models.user import User
from schemas.submission import SubmissionResponse
from services.github import ensure_repo
from services.submission import retry_github_sync

router = APIRouter()


@router.post("/ensure-repo")
async def ensure_user_repo(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        connection = await ensure_repo(db, user)
        return {
            "status": "ok",
            "repo_full_name": connection.repo_full_name,
            "default_branch": connection.default_branch,
        }
    except Exception as exc:
        return {"status": "failed", "message": str(exc)}


@router.post("/sync/{submission_id}", response_model=SubmissionResponse)
async def sync_submission(
    submission_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await retry_github_sync(db, user, submission_id)
    return SubmissionResponse(**result)
