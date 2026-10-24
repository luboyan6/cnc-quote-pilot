"""Public fixed-version app metadata only; never prints source or credentials."""

import json
import re
import sys
from urllib.request import Request, urlopen

ROOT = "https://www.xometry.com/quoting/f2a0abe95eba64c6489707d33f36836523930363/"
ASSETS = ("env.js", "resources/instant-quote-app.30062e772837939cc52f.mjs")
TERMS = ("us-files.xometry.com", "sentry.mgmt.global.xmtr.io", "appgw.conviva.com", "volume", "volumeMm3", "dimensions", "quantity", "Save Configuration")

for asset in ASSETS:
    try:
        request = Request(ROOT + asset, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=20) as response:
            source = response.read(4_000_000).decode("utf-8")
            print(json.dumps({"asset": asset.split("/")[-1], "status": response.status, "size": len(source), "terms": {term: source.count(term) for term in TERMS}}), flush=True)
            if "--contexts" in sys.argv and asset.endswith("mjs"):
                for term in ("volume", "dimensions", "thumbnail", "quotePart", "upload", "itar"):
                    print(json.dumps({"public_source_term":term,"contexts":[source[max(0,match.start()-85):match.end()+120] for match in list(re.finditer(term,source,re.I))[:8]]}),flush=True)
    except Exception as error:
        print(json.dumps({"asset": asset.split("/")[-1], "error_type": type(error).__name__}), flush=True)
