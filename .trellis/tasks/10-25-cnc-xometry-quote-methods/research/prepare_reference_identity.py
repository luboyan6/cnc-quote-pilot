"""Prepare a read-only reference-browser identity comparison, without PII output."""

import asyncio
import hashlib
import json
from pathlib import Path

from managed_login_probe import EXPECTED_HASH, LoginError, QuoteRepository, async_engine


async def main():
    try:
        repository = QuoteRepository()
        auth = await repository.authorizer.load(1)
        snapshot = await repository.snapshot(auth, 3, 1)
        if snapshot.part_id != 4 or snapshot.payload.sha256 != EXPECTED_HASH:
            raise LoginError("QUOTE_INPUT_CHANGED")
        expected = hashlib.sha256(snapshot.account.username.strip().casefold().encode()).hexdigest()
        source = """async () => {
  if (location.protocol !== 'https:' || location.hostname !== 'www.xometry.com' ||
      !location.pathname.startsWith('/quoting/')) return {identity_match:false, reason:'WRONG_REFERENCE_PAGE'};
  try {
    const r = await fetch('https://api.xometry.com/v2/users/me', {
      credentials:'include', redirect:'error', headers:{Accept:'application/json'},
      signal:AbortSignal.timeout(3000)
    });
    if (!r.ok) return {identity_match:false, identity_available:false};
    const body = await r.json(), user = body.data || body.user || body;
    const values = ['email_address','email'].map(k=>user?.[k])
      .filter(v=>typeof v==='string' && v.trim());
    let matched = false;
    for (const value of values) {
      const bytes = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value.trim().toLowerCase()));
      const digest = [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join('');
      matched ||= digest === EXPECTED_DIGEST;
    }
    return {identity_match:matched, identity_available:values.length>0};
  } catch {return {identity_match:false, identity_available:false};}
}""".replace("EXPECTED_DIGEST", json.dumps(expected))
        output = Path(__file__).with_name("reference_identity_read.js")
        output.write_text(source, encoding="utf-8")
        print(json.dumps({"prepared": True, "file": output.name, "selected_file_verified": True}))
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
