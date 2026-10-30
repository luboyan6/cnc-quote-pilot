"""Owned session metadata and visible-message projection for the source agent.

LangGraph checkpoints remain the sole source of inference state. These tables
only support authorization and rebuilding user-visible history.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase


class SourceChatSession(MappedBase):
    __tablename__: str = "ai_source_chat_session"
    __table_args__ = (Index("ix_ai_source_chat_session_owner_updated", "owner_id", "updated_at"),)

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SourceChatMessage(MappedBase):
    __tablename__: str = "ai_source_chat_message"
    __table_args__ = (UniqueConstraint("session_id", "position", name="uq_ai_source_chat_message_position"),)

    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("ai_source_chat_session.session_id", ondelete="CASCADE"), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_result_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True, default=list)
