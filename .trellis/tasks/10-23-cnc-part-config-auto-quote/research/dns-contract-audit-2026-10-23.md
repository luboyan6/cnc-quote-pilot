# Research: mixed DNS contract and edit provenance

- Query: Does the uncommitted unsafe-address filtering in `BrowserPolicy.resolve` implement an explicitly authorized user decision or an earlier implementation workaround? What is the smallest repair consistent with the existing contract and preservation of unrelated edits?
- Scope: internal code, task records, and targeted local conversation history; no provider connections or network configuration changes.
- Date: 2026-10-23

## Findings

### Decision and confidence

The executable contract is unambiguously strict: **reject the complete DNS answer set if any answer is unsafe**. The current filtering implementation is a regression against that contract. No explicit user instruction authorizing this filtering behavior was found in the reviewed task records or readable conversation history.

The author and exact motivation of the filtering edit remain **unattributed**. The evidence does not justify labeling it an earlier agent workaround, nor does it prove the user did not edit it manually. Keep this distinction when reporting the repair.

A narrowly scoped repair to `resolve` can restore the already documented behavior without discarding unrelated changes. Under the current user's instruction to fix necessary root causes, recommend repairing this specific regression, retaining the exact-host policy, optional-resource denial, error sanitization, and all other working-tree edits. Do not reset the whole file or repository, weaken the tests, or treat temporary DNS authorization as approval for filtering.

### Evidence for intent

1. `.trellis/spec/backend/browser-executor.md:30` requires all DNS answers to be public and explicitly rejects IPv6 site-local addresses. Its validation matrix at line 42 names private/**mixed**/site-local DNS as policy stops. The D-18 extension at line 17 preserves strict DNS rules.
2. `.trellis/spec/backend/cnc-account-login.md:35` preserves mixed/private/reserved DNS rejection; line 53 requires reserved/mixed DNS refusal and reports live integration unverified.
3. `.trellis/tasks/10-23-cnc-part-config-auto-quote/research/existing-flow.md:35` says to recheck the managed executor rather than weaken its policy.
4. `research/operations-2026-10-23.md:11`–19 records authorization for the exact temporary `quote_dns_override.py --apply` operation: runtime fake-IP exclusions for already registered hosts, no on-disk configuration rewrite, and **BrowserPolicy unchanged**. That is an environment diagnostic, not a safety-policy exception.
5. `research/continuation-2026-10-23.md:9` records successful restoration of that temporary override. Nothing there authorizes a persistent resolver policy change.
6. `research/provider-live-evidence-2026-10-23.md:27` explicitly says IPv4 classification does not authorize discarding the unsafe IPv6 answer. Historical D-18 evidence in `.trellis/tasks/10-21-cnc-mvp-02-first-quote/research/login-provider-evidence-2026-10-22.md:37` similarly states no filtering of problematic answers was performed.
7. The current handoff preserves this as an unresolved contract conflict rather than an approved new policy: `research/session-handoff-2026-10-23-chrome-devtools.md:78`.

### Targeted history review and limits

Used the `trellis-session-insight` skill and project-scoped, date-bounded `trellis mem` searches for `DNS`, `policy.py`, `过滤`, and `filter`. Searches for `policy.py` and `filter` returned no dialogue hits. Relevant DNS extracts were limited to decision-related turns; credentials, account state, authenticated DOM, and unrelated logs were not emitted or copied into this report.

- Session `01a16716-b56c-70d0-8561-c1447200cd9e`, DNS hit turns 19–21: the assistant describes temporary Fake-IP repair while retaining browser safety checks, then reports real public answers. No policy-filter authorization is present in these turns.
- Session `01a16855-667f-77f1-aabc-7e1c454484d8`, DNS hit turns 7 and 9: the later reviewer reports the policy/test conflict and deliberately leaves it for the main session to coordinate.
- `trellis mem` warned that 45 and 17 inter-agent payloads, respectively, are encrypted and cannot be recovered. Absence of a readable instruction is not proof of complete historical absence.
- A bounded, read-only scan of the 2026-10-23 local Codex tool records found no matching tool call that wrote `browser/policy.py`. Nearby patches mentioned that path in reports but changed `login/providers.py` or documentation instead. This does not cover manual IDE edits, other applications, or unavailable history.
- `policy.py` last-write timestamp at audit: `2026-10-23 10:30:13 UTC`, preceding the previous main-session rollout. A filesystem timestamp cannot establish authorship.

