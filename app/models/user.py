import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    github_username: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    github_connection = relationship(
        "UserGitHubConnection", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    submissions = relationship("LeetCodeSubmission", back_populates="user", cascade="all, delete-orphan")
