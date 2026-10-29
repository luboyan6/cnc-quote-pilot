"""Shared login orchestration for HTTP and MCP, with the same actor checks."""

from app.core.exceptions import CustomException

from .contracts import LoginError
from .runtime import get_login_manager


async def login_action(auth, account_id, session_id=None, kind="start", payload=None, *, manager=None):
    """Load and decrypt stored credentials internally; return only a public view."""
    manager = manager if manager is not None else get_login_manager()
    try:
        account = await manager.repository.load(auth, account_id)
        if kind == "start":
            return await manager.start(account)
        return await manager.command(account, session_id or "", kind, payload)
    except LoginError as exc:
        owned = manager.accounts.get(account_id)
        if (
            owned
            and owned.account.actor_id == auth.user.id
            and exc.reason
            in {
                "ACCOUNT_UNAVAILABLE",
                "ACCOUNT_DISABLED",
                "ACCOUNT_CHANGED",
                "CREDENTIALS_UNAVAILABLE",
                "PLATFORM_CONFIGURATION_INVALID",
            }
        ):
            await manager.revoke(account_id)
        raise CustomException(msg=exc.reason) from None
