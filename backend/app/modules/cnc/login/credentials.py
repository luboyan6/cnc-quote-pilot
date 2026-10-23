"""All write paths use the application's existing encryption key ring."""

import json

from app.utils.crypto_util import CryptoUtil

from .contracts import LoginError


def seal_credentials(username: str, password: str) -> bytes:
    return CryptoUtil.encrypt(json.dumps({"version": 1, "username": username, "password": password}, separators=(",", ":"))).encode()


def read_credentials(account) -> tuple[str, str]:
    try:
        if account.credential_ciphertext:
            value = json.loads(CryptoUtil.decrypt(bytes(account.credential_ciphertext).decode()))
            if value.get("version") != 1 or value.get("username") != account.username or not isinstance(value.get("password"), str):
                raise ValueError
            return account.username, value["password"]
        return account.username, account.password or ""
    except Exception:
        raise LoginError("CREDENTIALS_UNAVAILABLE") from None
