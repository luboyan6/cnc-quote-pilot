"""Read anonymous official static sources; never request account/auth state.

This is source evidence only, with no login, browser ownership, cookies,
database access, file upload, parameter edit or quotation action.
"""

import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ORIGIN = "https://www.xometry.com"
PATHS = (
    "/quoting/home/",
    "/_next/static/chunks/26c2f1551c8f4dde.js",
    "/_next/static/chunks/c5ab5fec30a829d4.js",
    "/quoting/e94bcc6f5b9fca8d286f525fc63c08878c458746/resources/instant-quote-app.ed91074d66869df1a766.mjs",
)
TERMS = (
    "_identity_cache",
    "Identity cache cookie not found",
    "Failed to decode identity cache cookie",
    "/api/auth/refresh",
    "expiresInSeconds",
    "AuthTokenKeepAlive",
    "buildLoginRedirectUrl",
    "navigateToAuthHostLogin",
    "https://xometry.com/login",
    "/v2/users/me",
    "/v1/jwt/login",
    "/login/callback",
)


def main():
    for path in PATHS:
        request = Request(
            ORIGIN + path,
            headers={"User-Agent": "Mozilla/5.0", "Referer": ORIGIN + "/quoting/home/"},
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = response.read(12_000_001)
                if len(payload) > 12_000_000:
                    print(json.dumps({"path": path, "status": "SOURCE_SIZE_LIMIT"}))
                    continue
                source = payload.decode("utf-8")
                result = {
                    "path": path,
                    "status": response.status,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "content_type": response.headers.get_content_type(),
                    "term_counts": {term: source.count(term) for term in TERMS},
                }
                if path == "/quoting/home/":
                    # Static script paths only. Do not output inline HTML,
                    # headers, response bodies or authentication information.
                    result["same_origin_script_paths"] = [
                        value
                        for value in re.findall(r'<script[^>]+src="([^"]+)"', source)
                        if value.startswith(("/quoting/", "/_next/static/"))
                        and "?" not in value
                        and "#" not in value
                    ]
                print(json.dumps(result), flush=True)
        except HTTPError as error:
            print(json.dumps({"path": path, "status": error.code}), flush=True)
        except (URLError, TimeoutError, UnicodeError):
            print(json.dumps({"path": path, "status": "PUBLIC_SOURCE_UNAVAILABLE"}), flush=True)


if __name__ == "__main__":
    main()
