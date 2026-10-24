# Approved DNS candidate filtering — 2026-10-23

## User decision and scope

The user explicitly chose: **“保留 Antigravity 的地址过滤方案；同步调整契约和验证”**. This supersedes the earlier strict candidate that rejected a complete answer set whenever any address was unsafe. This is an approved behavior change; tests now verify the chosen contract instead of silently weakening the prior expectations.

The earlier [audit](dns-contract-audit-2026-10-23.md) and [strict-candidate repair](dns-contract-fix-2026-10-23.md) remain historical records. They describe the evidence and decision available at that time. This report records the subsequent explicit choice without rewriting those records or inferring original authorship from the user's naming.

This implementation owns `browser/policy.py`, only DNS-related portions of `browser/test_policy_files_state.py` and `browser/test_egress.py`, and this new record. The main session owns synchronized spec/design updates and final combined verification. Preserve the concurrent `.setp` implementation/tests and all other edits. No DNS/proxy settings, provider access/activation, business data, migrations, service restart, commit, or task archive is part of this repair.

## Approved contract

- Keep exact trusted hostnames and HTTPS/443 constraints. Reviewed optional denied resources remain denied and outside the allowlist.
- Resolve once and deduplicate literal candidates in order. Exclude non-global/private/special/multicast/unspecified/loopback/link-local and IPv6 site-local addresses.
- When at least one vetted candidate remains, return only those candidates. Public-plus-unsafe and unsafe-plus-public answer sets must retain their safe IPs without connecting to excluded IPs.
- Reject all-unsafe, empty, malformed, and resolver-error cases with the fixed `policy_blocked` reason. A malformed answer must not be bypassed merely because a preceding address was public.
- The SOCKS proxy must pass only the vetted literal list to `_open_first`; it must never retry an excluded candidate or pass the hostname for another resolution.

## Initial source and verification plan

The incoming strict candidate's byte SHA-256 was `5EA9F6BA61C121D7C9D01E685426CE7B6C492237651128D3D188B11B4046BAAF`. The original filtering candidate's byte SHA-256 and exact two-hunk diff remain preserved in the earlier strict-candidate report: `4FB0BEE64735D5338896A4B9A6AF11AF3F5BF17A2DA375A72B03492177C1666C`.

Use targeted patches only. Restore that filtering behavior, and explicitly sanitize truncated resolver tuples (`IndexError`) along with existing resolver/address faults so malformed responses satisfy the chosen fixed-reason contract.

Update the behavioral tests first, reproduce their expected incompatibility with the strict candidate, then restore filtering and run policy, egress, scoped Ruff and basedpyright. Keep unsafe-only refusal, non-443/unknown-host refusal, literal pinning, sanitized logging, cancellation and cleanup assertions. The existing `.setp` tests in the shared policy/files/state test file are outside the DNS edits.

## Results

### New-contract failures before restoring filtering

With the tests updated and the production resolver still at the strict candidate above, from `backend`:

| Exact command | Expected incompatibility observed |
| --- | --- |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k PolicyTests -q` | Exit 1; 7 methods, **29 subtest errors**, 0.037 s. Both mixed-answer orders for 13 unsafe IPs produced 26 `ValueError(policy_blocked)` errors instead of retaining the public candidate. Three truncated answer tuples exposed `IndexError` instead of the fixed reason. Existing unsafe-only, empty, invalid-literal, resolver-fault and all-public cases passed. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_egress.py -k test_mixed_dns_connects_only_to_safe_pinned_ips -v` | Exit 1; 1 method, **1 failure**, 0.050 s. Strict whole-set refusal returned SOCKS reply 2 rather than reaching the safe-IP connector stub, which intentionally returns unreachable reply 4. Client/proxy cleanup completed. |

These are failures against the newly chosen contract, not evidence that the former strict contract was incorrectly implemented. The change is authorized by the explicit user decision above.

### Implementation and preserved boundaries

