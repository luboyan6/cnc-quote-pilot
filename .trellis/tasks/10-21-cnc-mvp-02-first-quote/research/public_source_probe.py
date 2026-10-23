"""Inspect public provider JavaScript contracts; no account/session is loaded."""

import hashlib
import re
import sys
import urllib.request
from pathlib import Path

target = Path(".trellis/.runtime/login-public-source")
target.mkdir(parents=True, exist_ok=True)
for url in sys.argv[1:]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        source = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
        path = target / (hashlib.sha256(url.encode()).hexdigest()[:12] + ".js")
        path.write_text(source, encoding="utf-8")
        print(f"SOURCE {url} bytes={len(source)} saved={path}", flush=True)
        matches = re.findall(r".{0,100}(?:getUserInfo|userInfo|currentUser|userEmail|loginWithRedirect|/login|/user/|/user-info|/account|passportUrl|loginUrl|LOGIN_URL).{0,160}", source)
        for snippet in list(dict.fromkeys(matches))[:40]:
            print(snippet, flush=True)
    except Exception as exc:
        print(f"SOURCE ERROR {url}: {type(exc).__name__}", flush=True)
