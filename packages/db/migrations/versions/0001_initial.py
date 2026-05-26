"""Initial local Slack RAG schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "rag_sources",
        _uuid_pk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("connector_type", sa.Text(), nullable=True),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "crawl_policy", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("auth_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auth_mode", sa.Text(), nullable=False, server_default=sa.text("'none'")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("visibility", sa.Text(), nullable=False, server_default=sa.text("'internal'")),
        sa.Column("authority_score", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "rag_documents",
        _uuid_pk(),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rag_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("uri", sa.Text(), nullable=True),
        sa.Column("canonical_uri", sa.Text(), nullable=True),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("normalized_text_hash", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
    )

    op.create_table(
        "slack_conversations",
        _uuid_pk(),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("root_message_ts", sa.Text(), nullable=False),
        sa.Column("thread_ts", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        *_timestamps(),
        sa.UniqueConstraint("workspace_id", "channel_id", "thread_ts", name="uq_slack_thread"),
    )

    op.create_table(
        "rag_chunks",
        _uuid_pk(),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rag_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("checksum", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        *_timestamps(),
    )

    op.create_table(
        "embedding_jobs",
        _uuid_pk(),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rag_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("model", sa.Text(), nullable=False, server_default=sa.text("'Qwen3-Embedding-8B'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "conversation_messages",
        _uuid_pk(),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("slack_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slack_message_ts", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "conversation_summaries",
        _uuid_pk(),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("slack_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_message_end_ts", sa.Text(), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "conversation_facts",
        _uuid_pk(),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("slack_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("facts", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
    )

    op.create_table(
        "troubleshooting_sessions",
        _uuid_pk(),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("slack_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("issue_type", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("known_facts", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("missing_fields", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("hypotheses", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        *_timestamps(),
    )

    op.create_table(
        "source_permissions",
        _uuid_pk(),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rag_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("allowed_groups", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("allowed_users", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("visibility", sa.Text(), nullable=False, server_default=sa.text("'internal'")),
        *_timestamps(),
    )

    op.create_table(
        "answer_feedback",
        _uuid_pk(),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("slack_conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("message_ts", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("rating", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "source_fetches",
        _uuid_pk(),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rag_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rag_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("canonical_uri", sa.Text(), nullable=True),
        sa.Column("fetch_status", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified_header", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("normalized_text_hash", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "response_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )

    op.create_table(
        "source_discovered_urls",
        _uuid_pk(),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rag_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("canonical_uri", sa.Text(), nullable=True),
        sa.Column("discovery_method", sa.Text(), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_id", "uri", name="uq_source_discovered_uri"),
    )

    op.create_table(
        "source_auth_configs",
        _uuid_pk(),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rag_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("auth_mode", sa.Text(), nullable=False),
        sa.Column("secret_ref", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
    )

    op.create_index("ix_rag_documents_source_id", "rag_documents", ["source_id"])
    op.create_index("ix_rag_chunks_document_id", "rag_chunks", ["document_id"])
    op.create_index("ix_source_fetches_source_id", "source_fetches", ["source_id"])
    op.create_index("ix_source_discovered_urls_source_id", "source_discovered_urls", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_source_discovered_urls_source_id", table_name="source_discovered_urls")
    op.drop_index("ix_source_fetches_source_id", table_name="source_fetches")
    op.drop_index("ix_rag_chunks_document_id", table_name="rag_chunks")
    op.drop_index("ix_rag_documents_source_id", table_name="rag_documents")
    op.drop_table("source_auth_configs")
    op.drop_table("source_discovered_urls")
    op.drop_table("source_fetches")
    op.drop_table("answer_feedback")
    op.drop_table("source_permissions")
    op.drop_table("troubleshooting_sessions")
    op.drop_table("conversation_facts")
    op.drop_table("conversation_summaries")
    op.drop_table("conversation_messages")
    op.drop_table("embedding_jobs")
    op.drop_table("rag_chunks")
    op.drop_table("slack_conversations")
    op.drop_table("rag_documents")
    op.drop_table("rag_sources")
