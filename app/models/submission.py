import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class LeetCodeSubmission(Base):
    __tablename__ = "leetcode_submissions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "problem_slug", "language", "code_hash", name="uq_submission_dedup"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_title: Mapped[str] = mapped_column(String(512), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    leetcode_url: Mapped[str] = mapped_column(String(512), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    code_text: Mapped[str] = mapped_column(Text, nullable=False)
    llm_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_path_code: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_path_explanation: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="submissions")
