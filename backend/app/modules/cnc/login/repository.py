"""Independent committed transactions: no HTTP session is retained by a browser."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select, update

from app.plugin.module_cnc.cnc_account.model import CncAccountModel

from .contracts import AccountSnapshot, LoginError
from .credentials import read_credentials, seal_credentials


def utcnow():
    # Existing lease/auth timestamp columns are PostgreSQL timestamp without TZ.
    return datetime.now(UTC).replace(tzinfo=None)


def revision(account) -> str:
    platform = account.platform
    data = [
        account.username,
        account.platform_id,
        account.login_method,
        account.enabled,
        account.is_deleted,
        account.created_id,
        bytes(account.credential_ciphertext or b"").hex(),
        account.password,
        platform.login_url if platform else None,
        platform.quote_entry_url if platform else None,
        platform.is_deleted if platform else True,
    ]
    return hashlib.sha256(json.dumps(data).encode()).hexdigest()


class LoginRepository:
    def __init__(self, session_factory=None):
        if session_factory is None:
            from app.core.database import async_db_session

            session_factory = async_db_session
        self.sessions = session_factory

    async def load(self, auth, account_id: int) -> AccountSnapshot:
        async with self.sessions() as db, db.begin():
            account = await db.scalar(select(CncAccountModel).where(CncAccountModel.id == account_id, CncAccountModel.is_deleted.is_(False)))
            if account is None or (not auth.user.is_superuser and account.created_id != auth.user.id):
                raise LoginError("ACCOUNT_UNAVAILABLE")
            if not account.enabled:
                raise LoginError("ACCOUNT_DISABLED")
            if not account.platform_id or not account.platform or account.platform.is_deleted or not account.platform.login_url or not account.platform.quote_entry_url:
                raise LoginError("PLATFORM_CONFIGURATION_INVALID")
            username, password = read_credentials(account)
            if not account.credential_ciphertext and password:
                account.credential_ciphertext = seal_credentials(username, password)
                account.password = ""
                await db.flush()
            return AccountSnapshot(
                account.id,
                auth.user.id,
                account.created_id or 0,
                account.platform_id,
                account.platform.name or "",
                username,
                password,
                account.login_method or "PASSWORD",
                account.platform.login_url,
                account.platform.quote_entry_url,
                revision(account),
                bytes(account.session_ciphertext).decode() if account.session_ciphertext else None,
            )

    async def claim(self, snapshot: AccountSnapshot, owner: str) -> int:
        async with self.sessions() as db, db.begin():
            now = utcnow()
            result = await db.execute(
                update(CncAccountModel)
                .where(
                    CncAccountModel.id == snapshot.id,
                    CncAccountModel.is_deleted.is_(False),
                    CncAccountModel.enabled.is_(True),
                    or_(CncAccountModel.lease_owner.is_(None), CncAccountModel.lease_until < now),
                )
                .values(lease_owner=owner, lease_until=now + timedelta(seconds=60), lease_token=func.coalesce(CncAccountModel.lease_token, 0) + 1)
                .returning(CncAccountModel.lease_token)
            )
            token = result.scalar_one_or_none()
            if token is None:
                raise LoginError("ACCOUNT_BUSY")
            # Check revision under the same write lock before commit/grant.
            account = await db.scalar(select(CncAccountModel).where(CncAccountModel.id == snapshot.id).execution_options(populate_existing=True))
            if revision(account) != snapshot.revision:
                raise LoginError("ACCOUNT_CHANGED")
            return token

    def _fence(self, snapshot, owner, token):
        return (CncAccountModel.id == snapshot.id, CncAccountModel.lease_owner == owner, CncAccountModel.lease_token == token, CncAccountModel.lease_until > utcnow())

    async def renew(self, snapshot, owner, token, *, state: str | None = None) -> None:
        async with self.sessions() as db, db.begin():
            account = await db.scalar(select(CncAccountModel).where(*self._fence(snapshot, owner, token)).with_for_update(of=CncAccountModel))
            if account is None or revision(account) != snapshot.revision:
                raise LoginError("ACCOUNT_CHANGED_OR_LEASE_LOST")
            values: dict[str, Any] = {"lease_until": utcnow() + timedelta(seconds=60)}
            if state is not None:
                values.update(session_ciphertext=state.encode(), session_status="VALID", last_verified_at=utcnow(), session_version=(account.session_version or 0) + 1)
            result = await db.execute(update(CncAccountModel).where(*self._fence(snapshot, owner, token)).values(**values).returning(CncAccountModel.id))
            if result.scalar_one_or_none() != snapshot.id:
                # The lease can expire while waiting for the row lock. A prior
                # read never substitutes for the final conditional write.
                raise LoginError("ACCOUNT_CHANGED_OR_LEASE_LOST")

    async def release(self, snapshot, owner, token):
        async with self.sessions() as db, db.begin():
            await db.execute(
                update(CncAccountModel).where(CncAccountModel.id == snapshot.id, CncAccountModel.lease_owner == owner, CncAccountModel.lease_token == token).values(lease_owner=None, lease_until=None)
            )
