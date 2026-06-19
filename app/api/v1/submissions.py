from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from database import get_db
from models.submission import LeetCodeSubmission
from models.user import User
from schemas.submission import LeetCodeSubmissionCreate, SubmissionListItem, SubmissionResponse
from services.submission import process_leetcode_submission

router = APIRouter()


@router.post("/leetcode", response_model=SubmissionResponse)
async def create_leetcode_submission(
    payload: LeetCodeSubmissionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await process_leetcode_submission(
        db,
        user,
        problem_slug=payload.problem_slug,
        problem_title=payload.problem_title,
        difficulty=payload.difficulty,
        language=payload.language,
        code=payload.code,
        status=payload.status,
        leetcode_url=payload.leetcode_url,
    )
    return SubmissionResponse(**result)


@router.get("", response_model=List[SubmissionListItem])
def list_submissions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submissions = (
        db.query(LeetCodeSubmission)
        .filter(LeetCodeSubmission.user_id == user.id)
        .order_by(LeetCodeSubmission.created_at.desc())
        .limit(100)
        .all()
    )
    return submissions
