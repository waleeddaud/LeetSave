"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-06-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("github_id", sa.String(length=64), nullable=False),
        sa.Column("github_username", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)
    op.create_index("ix_users_github_username", "users", ["github_username"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)

    op.create_table(
        "user_github_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_type", sa.String(length=64), nullable=True),
        sa.Column("scope", sa.String(length=255), nullable=True),
        sa.Column("repo_name", sa.String(length=255), nullable=True),
        sa.Column("repo_full_name", sa.String(length=512), nullable=True),
        sa.Column("repo_id", sa.String(length=64), nullable=True),
        sa.Column("default_branch", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "leetcode_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_slug", sa.String(length=255), nullable=False),
        sa.Column("problem_title", sa.String(length=512), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("leetcode_url", sa.String(length=512), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("code_text", sa.Text(), nullable=False),
        sa.Column("llm_explanation", sa.Text(), nullable=True),
        sa.Column("github_path_code", sa.String(length=512), nullable=True),
        sa.Column("github_path_explanation", sa.String(length=512), nullable=True),
        sa.Column("github_commit_sha", sa.String(length=64), nullable=True),
        sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "problem_slug", "language", "code_hash", name="uq_submission_dedup"),
    )
    op.create_index("ix_leetcode_submissions_code_hash", "leetcode_submissions", ["code_hash"], unique=False)
    op.create_index("ix_leetcode_submissions_user_id", "leetcode_submissions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("leetcode_submissions")
    op.drop_table("user_github_connections")
    op.drop_table("user_sessions")
    op.drop_table("users")
