"""Trusted exact-domain policy; DNS answers are checked at actual proxy connect."""

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

from .errors import BrowserStop, Reason


def _hostname(value: str) -> str:
    if not isinstance(value, str) or value != value.lower() or len(value) > 253 or "." not in value:
        raise BrowserStop(Reason.POLICY_BLOCKED)
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in value.split(".")):
        raise BrowserStop(Reason.POLICY_BLOCKED)
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    raise BrowserStop(Reason.POLICY_BLOCKED)


@dataclass(frozen=True)
class BrowserPolicy:
    allowed_hosts: frozenset[str]
    blocked_resource_hosts: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_hosts, frozenset) or not self.allowed_hosts:
            raise BrowserStop(Reason.POLICY_BLOCKED)
        for host in self.allowed_hosts:
            _hostname(host)
        if not isinstance(self.blocked_resource_hosts, frozenset) or self.allowed_hosts & self.blocked_resource_hosts:
            raise BrowserStop(Reason.POLICY_BLOCKED)
        for host in self.blocked_resource_hosts:
            _hostname(host)

    def blocks_optional_resource(self, request) -> bool:
        """Deny reviewed analytics/QR resources without stopping the page.

        No egress is granted: blocked hosts remain outside the SOCKS allowlist.
        Top-level navigation and unknown destinations still stop execution.
        """
        try:
            parsed = urlsplit(request.url)
            if parsed.hostname not in self.blocked_resource_hosts or parsed.scheme != "https" or parsed.port not in {None, 443} or parsed.username or parsed.password:
                return False
            return not request.is_navigation_request() or request.frame.parent_frame is not None
        except Exception:
            return False

    def validate_url(self, url: str) -> None:
        try:
            if not isinstance(url, str) or any(ord(c) <= 32 or c == "\\" for c in url):
                raise ValueError
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None or parsed.port not in {443, None}:
                raise ValueError
            if parsed.hostname not in self.allowed_hosts:
                raise ValueError
        except (ValueError, TypeError):
            raise BrowserStop(Reason.POLICY_BLOCKED) from None

    def resolve(self, host: str) -> list[str]:
        """SOCKS resolver hook, all answers vetted and returned as fixed IPs.

        Any private/mixed/special answer rejects the whole connection. Convert
        faults to ValueError so the vendored proxy logs only fixed reason codes.
        No injectable private-allow resolver exists in the production API.
        """
        if host not in self.allowed_hosts:
            raise ValueError(Reason.POLICY_BLOCKED.value)
        try:
            records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
            addresses = list(dict.fromkeys(str(record[4][0]) for record in records))
            if not addresses:
                raise ValueError
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified or ip.is_loopback or ip.is_link_local or (isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local):
                    raise ValueError
            return addresses
        except (OSError, ValueError, TypeError):
            raise ValueError(Reason.POLICY_BLOCKED.value) from None
