"""Freeze a complete request before atomically admitting any item."""

from app.config.setting import settings
from app.modules.cnc.quote.repository import QuoteRepository

from .contracts import BatchError, digest, normalized_targets
from .repository import BatchRepository


class BatchService:
    def __init__(self, quote_repository=None, repository=None):
        self.quotes = quote_repository or QuoteRepository()
        self.repository = repository or BatchRepository(self.quotes.sessions)

    async def authorize(self, auth, permission, *, for_run=False):
        current = await self.quotes.authorizer.load(auth.user.id, for_run=for_run)
        if not current.user.is_superuser and f"module_cnc:cnc_quote_batch:{permission}" not in current.permissions:
            raise BatchError("BATCH_PERMISSION_REVOKED", 403)
        return current

    async def normalize(self, auth, data):
        snapshots = {}
        targets = normalized_targets(data)
        if len(targets) > self.repository.capacity:
            raise BatchError("BATCH_QUEUE_FULL", 409)
        bases = {}
        for config_id, account_id, quantity in targets:
            key = config_id, account_id
            if key not in bases:
                snapshot = await self.quotes.snapshot(auth, config_id, account_id)
                bases[key] = snapshot.frozen | {"config_id": config_id, "part_id": snapshot.part_id, "account_id": snapshot.account.id, "file_name": snapshot.file_name}
            base = bases[key]
            frozen = base | {"requested": base["requested"] | {"quantity": str(quantity)}}
            snapshots[digest(frozen)] = frozen
        return [(frozen, key) for key, frozen in sorted(snapshots.items())]

    async def preview(self, auth, data):
        if not settings.CNC_BATCH_ENABLED:
            raise BatchError("BATCH_DISABLED", 503)
        auth = await self.authorize(auth, "create", for_run=True)
        snapshots = await self.normalize(auth, data)
        return {"item_count": len(snapshots), "items": [{"config_id": f["config_id"], "account_id": f["account_id"], "file_name": f["file_name"], "requested": f["requested"]} for f, _ in snapshots]}

    async def create(self, auth, data):
        if not settings.CNC_BATCH_ENABLED:
            raise BatchError("BATCH_DISABLED", 503)
        auth = await self.authorize(auth, "create", for_run=True)
        fingerprint = digest(normalized_targets(data))
        # Network replays keep the original frozen request even after sources change.
        prior = await self.repository.find_request(auth.user.id, str(data.request_id), fingerprint)
        if prior:
            return await self.repository.detail(auth.user.id, prior)
        snapshots = await self.normalize(auth, data)
        id = await self.repository.create(auth.user.id, str(data.request_id), fingerprint, snapshots)
        return await self.repository.detail(auth.user.id, id)


_service = None


def get_batch_service():
    global _service
    if _service is None:
        _service = BatchService()
    return _service
