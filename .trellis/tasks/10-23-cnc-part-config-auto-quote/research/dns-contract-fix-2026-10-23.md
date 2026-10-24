# DNS contract repair — 2026-10-23

## Scope and evidence boundary

The existing browser/login contracts require rejecting the complete DNS answer set when any address is unsafe, including IPv6 site-local addresses. The current resolver instead filters unsafe addresses and returns any remaining public addresses. This repair belongs only in `backend/app/modules/cnc/browser/policy.py:BrowserPolicy.resolve`; no proxy or provider change is necessary.

Implementation ownership is limited to that resolver and this record. Preserve exact-host validation, optional-resource denial, fixed error sanitization, and all unrelated working-tree edits. Do not edit tests to accept filtering, change DNS/proxy settings, contact providers, change business data/migrations, restart services, commit, or archive the task. The final reviewer owns the combined browser/login/quote checks after the concurrent file-extension repair settles.

The [provenance audit](dns-contract-audit-2026-10-23.md) found no explicit authorization for the filtering behavior. Its author and motivation remain unknown. Historical approval was for temporary runtime proxy fake-IP exclusions and explicitly preserved BrowserPolicy; that override was later restored. This report does not attribute the filtering edit to an earlier agent or imply proof that the user never edited it.

## Pre-edit snapshot

Captured before the repair, on branch `dev`, HEAD `93dff6ec`:

- Source byte SHA-256: `4FB0BEE64735D5338896A4B9A6AF11AF3F5BF17A2DA375A72B03492177C1666C`.
- Committed blob: `8008480820a0ef7172050e398b2debe60aeaa986` (`git rev-parse HEAD:backend/app/modules/cnc/browser/policy.py`).
- The hash matches the independent audit and previous failed browser-check record.
- `git diff -- backend/app/modules/cnc/browser/policy.py` produced exactly the two resolver hunks below. Git also warned that its next checkout may convert LF to CRLF; that warning is not a source edit.

```diff
diff --git a/backend/app/modules/cnc/browser/policy.py b/backend/app/modules/cnc/browser/policy.py
index 80084808..636b50ba 100644
--- a/backend/app/modules/cnc/browser/policy.py
+++ b/backend/app/modules/cnc/browser/policy.py
@@ -63,9 +63,10 @@ class BrowserPolicy:
             raise BrowserStop(Reason.POLICY_BLOCKED) from None
 
     def resolve(self, host: str) -> list[str]:
-        """SOCKS resolver hook, all answers vetted and returned as fixed IPs.
+        """SOCKS resolver hook, vetted answers returned as fixed IPs.
 
-        Any private/mixed/special answer rejects the whole connection. Convert
+        Non-global, private, or special-purpose addresses are filtered out.
+        The connection is refused only when no safe address remains. Convert
         faults to ValueError so the vendored proxy logs only fixed reason codes.
         No injectable private-allow resolver exists in the production API.
         """
@@ -73,13 +74,16 @@ class BrowserPolicy:
             raise ValueError(Reason.POLICY_BLOCKED.value)
         try:
             records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
-            addresses = list(dict.fromkeys(str(record[4][0]) for record in records))
-            if not addresses:
+            candidates = list(dict.fromkeys(str(record[4][0]) for record in records))
+            if not candidates:
                 raise ValueError
-            for address in addresses:
+            addresses = []
+            for address in candidates:
                 ip = ipaddress.ip_address(address)
-                if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified or ip.is_loopback or ip.is_link_local or (isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local):
-                    raise ValueError
+                if ip.is_global and not ip.is_multicast and not ip.is_reserved and not ip.is_unspecified and not ip.is_loopback and not ip.is_link_local and not (isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local):
+                    addresses.append(address)
+            if not addresses:
+                raise ValueError
             return addresses
         except (OSError, ValueError, TypeError):
             raise ValueError(Reason.POLICY_BLOCKED.value) from None
```

## Failure reproduction before repair

From `backend`:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k test_dns_rejects_every_private_special_or_mixed_answer -v
```

Result: exit **1**, **1 existing method run**, **12 failing mixed-answer subtests**, 0.018 s. Each `(8.8.8.8, unsafe_address)` pair failed `assertRaises(ValueError)`; the unsafe-only variants were refused. Tested unsafe addresses were `127.0.0.1`, `10.0.0.1`, `169.254.169.254`, `::1`, `fd00::1`, `fe80::1`, `fec0::1`, `feff:ffff::1`, `0.0.0.0`, `224.0.0.1`, `100.64.0.1`, and `192.0.2.1`. DNS is mocked; this reproduction makes no provider connection.

## Repair and final checks

Applied a targeted patch to the two resolver hunks only:

1. Keep the complete deduplicated literal-address list and reject an empty answer set.
2. Raise on any existing unsafe-address predicate, preserving the explicit IPv6 site-local check. Return the list only after every address passes.
3. Restore the docstring to the same strict contract. Preserve DNS arguments, hostname gate, and the fixed `ValueError(policy_blocked)` conversion.

No test was edited by this repair. The existing DNS and egress tests exercise the original required refusal behavior. A concurrent worker owns file-extension changes and their tests; they are outside this report's implementation ownership.

Final source byte SHA-256: `5EA9F6BA61C121D7C9D01E685426CE7B6C492237651128D3D188B11B4046BAAF`. `git hash-object backend/app/modules/cnc/browser/policy.py` returns `8008480820a0ef7172050e398b2debe60aeaa986`, matching the committed blob. `git diff --exit-code HEAD -- backend/app/modules/cnc/browser/policy.py` exits **0** with no diff. The formerly dirty policy entry therefore becomes content-clean as the consequence of this targeted repair; no checkout/reset/revert command was used, and no unrelated file content was replaced.

All test/lint/type-check commands below ran from `backend`; Git inspection ran from the workspace root.

| Exact command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k PolicyTests -v` | **5 methods passed**, 0.011 s, zero skips, exit 0. Includes all 24 unsafe-only/mixed DNS subcases, public-IP deduplication, unknown-host refusal, and existing URL/scope contracts. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_egress.py -v` | **3 methods passed**, 0.206 s, zero skips, exit 0. Includes mixed DNS refusal before upstream connect, zero awaited upstream connection, released handlers, cancelled resolving handlers, IP pinning, and sanitized fault logging. |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/browser/policy.py` | All checks passed, exit 0. |
| `.venv/Scripts/basedpyright.exe app/modules/cnc/browser/policy.py` | 0 errors, 0 warnings, 0 notes, exit 0. |
| `git diff --check -- backend/app/modules/cnc/browser/policy.py .trellis/tasks/10-23-cnc-part-config-auto-quote/research/dns-contract-fix-2026-10-23.md` | Exit 0; no whitespace error in tracked changes. The new record was also read back after writing. |

The previously reported mixed-DNS egress failure/cleanup error did not recur in this unchanged egress regression suite. This supports resolving the policy root cause without a separate cleanup patch. It is not a new full-browser-suite result.

## Remaining verification boundary

The main session's final reviewer must run the combined browser/login/quote/upload regressions after both concurrent repairs settle and separately report opt-in Chromium and Windows symlink skips. This worker ran only the focused checks listed above. The all-answers-vetted policy remains strict; these synthetic DNS/local SOCKS results do not establish real provider connectivity, adapter readiness, current geometry/parameters, or a real price. No provider was contacted, no DNS/proxy setting changed, and no running service or business data was modified.
