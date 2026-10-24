"""Reviewable, temporary Mihomo DNS exception for the registered quote hosts.

Dry-run by default. --apply reloads an in-memory payload through the existing
local Windows controller pipe; it NEVER rewrites the user's on-disk config.
--restore reloads the unchanged disk config. No proxy or application credentials
are printed. This is a local integration diagnostic, not application behavior.
Sources: https://wiki.metacubex.one/en/config/dns/ and /en/api/.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys
import threading

import yaml

HOSTS = (
    "www.xometry.com", "xometry.com", "get.xometry.com", "auth.xometry.com",
    "login.xometry.com", "api.xometry.com", "assets.xometry.com", "cdn.auth0.com",
    "fonts.gstatic.com", "images.prismic.io", "xometry-marketing.cdn.prismic.io",
    "featureassets.org", "prodregistryv2.org", "us-files.xometry.com", "www.jlc-cnc.com", "jlc-cnc.com",
    "passport.jlc.com", "static-passport.jlc.com", "static.jlc.com",
    "static.jlc-cnc.com", "pbt-pub.jlc.com", "g.alicdn.com", "o.alicdn.com",
)
CONFIG = (
    Path(os.environ["APPDATA"])
    / "io.github.clash-verge-rev.clash-verge-rev"
    / "clash-verge.yaml"
)


def request(config, body=None):
    pipe = config.get("external-controller-pipe", "")
    if not isinstance(pipe, str) or not pipe.startswith("\\\\.\\pipe\\verge-mihomo"):
        raise ValueError("Expected existing local Mihomo controller pipe")
    secret = config.get("secret", "")
    if not isinstance(secret, str) or "\r" in secret or "\n" in secret:
        raise ValueError("Invalid local controller configuration")
    payload = json.dumps(body).encode("utf-8") if body is not None else b""
    method_path = "PUT /configs?force=true" if body is not None else "GET /version"
    headers = [
        f"{method_path} HTTP/1.1", "Host: localhost",
        "Content-Type: application/json", f"Content-Length: {len(payload)}",
        "Connection: close",
    ]
    if secret:
        headers.append(f"Authorization: Bearer {secret}")
    packet = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + payload

    def timeout():
        print("CONTROLLER_RESULT_UNCONFIRMED_NO_RETRY", flush=True)
        os._exit(3)

    watchdog = threading.Timer(20, timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        try:
            controller = open(pipe, "r+b", buffering=0)
        except FileNotFoundError:
            # Verge's generated disk file can retain its sidecar build label
            # while the installed production core uses the same private suffix.
            # No request has been sent; only this exact local alias is allowed.
            marker = "\\verge-mihomo-sidecar-release-"
            if marker not in pipe:
                raise
            controller = open(pipe.replace(marker, "\\verge-mihomo-production-", 1), "r+b", buffering=0)
        with controller as stream:
            # A FileIO write may be partial. Never send a second HTTP request.
            remaining = memoryview(packet)
            while remaining:
                sent = stream.write(remaining)
                if sent is None or sent <= 0:
                    raise OSError("Controller write unconfirmed")
                remaining = remaining[sent:]
            first = bytearray()
            while b"\r\n" not in first and len(first) < 8192:
                value = stream.read(4096)
                if not value:
                    raise OSError("Controller response unconfirmed")
                first.extend(value)
            match = re.match(rb"HTTP/1\.[01] (\d{3}) [^\r\n]*\r\n", first)
            if match is None:
                raise OSError("Invalid controller response")
            status = int(match.group(1))
            if status != (204 if body is not None else 200):
                print(json.dumps({"controller_http_status": status}))
                raise OSError("Controller reload rejected")
    finally:
        watchdog.cancel()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--restore", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    original = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    dns = original.get("dns", {})
    if dns.get("enhanced-mode") != "fake-ip" or dns.get("fake-ip-filter-mode", "blacklist") != "blacklist":
        raise ValueError("Unexpected DNS mode; no change")
    filters = dns.get("fake-ip-filter", [])
    if not isinstance(filters, list) or any(not isinstance(value, str) for value in filters):
        raise ValueError("Unexpected DNS filters; no change")
    modified = copy.deepcopy(original)
    added = [host for host in HOSTS if host not in filters]
    modified["dns"]["fake-ip-filter"] = filters + added
    check = copy.deepcopy(modified)
    check["dns"]["fake-ip-filter"] = filters
    assert check == original, "Only exact host DNS exceptions may change"
    summary = {"disk_config_modified": False, "added_exact_hosts": added}
    if args.check:
        request(original)
        summary["action"] = "read_only_controller_check_passed"
    elif args.restore:
        request(original, {"payload": yaml.safe_dump(original, allow_unicode=True, sort_keys=False)})
        summary["action"] = "restored_original_runtime_configuration"
    elif args.apply:
        request(original, {"payload": yaml.safe_dump(modified, allow_unicode=True, sort_keys=False)})
        summary["action"] = "temporary_runtime_dns_exceptions_applied"
    else:
        summary["action"] = "dry_run_only"
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # YAML/parser/controller exceptions can embed private config fragments.
        print(json.dumps({"error": "DNS_DIAGNOSTIC_FAILED_NO_CONFIG_CONTENT_LOGGED", "type": type(exc).__name__, "errno": getattr(exc, "errno", None), "winerror": getattr(exc, "winerror", None)}), file=sys.stderr)
        sys.exit(1)
