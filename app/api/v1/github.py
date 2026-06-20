from uuid import UUID
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from database import get_db
from models.user import User
from schemas.submission import SubmissionResponse
from services.github import ensure_repo
from services.submission import retry_github_sync

router = APIRouter()
logger = logging.getLogger("leetsave")


@router.post("/ensure-repo")
async def ensure_user_repo(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        connection = await ensure_repo(db, user)
        logger.info("GitHub repo ready %s", connection.repo_full_name)
        return {
            "status": "ok",
            "repo_full_name": connection.repo_full_name,
            "default_branch": connection.default_branch,
        }
    except Exception as exc:
        logger.warning("GitHub repo FAIL %s — %s", user.github_username, str(exc).split(".")[0])
        return {"status": "failed", "message": str(exc)}


@router.post("/sync/{submission_id}", response_model=SubmissionResponse)
async def sync_submission(
    submission_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SubmissionResponse(**await retry_github_sync(db, user, submission_id))
