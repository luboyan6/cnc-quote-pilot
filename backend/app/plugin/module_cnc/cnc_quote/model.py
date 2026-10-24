"""Minimal durable runs/intents, discovered alongside other plugin models."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase


class CncQuoteRunModel(MappedBase):
    __tablename__: str = "cnc_quote_run"
    __table_args__ = (UniqueConstraint("actor_id", "config_id", "request_id", name="uq_cnc_quote_request"),)

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[int] = mapped_column(Integer, index=True)
    owner_id: Mapped[int] = mapped_column(Integer)
    config_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # NULL after terminal persistence. A portable UNIQUE also covers concurrent
    # starts on SQLite, where SELECT FOR UPDATE is not available.
    active_config_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    part_id: Mapped[int] = mapped_column(Integer)
    platform_id: Mapped[int] = mapped_column(Integer)
    account_id: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str] = mapped_column(String(36))
    frozen: Mapped[dict] = mapped_column(JSON)
    public_view: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32))
    stage: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CncQuoteIntentModel(MappedBase):
    __tablename__: str = "cnc_quote_intent"
    __table_args__ = (UniqueConstraint("run_id", "generation", "operation", name="uq_cnc_quote_intent"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("cnc_quote_run.run_id"), index=True)
    generation: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(16))
    fingerprint: Mapped[str] = mapped_column(String(64))
    scope: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16))
    receipt: Mapped[dict | None] = mapped_column(JSON, nullable=True)
