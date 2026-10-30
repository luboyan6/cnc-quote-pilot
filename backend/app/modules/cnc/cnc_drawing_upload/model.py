"""Durable request-to-drawing mapping for safe upload retries."""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase


class CncDrawingUpload(MappedBase):
    __tablename__: str = "cnc_drawing_upload"
    __table_args__ = (UniqueConstraint("part_id", name="uq_cnc_drawing_upload_part"),)

    owner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("cnc_part.id", ondelete="RESTRICT"), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
