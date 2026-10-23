"""Encrypted scope envelope; inject existing CryptoUtil, do not invent a cipher."""

import json
from typing import Protocol

from .contracts import SessionScope
from .errors import BrowserStop, Reason
from .policy import BrowserPolicy


class CryptoCodec(Protocol):
    # Production: SessionCodec(CryptoUtil). Tests inject real Fernet or a spy.
    def encrypt(self, plain: str) -> str: ...
    def decrypt(self, cipher: str) -> str: ...


class SessionCodec:
    def __init__(self, crypto: CryptoCodec) -> None:
        self._crypto = crypto

    @staticmethod
    def _validate_state(state: dict, policy: BrowserPolicy) -> None:
        if not isinstance(state, dict) or set(state) != {"cookies", "origins"}:
            raise BrowserStop(Reason.SESSION_INVALID)
        if not isinstance(state["cookies"], list) or not isinstance(state["origins"], list):
            raise BrowserStop(Reason.SESSION_INVALID)
        for cookie in state["cookies"]:
            if not isinstance(cookie, dict) or not isinstance(cookie.get("domain"), str) or cookie["domain"].lstrip(".") not in policy.allowed_hosts:
                raise BrowserStop(Reason.SESSION_INVALID)
        for origin in state["origins"]:
            if not isinstance(origin, dict) or not isinstance(origin.get("origin"), str):
                raise BrowserStop(Reason.SESSION_INVALID)
            policy.validate_url(origin["origin"])

    def seal(self, scope: SessionScope, state: dict, policy: BrowserPolicy) -> str:
        try:
            self._validate_state(state, policy)
            plain = json.dumps({"version": 1, "scope": scope.as_dict(), "state": state}, separators=(",", ":"))
            cipher = self._crypto.encrypt(plain)
            if not isinstance(cipher, str) or not cipher or cipher == plain:
                raise ValueError
            return cipher
        except Exception:
            raise BrowserStop(Reason.SESSION_INVALID) from None

    def open(self, scope: SessionScope, ciphertext: str, policy: BrowserPolicy) -> dict:
        try:
            if not isinstance(ciphertext, str) or not ciphertext or len(ciphertext) > 16 * 1024 * 1024:
                raise ValueError
            envelope = json.loads(self._crypto.decrypt(ciphertext))
            if envelope.get("version") != 1 or envelope.get("scope") != scope.as_dict():
                raise ValueError
            state = envelope["state"]
            self._validate_state(state, policy)
            return state
        except Exception:
            raise BrowserStop(Reason.SESSION_INVALID) from None
