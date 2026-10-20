from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def jsonb_dict(default: dict[str, Any] | None = None) -> Mapped[dict[str, Any]]:
    return mapped_column(JSONB, nullable=False, default=lambda: dict(default or {}))


def jsonb_list(default: list[Any] | None = None) -> Mapped[list[Any]]:
    return mapped_column(JSONB, nullable=False, default=lambda: list(default or []))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RagSource(TimestampMixin, Base):
    __tablename__ = "rag_sources"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    connector_type: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict[str, Any]] = jsonb_dict()
    crawl_policy: Mapped[dict[str, Any]] = jsonb_dict()
    auth_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auth_mode: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    visibility: Mapped[str] = mapped_column(Text, nullable=False, default="internal")
    authority_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    documents: Mapped[list[RagDocument]] = relationship(back_populates="source")


class RagDocument(TimestampMixin, Base):
    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    uri: Mapped[str | None] = mapped_column(Text)
    canonical_uri: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(Text)
    normalized_text_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    source: Mapped[RagSource] = relationship(back_populates="documents")
    chunks: Mapped[list[RagChunk]] = relationship(back_populates="document")


class RagChunk(TimestampMixin, Base):
    __tablename__ = "rag_chunks"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")

    document: Mapped[RagDocument] = relationship(back_populates="chunks")


class EmbeddingJob(TimestampMixin, Base):
    __tablename__ = "embedding_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_chunks.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    model: Mapped[str] = mapped_column(Text, nullable=False, default="Qwen3-Embedding-8B")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SlackConversation(TimestampMixin, Base):
    __tablename__ = "slack_conversations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "channel_id", "thread_ts", name="uq_slack_thread"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    root_message_ts: Mapped[str] = mapped_column(Text, nullable=False)
    thread_ts: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")

    messages: Mapped[list[ConversationMessage]] = relationship(back_populates="conversation")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slack_conversations.id", ondelete="CASCADE"), nullable=False
    )
    slack_message_ts: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped[SlackConversation] = relationship(back_populates="messages")


class ConversationSummary(TimestampMixin, Base):
    __tablename__ = "conversation_summaries"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slack_conversations.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_message_end_ts: Mapped[str | None] = mapped_column(Text)


class ConversationFact(TimestampMixin, Base):
    __tablename__ = "conversation_facts"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slack_conversations.id", ondelete="CASCADE"), nullable=False
    )
    facts: Mapped[dict[str, Any]] = jsonb_dict()


class TroubleshootingSession(TimestampMixin, Base):
    __tablename__ = "troubleshooting_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slack_conversations.id", ondelete="CASCADE"), nullable=False
    )
    issue_type: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    known_facts: Mapped[dict[str, Any]] = jsonb_dict()
    missing_fields: Mapped[list[Any]] = jsonb_list()
    hypotheses: Mapped[list[Any]] = jsonb_list()


class SourcePermission(TimestampMixin, Base):
    __tablename__ = "source_permissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False
    )
    allowed_groups: Mapped[list[Any]] = jsonb_list()
    allowed_users: Mapped[list[Any]] = jsonb_list()
    visibility: Mapped[str] = mapped_column(Text, nullable=False, default="internal")


class AnswerFeedback(Base):
    __tablename__ = "answer_feedback"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("slack_conversations.id", ondelete="SET NULL")
    )
    message_ts: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SourceFetch(Base):
    __tablename__ = "source_fetches"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_documents.id", ondelete="SET NULL")
    )
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_uri: Mapped[str | None] = mapped_column(Text)
    fetch_status: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified_header: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(Text)
    normalized_text_hash: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    response_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class SourceDiscoveredUrl(Base):
    __tablename__ = "source_discovered_urls"
    __table_args__ = (UniqueConstraint("source_id", "uri", name="uq_source_discovered_uri"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False
    )
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_uri: Mapped[str | None] = mapped_column(Text)
    discovery_method: Mapped[str | None] = mapped_column(Text)
    depth: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SourceAuthConfig(TimestampMixin, Base):
    __tablename__ = "source_auth_configs"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False
    )
    auth_mode: Mapped[str] = mapped_column(Text, nullable=False)
    secret_ref: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
