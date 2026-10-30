# Research: Current official Xometry identity and login source

- Query: Determine the current native login entry and how the new quotation UI obtains `_identity_cache`; distinguish legacy authentication from new UI identity.
- Scope: Mixed: anonymous official deployed client source plus existing local implementation and redacted managed diagnostic evidence.
- Date: 2026-10-26

## Findings

### Reproducible public-source access

`research/static_auth_source_probe.py` performs anonymous GET requests to four fixed official source paths. It sends only a public browser User-Agent and Referer, does not use browser/account state, and reports byte counts, source hashes and fixed-term counts. It never requests an authenticated API, logs in, claims an account lease or changes a quotation.

The earlier HTTP 403 results for known JavaScript chunks did not establish removal of those chunks. The same fixed paths currently return HTTP 200 when the request has `User-Agent: Mozilla/5.0` and Referer `https://www.xometry.com/quoting/home/`.

Verified source fingerprints from this run:

| Official path | Bytes | SHA-256 |
| --- | ---: | --- |
| `/_next/static/chunks/26c2f1551c8f4dde.js` | 248315 | `8c3fcb42745f989a4b5cafd1e3e4ede2a710afe4a59c097b32d32d69700d5870` |
| `/_next/static/chunks/c5ab5fec30a829d4.js` | 22541 | `2038e009ce7fc87caa873c83d5798ebe4b9a9228de0d809d9f594c7622bfdcc9` |
| `/quoting/e94bcc6f5b9fca8d286f525fc63c08878c458746/resources/instant-quote-app.ed91074d66869df1a766.mjs` | 2472140 | `319b1cf28ee48fb34f9a3db9402bdd0d9b66b17bb343c6a497fc1ddea4bce3ee` |

### Canonical native login

The current deployed header source at [`c5ab5fec30a829d4.js`](https://www.xometry.com/_next/static/chunks/c5ab5fec30a829d4.js), minified line 1, exports these separate functions:

- `navigateToAuthHostLogin(event)` directs a normal click to `https://xometry.com/login`. Modifier/auxiliary clicks open the same URL in a new window when possible. The target does not use `/account/login/`.
- `buildLoginRedirectUrl(...)` starts with `/login` on `https://xometry.com`. Its default destination is the current pathname, and its default destination query is the current search string without the leading `?`. It sets `domain` from the current hostname's first label, with a special preview-host case. It also includes a nonempty destination query or explicit email when provided.
- `redirectToLogin()` assigns the URL produced by that builder.

For the observed hostname `www.xometry.com` and pathname `/quoting/home/` with no query, the builder therefore yields `https://xometry.com/login?domain=www&destination=%2Fquoting%2Fhome%2F`. Bare `https://xometry.com/login` is the separately verified native header entry, not an inferred callback API.

The local product fallback remains `backend/app/modules/cnc/login/providers.py:275`: when not already at the hosted form, Xometry `_submit` navigates to `https://www.xometry.com/account/login/`. Correcting that obsolete fallback to the observed native target is a bounded source-grounded change. It must retain the existing hosted-form checks, single credential action, exact identity and settled-UI completion requirements. Such a correction alone does not prove that the new identity bridge works.

### New client identity is separate from the legacy identity API

The deployed [`26c2f1551c8f4dde.js`](https://www.xometry.com/_next/static/chunks/26c2f1551c8f4dde.js) contains the client `IdentityProvider` and `useIdentity` exports. Its resolver reads `_identity_cache` through the cookie library. It decodes base64 JSON, or the `z1.` compressed form, then parses the cached identity. Missing or undecodable data becomes invalid identity. The provider uses an already supplied identity when available; otherwise its effect resolves from the cookie.

This inspected client resolver does not call the legacy `/v2/users/me` endpoint and does not write `_identity_cache`. No cache-writing code was found in the inspected identity/header sources. This establishes the consumer contract, not the server-side writer.

The same identity chunk exports `AuthTokenKeepAlive`. Its wrapper enables it only when `useIdentity().isValid` is true. When enabled, it first sends a same-origin GET to `/api/auth/refresh`, with included credentials, no-store caching and JSON acceptance. It stops on HTTP 401; otherwise it parses JSON and reads numeric `expiresInSeconds` with a default of 1800. Later scheduled or visibility-triggered refreshes use POST.

Therefore, the missing cache can prevent automatic keep-alive from starting. The refresh endpoint's presence does not prove that it is an initial identity bootstrap or that calling it manually establishes the cache. A diagnostic HTTP 200 alone is insufficient without checking its response type/expected semantics and actual subsequent UI/identity state.

### Legacy/new application distinction remains current

An anonymous GET of [`/quoting/home/`](https://www.xometry.com/quoting/home/) currently returns the legacy application's `env.js` and `instant-quote-app.ed91074d66869df1a766.mjs` script paths. The legacy app has one `/v2/users/me` reference, one `/v1/jwt/login` reference, and no `_identity_cache` or `/api/auth/refresh` terms. Its protected-route code redirects a missing legacy user to its configured login origin with the current destination and `domain=www`.

Separately, the main session's fresh guarded diagnostic in `research/managed-auth-bridge-result-2026-10-26.json` records a legacy initial quote page and a Next application after the hosted callback. The new cache is absent in both page-visible and context cookie checks while the legacy identity API still matches. The one rejected cookie was not `_identity_cache`. This strengthens the mixed legacy/new routing hypothesis; it does not identify which server callback/middleware should mint the cache or prove its root cause.

## Files Found

- `research/static_auth_source_probe.py`: Anonymous, bounded, fixed-source retrieval with redacted metadata output; no application or authenticated operations.
- `research/site-auth-source-2026-10-25.md`: Previous official native-login/identity observations, now rechecked against the same current chunks.
- `research/pause-handoff-2026-10-26.md`: Frozen test scope, prior unsuccessful identity-bridge diagnostics and no-upload constraints.
- `research/managed-auth-bridge-result-2026-10-26.json`: Main-session guarded callback/variant/cache metadata; this researcher did not produce or modify it.
- `backend/app/modules/cnc/login/providers.py:275`: Current obsolete login fallback; the researcher did not change product code.
- `.trellis/spec/backend/cnc-account-login.md:34`: Same-owner, authenticated identity and quote-page verification contract.
- `.trellis/spec/backend/browser-executor.md:34`: Exact host policy, encrypted state and guarded browser requirements.

## Bounded Recommendation

Use the verified native `https://xometry.com/login` fallback when recovery is needed outside the hosted form, with focused regression coverage. Continue using the existing same-owner form flow and completion checks. Preserve the manual state when legacy identity matches but the new quote UI remains guest.

For further diagnosis, capture only response route/status/content-type and known-cookie presence around the official login/callback/refresh chain. Distinguish an actual JSON refresh response from an HTML fallback. Do not fabricate the cache, copy reference-browser authentication or relax browser egress. Avoid further credential submissions without a new evidence-driven hypothesis.

## Caveats / Not Found

- The server-side `_identity_cache` writer and exact callback/middleware implementation were not available in the inspected public client sources.
- No alternative official bootstrap endpoint was established.
- The native target correction does not establish live login readiness, file upload, parameter receipts, current pricing or production binding acceptance.
- Source hashes identify this observation only; deployment files can change.
- This researcher performed zero credential submissions, authenticated API requests, cookie transfers, account lease/database operations, uploads, declarations, saves or quotation requests. Product code, specs and other task files were left untouched.