The research role forbids Git operations, so no Git command was run. The exact preexisting diff was recovered from the **already recorded** reviewer output in rollout `01a16860-28d9-74d3-acd7-b1b90ac553d0`, record line 145, timestamp `2026-10-23T10:51:29.466Z`. Only the policy-file diff was projected from that output. It shows two local hunks in `resolve`: the docstring changes from whole-set rejection to filtering, and the validation loop changes from fail-on-unsafe to append-only-safe. No optional-resource or host-validation hunk is present in that recorded diff.

Exact recovered diff (historical output, not a Git command executed in this audit):

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

### Current code patterns and causal chain

- `backend/app/modules/cnc/browser/policy.py:65`: resolver entry point. Unknown hosts fail with the fixed `policy_blocked` value before DNS.
- `policy.py:76`: `socket.getaddrinfo` obtains all answers once for HTTPS/443.
- `policy.py:77`–87: current code deduplicates candidates, discards unsafe IPs, and returns the remaining public list. Thus `(8.8.8.8, 127.0.0.1)` returns `[8.8.8.8]` rather than refusing the answer set.
- `policy.py:88`: resolver faults are converted to fixed `ValueError(policy_blocked)`; preserve this sanitization.
- `backend/app/modules/cnc/browser/third_party/egress.py:131`: the proxy invokes the resolver in a worker thread before calling `_open_first` at line 148. Resolver `ValueError` already maps to policy refusal at line 132. A repair belongs in the policy resolver; no second DNS engine or proxy bypass is needed.
- `backend/tests/cnc/browser/test_policy_files_state.py:49`: existing test supplies explicit unsafe-only and mixed answers for 12 private/special IPs. No real OS DNS is involved.
- `backend/tests/cnc/browser/test_egress.py:26`: actual local SOCKS path asserts mixed answers return refusal, `_open_first` is not awaited, and handlers are released. Preserve these assertions.

Current policy SHA-256: `4FB0BEE64735D5338896A4B9A6AF11AF3F5BF17A2DA375A72B03492177C1666C`, matching the previous failed browser-run report. This ties the independent reproduction to the same source, not to changed network settings.

### Independent reproduction in this audit

From `backend`:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k PolicyTests -v
```

Result: **5 test methods run in 0.012s; 12 failing mixed-answer subtests; exit 1**. Four other methods pass. Every unsafe-only answer is rejected; every public-plus-unsafe pair fails its expected refusal. This deterministic mock-DNS test does not connect to providers or change DNS, business data, or production processes.

The prior broader result remains separately attributed: `research/chrome-devtools-backend-check-2026-10-23.md:45`–51 reports 94 browser tests, 12 failures, 1 egress cleanup error, and 13 skips. Do not report that broader command as rerun by this audit. The proxy cleanup error is downstream of the broken expected-refusal path; it must be retested after resolver repair before deciding whether any independent cleanup fix is needed.

### Smallest appropriate repair

Production ownership needs only `backend/app/modules/cnc/browser/policy.py`, limited to `BrowserPolicy.resolve`:

1. Restore the docstring's requirement that any private/mixed/special answer rejects the connection.
2. Keep the complete deduplicated address list; reject an empty list.
3. Validate **every** address before returning any address. If any fails the existing public/special/site-local checks, raise `ValueError`. Keep IPv6 site-local rejection even where Python reports `is_global=True`.
4. Return the full deduplicated list only after all answers pass. Preserve the fixed error conversion, hostname gate, exact DNS arguments, and absence of private-network injection hooks.

No spec behavior change is needed: browser and login specs already agree. Do not change `login/providers.py`, optional denied hosts, DNS configuration, `quote_dns_override.py`, business data, migration state, or quote adapters for this repair. Preserve all other user's or agents' edits. Before editing, compare the current resolver with the audited hash/hunk to avoid overwriting concurrent work.

### Required regressions and validation boundaries

Keep the existing failures as the first repair oracle; do not rewrite them to accept filtering. The existing tests already cover unsafe-only and public-first mixed answers, all-public deduplication, and unknown-host denial.

Useful focused additions, if absent when implementation begins:

- Reverse the mixed-answer order so unsafe-first/public-last also refuses; include actual observed `2001:2::/64` benchmark IPv6 alongside a public IPv4.
- All-public IPv4 plus IPv6 still returns deduplicated literals without a second resolution.
- Empty/malformed answers and resolver errors retain the fixed `policy_blocked` reason without raw host/error text.

Run focused policy and egress tests first, then original browser and login regressions because the policy is shared. From `backend`:

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k PolicyTests -v
.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_egress.py -v
.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_*.py -q
.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/login -p test_*.py -q
.venv/Scripts/ruff.exe check app/modules/cnc/browser/policy.py
.venv/Scripts/basedpyright.exe app/modules/cnc/browser/policy.py
```

