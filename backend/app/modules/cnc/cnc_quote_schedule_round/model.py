from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase


class CncQuoteScheduleRoundModel(MappedBase):
    __tablename__: str = "cnc_quote_schedule_round"
    __table_args__ = (UniqueConstraint("schedule_id", "scheduled_for", name="uq_cnc_schedule_slot"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(36), ForeignKey("cnc_quote_schedule.id"), index=True)
    round_no: Mapped[int] = mapped_column(Integer)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(24), default="RUNNING", index=True)
    batch_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cnc_quote_batch.id"), nullable=True, index=True)
    schedule_revision: Mapped[int] = mapped_column(Integer)
    skip_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