- Restored the incoming filtering docstring and candidate loop with targeted patches. The hostname gate, DNS call parameters, URL validation and optional-resource denial are unchanged.
- Added `IndexError` to the fixed-reason conversion for malformed/truncated resolver tuples. Invalid address literals and existing `OSError`/`ValueError`/`TypeError` cases still refuse the complete result, including when a preceding candidate was public.
- Replaced the former mixed-set rejection expectation with 13 unsafe-only refusals plus 26 public-first/unsafe-first filtering assertions. The original 12 unsafe IP cases remain; `2001:2::120` adds the observed benchmark IPv6 case. Explicit site-local cases remain `fec0::1` and `feff:ffff::1`.
- Extended all-public deduplication to IPv4 and IPv6 and asserted one exact HTTPS/443 resolver call. Added seven empty/malformed and three resolver-fault cases, all requiring the fixed reason.
- Kept non-443 and unknown-host refusal in the SOCKS test. Its unsafe-only set is still refused before `_open_first` is awaited and handlers are released. A separate mixed-answer test proves `_open_first` receives only `["8.8.8.8", "2001:4860:4860::8888"]` once, not the hostname, duplicate IPs, private addresses, benchmark IPv6 or site-local IPv6. The DNS call occurs once. Existing literal connector, sanitized logging, resolving cancellation and cleanup checks remain.
- The `.setp` test added by the other worker is retained unchanged; no `FileTests` or `StateTests` body was edited by this DNS implementation.

### Focused checks after the change

All commands below ran from `backend`, except the final Git inspection from the workspace root:

| Exact command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k PolicyTests -v` | **7 methods passed**, 0.020 s, zero skips, exit 0. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_egress.py -v` | **4 methods passed**, 0.314 s, zero skips, exit 0. |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/browser/policy.py tests/cnc/browser/test_policy_files_state.py tests/cnc/browser/test_egress.py` | All checks passed, exit 0. |
| `.venv/Scripts/basedpyright.exe app/modules/cnc/browser/policy.py tests/cnc/browser/test_policy_files_state.py tests/cnc/browser/test_egress.py` | 0 errors, 0 warnings, 0 notes, exit 0. |
| `git diff --check -- backend/app/modules/cnc/browser/policy.py backend/tests/cnc/browser/test_policy_files_state.py backend/tests/cnc/browser/test_egress.py .trellis/tasks/10-23-cnc-part-config-auto-quote/research/dns-filtering-approved-2026-10-23.md` | Exit 0; no whitespace error in tracked changes. Git emitted its existing LF-to-CRLF checkout notices. |

Final byte SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `backend/app/modules/cnc/browser/policy.py` | `180E26F19A20A9A00072AE687C086BB04F52AB943388046149987BDB99228F9C` |
| `backend/tests/cnc/browser/test_policy_files_state.py` | `47426C05AE0732CBD3D4514D4CE947B40798A1EEDB3E9A4908F7A73013CAF339` |
| `backend/tests/cnc/browser/test_egress.py` | `0C592899311CD6A4173681FFD732E40A3A24C73BFAF5BEE4A03611FE6B901C55` |

As a read-only provenance check, removing only the added `IndexError` catch from the final source **in memory** reproduces byte SHA-256 `4FB0BEE64735D5338896A4B9A6AF11AF3F5BF17A2DA375A72B03492177C1666C`. Thus the restored filtering source matches the originally recorded candidate except for this explicit malformed-tuple fix. No checkout, reset or revert command was used.

The main session synchronized the [shared browser contract](../../../spec/backend/browser-executor.md), [login contract](../../../spec/backend/cnc-account-login.md) and task design with the approved filtering decision while this implementation ran; their revised DNS clauses were read back before handoff.

## Remaining verification boundary

The main session will dispatch final combined browser/login/quote/upload verification and report Chromium/symlink skips separately. The focused checks above use mock DNS and synthetic local SOCKS connections; upstream connection creation is stubbed in the mixed-answer assertion. They prove candidate selection and pinning, not real provider connectivity or quote correctness. IP classification does not establish that a local proxy's synthetic public-looking IP is a provider address. Provider activation and real price/geometry/parameter acceptance remain separate, unchanged gates.