Report opt-in Chromium and Windows symlink skips explicitly. A passing strict policy test does not establish real provider connectivity, adapter readiness, geometry, parameter fidelity, or pricing. With the temporary DNS override restored, the current machine can still return fake/benchmark answers; that is an operational blocker, not justification to relax this contract. Classification of a fake IPv4 allocated from apparently global space alone cannot prove it is a genuine provider IP.

### Files found

| File | Relevance |
| --- | --- |
| `backend/app/modules/cnc/browser/policy.py` | Sole production repair target; strict-to-filtering resolver regression. |
| `backend/app/modules/cnc/browser/third_party/egress.py` | Consumes the resolver and pins accepted addresses; existing refusal path. |
| `backend/tests/cnc/browser/test_policy_files_state.py` | Deterministic DNS contract oracle and baseline failure reproduction. |
| `backend/tests/cnc/browser/test_egress.py` | SOCKS refusal before upstream connection and cleanup oracle. |
| `backend/tests/cnc/login/test_providers.py` | Existing optional-resource/unknown-host separation checks. |
| `.trellis/spec/backend/browser-executor.md` | Strict all-answer DNS and cleanup contract. |
| `.trellis/spec/backend/cnc-account-login.md` | Login integration preserves strict DNS semantics. |
| `.trellis/spec/backend/cnc-auto-quote.md` | Shared-policy regression requirement and truthful provider acceptance boundary. |
| Task `research/operations-2026-10-23.md` | Exact temporary DNS authorization, explicitly unchanged BrowserPolicy. |
| Task `research/continuation-2026-10-23.md` | Successful restoration of temporary DNS override. |
| Task `research/provider-live-evidence-2026-10-23.md` | Observed fake/benchmark answers and explicit no-filtering boundary. |
| Task `research/chrome-devtools-backend-check-2026-10-23.md` | Previously reported failure counts and matching source hash. |
| Task `research/session-handoff-2026-10-23-chrome-devtools.md` | Continuation constraints and outstanding policy conflict. |

### External references

No new web research was needed for this internal provenance/contract question. The operations record cites official [Mihomo DNS configuration](https://wiki.metacubex.one/en/config/dns/) and [reload API](https://wiki.metacubex.one/en/api/) for its historical temporary environment operation; those pages were not reverified in this audit. Python 3.12 site-local classification behavior and its explicit guard are already recorded in the browser spec and tests; this audit does not assert a new runtime-version migration.

## Caveats / Not Found

- No explicit filtering-policy authorization or attributable tool edit was recovered. Do not present this as proof that the user never changed the file.
- No production, test, or spec file was changed. The only written artifact is this report; no Git command was run.
- No DNS/network settings, business rows, leases, upload intents, adapters, or running services were changed. No provider was contacted.
- The report supports a narrow contract-restoring repair; it does not certify provider live acceptance or a complete browser-suite pass.

## Correction: later evidence identifies the related edit

The earlier **unattributed** finding is superseded by additional authoritative local evidence supplied by the main session on 2026-10-23. The original audit above accurately records the narrower Codex-history search and its limits; it did not include the related Antigravity work in Orca same-worktree terminal `term_78bf1412-d1b1-4c2f-ab2d-148d11e6310e`.

The main session's terminal read establishes this sequence: the user requested Chrome testing of CNC account login, then asked the assistant to solve the problem rather than provide an analysis report. That assistant explicitly described changing `resolve` from rejecting any unsafe answer to filtering safe addresses and recorded an edit to `policy.py`. After a quota/model switch, the user requested continuation and subsequently said the backend had been manually restarted and asked to test whether the modification succeeded. The assistant later claimed login reached READY with filtering. This attributes the edit to that separate login-repair work; it is no longer appropriate to describe its source as unknown.

The user's continuation and post-restart testing instructions establish intent to continue and validate that modification. They **do not establish an explicit, settled user choice** between strict all-answer rejection and retaining filtering as the permanent DNS contract. The existing strict specs/tests and the filtering implementation still disagree. The main session has requested clarification of that choice; neither the earlier lack of attribution nor the login assistant's READY claim should be used to resolve it implicitly.

At the time of this correction, the main session reports that a candidate strict patch has been tested but the running backend has **not** been restarted by it. This report makes no independent verification claim about the other assistant's live login result. No terminal/history reread, production/spec/test edit, service restart, network change, or private account-data capture was performed for this correction.
