"""Batch persistence uses independent transactions, never HTTP-owned sessions."""

from app.modules.cnc.batch.repository import BatchRepository as CncQuoteBatchCRUD

__all__ = ["CncQuoteBatchCRUD"]
