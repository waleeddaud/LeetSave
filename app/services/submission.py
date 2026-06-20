from datetime import datetime, timezone
import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.submission import LeetCodeSubmission
from models.user import User
from services.github import compute_code_hash, push_submission_files
from services.llm import generate_explanation

logger = logging.getLogger("leetsave")


async def process_leetcode_submission(
    db: Session,
    user: User,
    *,
    problem_slug: str,
    problem_title: str,
    difficulty: str | None,
    language: str,
    code: str,
    status: str,
    leetcode_url: str,
) -> dict:
    if status != "Accepted":
        return {"status": "error", "message": "Only Accepted submissions can be synced"}

    if not code.strip():
        return {"status": "error", "message": "Code must not be empty"}

    if not problem_slug or not problem_title:
        return {"status": "error", "message": "problem_slug and problem_title are required"}

    code_hash = compute_code_hash(code, language, problem_slug)

    existing = (
        db.query(LeetCodeSubmission)
        .filter(
            LeetCodeSubmission.user_id == user.id,
            LeetCodeSubmission.problem_slug == problem_slug,
            LeetCodeSubmission.language == language,
            LeetCodeSubmission.code_hash == code_hash,
            LeetCodeSubmission.sync_status == "synced",
        )
        .first()
    )
    if existing:
        logger.info("Sync SKIP %s/%s — already on GitHub", user.github_username, problem_slug)
        return {
            "status": "already_synced",
            "message": "This accepted solution was already pushed to GitHub",
            "submission_id": str(existing.id),
        }

    submission = LeetCodeSubmission(
        user_id=user.id,
        problem_slug=problem_slug,
        problem_title=problem_title,
        difficulty=difficulty,
        language=language,
        status=status,
        leetcode_url=leetcode_url,
        code_hash=code_hash,
        code_text=code,
        sync_status="processing",
    )
    db.add(submission)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = (
            db.query(LeetCodeSubmission)
            .filter(
                LeetCodeSubmission.user_id == user.id,
                LeetCodeSubmission.problem_slug == problem_slug,
                LeetCodeSubmission.language == language,
                LeetCodeSubmission.code_hash == code_hash,
            )
            .first()
        )
        if duplicate and duplicate.sync_status == "synced":
            return {
                "status": "already_synced",
                "message": "This accepted solution was already pushed to GitHub",
                "submission_id": str(duplicate.id),
            }
        submission = duplicate

    db.refresh(submission)

    try:
        explanation = await generate_explanation(
            problem_title=problem_title,
            problem_slug=problem_slug,
            difficulty=difficulty,
            language=language,
            code=code,
        )
        submission.llm_explanation = explanation
        db.commit()
    except Exception:
        submission.llm_explanation = (
            f"# {problem_title}\n\nExplanation generation failed; solution saved without AI notes."
        )
        submission.sync_status = "explanation_failed"
        db.commit()

    try:
        commit_sha = await push_submission_files(db, user, submission)
        logger.info(
            "Sync OK %s/%s → GitHub commit %s",
            user.github_username,
            problem_slug,
            (commit_sha or "")[:7],
        )
        return {
            "status": "synced",
            "message": "Solution synced to GitHub",
            "submission_id": str(submission.id),
            "commit_sha": commit_sha,
        }
    except Exception as exc:
        submission.sync_status = "github_failed"
        db.commit()
        short_error = str(exc).split(".")[0]
        logger.warning("Sync FAIL %s/%s — %s", user.github_username, problem_slug, short_error)
        return {
            "status": "failed",
            "message": f"GitHub sync failed: {exc}",
            "submission_id": str(submission.id),
        }


async def retry_github_sync(db: Session, user: User, submission_id: UUID) -> dict:
    submission = (
        db.query(LeetCodeSubmission)
        .filter(LeetCodeSubmission.id == submission_id, LeetCodeSubmission.user_id == user.id)
        .first()
    )
    if not submission:
        return {"status": "error", "message": "Submission not found"}

    if submission.sync_status == "synced" and submission.github_commit_sha:
        return {
            "status": "already_synced",
            "message": "Submission already synced",
            "submission_id": str(submission.id),
        }

    if not submission.llm_explanation:
        submission.llm_explanation = await generate_explanation(
            problem_title=submission.problem_title,
            problem_slug=submission.problem_slug,
            difficulty=submission.difficulty,
            language=submission.language,
            code=submission.code_text,
        )
        db.commit()

    try:
        commit_sha = await push_submission_files(db, user, submission)
        logger.info(
            "Sync OK %s/%s → GitHub commit %s (retry)",
            user.github_username,
            submission.problem_slug,
            (commit_sha or "")[:7],
        )
        return {
            "status": "synced",
            "message": "Solution synced to GitHub",
            "submission_id": str(submission.id),
            "commit_sha": commit_sha,
        }
    except Exception as exc:
        submission.sync_status = "github_failed"
        db.commit()
        short_error = str(exc).split(".")[0]
        logger.warning(
            "Sync FAIL %s/%s — %s (retry)",
            user.github_username,
            submission.problem_slug,
            short_error,
        )
        return {
            "status": "failed",
            "message": f"GitHub sync failed: {exc}",
            "submission_id": str(submission.id),
        }
