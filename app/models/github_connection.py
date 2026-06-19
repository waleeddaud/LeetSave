import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserGitHubConnection(Base):
    __tablename__ = "user_github_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repo_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repo_full_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    repo_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="github_connection")
