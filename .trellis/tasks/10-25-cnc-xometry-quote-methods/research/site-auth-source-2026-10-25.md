# Current deployed Xometry source observations — 2026-10-25

## Scope

Read-only inspection of the current official `www.xometry.com` JavaScript loaded by the existing configuration tab. No historical configuration, upload, save, declaration, or quote operation was performed. This is source/route research, not acceptance for the selected file. No cookies, authentication responses, storage values, headers, or signed URLs were retained.

## Authentication distinction

- `/_next/static/chunks/26c2f1551c8f4dde.js`: the client identity resolver reads the `_identity_cache` cookie and decodes the cached identity; `IdentityProvider` exposes that state to the new UI. Cookie contents were not inspected or fabricated.
- `/_next/static/chunks/7f7db42738e71894.js`: the new-quote upload component displays its sign-in requirement when the UI identity is neither valid nor expired. Its upload pipeline separately requires a valid identity and user ID. This explains why the legacy identity endpoint alone cannot establish upload readiness; it does not yet establish why this managed session lacks UI identity.
- `/_next/static/chunks/c5ab5fec30a829d4.js`: the deployed header's `navigateToAuthHostLogin` uses `https://xometry.com/login`. The application provider currently falls back to the older `https://www.xometry.com/account/login/` route. Live managed redirect/form evidence is required before changing recovery.
- The same chunk's `buildLoginRedirectUrl` also uses `https://xometry.com/login`, with the current application hostname's first label as `domain` and current pathname as `destination`; its `redirectToLogin` calls this builder. For the observed home page these are `www` and `/quoting/home/`. This is a source-grounded callback route, not a guessed Auth0 query.
- The identity chunk's `AuthTokenKeepAlive` makes an initial same-origin `GET /api/auth/refresh` with included credentials and no-store caching, and later uses POST on its timer. Only the observed initial GET is being considered for separate login research; no product refresh fallback is inferred from its existence.

## Configuration route distinction

`/_next/static/chunks/379793183a4d440e.js` defines `vercel_part_config` beside the deployed `bx_part_config_v2` experiment, its `use_part_config_v2` switch, and control-cohort bounce handling. The ordinary dashboard's native configuration link was already observed carrying this query key.

Therefore, the query key alone does not prove that a page is the public test drive or that it is unusable production UI. The binding must identify the actual deployed variant and verify same-file managed behavior. Historical part/price observations still cannot satisfy current-file acceptance, and this source observation does not activate any binding.

## Next diagnostic

Attach sanitized request/response/navigation listeners before the managed owner's initial navigation; record hostname/path/query-key names, safe control counts and cookie-name presence only. Distinguish an actual hosted challenge from a silent SSO redirect or missing new-UI identity. Preserve the existing guarded executor, account lease, and exact-file snapshot throughout.

## Managed follow-up observations

All attempts below used the existing guarded executor, account 1/configuration 3, frozen selected file checks and fenced lease. They performed zero quote mutations. Outputs exclude request/response bodies, headers, authentication values and raw browser errors. Cleanup completed with executor active count zero.

| Output | Observation |
| --- | --- |
| `managed-auth-diagnostic-result.json` | Restored API identity coexists with guest home. Existing generic fallback ends on `/account/login/` with no login/challenge controls and page errors. |
| `managed-auth-native-entry-result.json` | The observed native header initiates the official redirect chain; a research DOM read races navigation and stops safely. This is not a completed native-route result. |
| `managed-auth-native-entry-result-2.json` | After bounded read-only navigation settling, bare native login returns a fully loaded guest home without the UI cache name or a credential/challenge form. |
| `managed-auth-app-login-result.json` | Initial hydration fails before the callback-mode entry is reached. It is not evidence about the callback entry. |
| `managed-auth-app-login-result-2.json` | The source-grounded application return route also finishes at guest home; a further five-second same-owner observation and identity/readiness check remain negative. No credentials submitted. |
| `managed-auth-fresh-context-result.json` | Only restored state was omitted; the original account snapshot and stored ciphertext were preserved. Native hosted identifier and password were each submitted once. The password POST redirects successfully, but the button's eight-second wait returns false at 22.594 s, before the successful home navigation at 22.844 s. The early final home DOM is still hydrating; this attempt does not establish settled UI readiness. |

The last observation establishes a separate code gap: a timed-out final login click is not necessarily a failed login, and the same owner's read-only completion check must precede a manual-state conclusion. The approved correction is Xometry-specific, does not repeat credentials or navigate away from a challenge, and keeps exact identity verification mandatory. It does not by itself establish that the restored state can satisfy the current uploader.
