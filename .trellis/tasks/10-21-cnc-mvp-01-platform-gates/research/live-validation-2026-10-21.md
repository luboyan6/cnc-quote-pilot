# Controlled platform validation — 2026-10-21

## Result and execution boundary

Task 01 is **in progress; its live entry criteria have not passed**. The user authorized sequential execution of the existing 01 → 05 tasks. This record is a feasibility result, not an implemented backend or an automated-quote acceptance report.

RapidDirect A and B returned no instant quote after Apply. Both displayed zero dimensions/volume and a placeholder preview; amount and lead time remain absent. C was uploaded once as the planned fallback and showed zero dimensions at the last observation; it was **not configured or price-tested** before the G-01 stop. Xometry's official quote entry was reachable, but account identity, upload and quotations were not verified.

Current official access/use restrictions were subsequently established for both providers. SRS G-01 requires pausing a restricted platform; applicable project permission is unconfirmed. Further automated platform actions stopped. The main session asked for the non-sensitive scope of any existing provider permission and continued only local input/configuration checks. See [terms readiness](terms-readiness-2026-10-21.md).

No purchase, checkout, payment, final order, security-setting change, manual RFQ submission or support message was performed. The quote list's generic engineering-review text is not evidence that a manual RFQ was submitted. No credentials, cookies, session export, address or CAD contents are included here.

## Input identity

Source files were read without modification in `E:/AIWorkspace/3d_models`. A/B match the earlier [candidate record](../../10-21-cnc-pricing-mvp/research/step-samples-2026-10-21.md); the local probe verifies identity, size and the explicit millimetre declaration, not CAD validity.

| Sample | Original filename | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| A | D14-TO-CS-ADAPTER_LP0335_P2002B.STEP | 300561 | `364dcf18796a0613f7453984faf66c510be980905b4f0991aa9fda06a58c8d6c` |
| B | 292.1301C (M12-TO-CS-ADAPTER).STEP | 1929001 | `d3884475c50c336e3f13e5ca1665605104dc1ccc4113e962c62bff46b21e25e6` |
| C, fallback | 292.1001A (CS ring 5mm).STEP | 3609635 | `038fe7d3d464c57bfc0cb0856954f1f6bbf78b152f6db9a67ede92dbd8ea7cc7` |

C is not a newly frozen acceptance sample. A/B/C geometry and DFM have not passed; the two-file common baseline remains unfrozen. No source repair, scaling, conversion or re-upload of A was performed.

## RapidDirect observations (UTC)

Origin `https://app.rapiddirect.com`, path `/quote/detail3.0`. Existing quote alias: `RD-trial-01`; this private workspace record keeps no account identity or session material.

| Time | Action / observation | Result |
| --- | --- | --- |
| 09:14:32 | Reopened the existing quote through View quote | A row still showed zero dimensions and no material/roughness; no duplicate A upload |
| 09:15:09 | Opened A's row-scoped Configure | CNC, 6061-T6, Ra3.2, quantity 1 visible; zero dimensions/volume and placeholder image |
| 09:16:54 | Clicked A Apply once for diagnostic configuration/quote observation | Geometry remained unverified; this action did not establish a successful geometry gate |
| 09:17:08 | Read post-Apply form | Finish read back as Not required; additional required fields appeared; USD placeholder and explicit no-instant-quote message; no numeric amount or lead time |
| 09:17:50–09:18:01 | Saved A configuration once; returned to quote list | Basic parameter readback persisted; generic engineering-review text displayed; no manual RFQ requested |
| Before 09:20:07 | Uploaded original B once through the observed CAD upload input | B row appeared with zero dimensions; upload accepted is not parse success |
| 09:21:19 / 09:22:51 | Opened B's own expanded-row Configure and clicked Apply once | Same CNC/6061-T6/Ra3.2/quantity 1 trial; no instant quote |
| 09:23:59–09:24:24 | Changed B quote-panel quantity to 2 and reread it | Panel value/ARIA read 2, while edit form still showed 1; amount remained absent |
| 09:25:06–09:25:35 | Changed B quote-panel quantity to 5 and reread it | Panel read 5; same no-price branch; no successful recalculation or saved-effective-quantity claim |
| 09:26:12 / 09:26:34 | Restored B panel quantity to 1 and saved configuration once | Returned to list; no manual RFQ requested |
| Before 09:27:41 | Uploaded original fallback C once | C row showed zero dimensions; no Configure/Apply/price trial followed because of G-01 |

A's previous observation was hours earlier, but that does not prove continuous waiting. B/C elapsed time was not a completed ten-minute parsing experiment. No site-wide parser outage, corrupt source CAD or root cause is inferred from these results. No automatic retries, repeated uploads or refresh loops were used.

### Post-Apply parameter readback

| Field | Observed selected label / state | Qualification |
| --- | --- | --- |
| Process / material | CNC Machining / Aluminum 6061-T6, 3.3211, AlMg1SiCu | Existing process/material catalog IDs belong only to RapidDirect |
| Finish / roughness | Not required / As machined (Ra3.2) | Separate fields; empty initial Finish selection was read back after Apply and A save |
| Cosmetic part / inserts | No / No | Observed page selections, not inferred defaults or frozen requirements |
| Tightest Tolerance | ISO2768M | Other displayed labels: ISO2768C, ISO2768F, custom with drawing; IDs/equivalence unverified |
| Threads and Tapped holes | No threads | Standard/custom choices require 2D drawings; this trial does not establish functional thread requirements |
| Marking / inspection | Empty selections | Semantic absence and execution mappings remain unverified; page says inspection reports add a fee and require manual quotation |
| Quantity | A saved 1; B restored/saved 1 | B panel values 2/5 alone did not establish saved parameters or a new quotation |
| Commercial context | USD displayed next to a missing amount | No actual price; unit/line amount, tax, shipping, destination and production/delivery time remain unknown |

Runtime interpretation of the observed no-price branch is `NO_QUOTE`, not `QUOTED` or a submitted `PENDING_REVIEW`. No product task/item/quote rows exist yet. A successful `Freshness` state is not established; none of these trials may count toward monitoring success, throughput or AC-01/02.

### Evidence

- [A zero geometry before Apply](evidence/rapiddirect-a-geometry-zero.png)
- [A post-Apply no instant quote](evidence/rapiddirect-a-no-instant-quote.png)
- [B no instant quote with panel quantity 5](evidence/rapiddirect-b-no-instant-quote-qty5.png)

Screenshots were captured from the bounded configuration region, excluding the account/header. They contain no actual CAD rendering. File hashes and exact screenshot dimensions are checked in the local verification report. They are private engineering evidence, not a public artifact or product evidence-service implementation.

## Xometry US observations (UTC)

At 09:22:53 the official `https://www.xometry.com/` page exposed its quote entry. Clicking the unique small header Get an Instant Quote button at 09:23:07 navigated to `https://www.xometry.com/quoting/home/`. At 09:24:22 the page showed Dashboard, No Quotes Yet and CAD-upload/Start Instant Quote controls.

This does not establish whose account is authenticated, a valid reusable session, an accepted CAD file or a quote. No upload, registration, credential entry, identity inspection, quote submission or new host allowlisting occurred. Existing planned `login.xometry.com` entries remain unverified; only the observed `www.xometry.com` entry/path was updated. Further automated data collection awaits the G-01 condition.

## G-01–G-07 matrix

| Gate | RapidDirect | Xometry US |
| --- | --- | --- |
| G-01 terms/identity/use | **Not passed**: current access/use restrictions; applicable provider permission unconfirmed. User supplied account/sample authorization, but site permission is a separate recorded condition | **Not passed**: current scraping/competitive-service restrictions; applicable permission and authorized account identity unconfirmed |
| G-02 reachability/login/session | Existing business page reached; close/reopen isolated-context session reuse and reauthentication not tested | Official quote entry reached; identity, login challenges and session reuse not tested |
| G-03 upload/geometry | A already present, B/C uploaded once; all last-observed dimensions zero. Geometry gate not passed | No upload performed; not tested |
| G-04 shared parameters | Basic and post-Apply labels observed; additional IDs/dependencies, alternate material and cross-provider common specification not frozen | Catalog/configuration not observed |
| G-05 actual quote/boundary | A/B no instant quote, no amount/lead time; C not price-tested. No order/payment or manual RFQ | No actual quote; not tested |
| G-06 deterministic controls | Row-scoped Configure, CAD input, Apply and Save configuration exercised; successful geometry/result extraction remains unverified | Only official entry and upload affordance observed; no adapter verified |
| G-07 freshness | B panel 1/2/5 readback did not establish recalculation; no successful fresh quote | Not tested |

## Acceptance and handoff

| Criterion | Current conclusion |
| --- | --- |
| V-01 | A timestamped pass/fail/pending matrix now exists; substantive platform gates remain unmet |
| V-02 / V-03 | Not passed: no explicit real quote, no validated common two-sample set, incomplete effective-parameter mappings |
| V-04 | Providers are distinct (`rapiddirect` / `xometry`); Xometry E2 is not established |
| V-05 | No invented prices/selectors/performance; bounded trials and planned fallback recorded; stopped on G-01 |
| V-06 | Configuration/evidence handoff updated; secrets excluded; this is not a passed E2/E3 handoff |
| V-07 | SDK/Python/provider/checkpoint prerequisites and gaps recorded in [runtime readiness](runtime-readiness-2026-10-21.md); normal/exception stopping positions below |

Workflow handoff: S04 WAIT_GEOMETRY cannot pass on upload-row presence or zero geometry. Apply can reveal further S05/S06 configuration/readback fields; do not freeze only the initial form. No-price follows E07; unavailable model recovery follows E12 as documented in the parent workflow. E01/E02 identity/challenge, E03 remote failures, E09 uncertain receipt and E11 restart were not injected or tested. All other E01–E13 and TC-WF/TC-DA assertions remain pending task 02; these human-controlled diagnostics are not evidence of a running Workflow or Agent.

## Next executable step

1. Resolve G-01 for each provider using an existing applicable authorization or an approved alternative. No account registration or support contact is implicitly authorized.
2. For an eligible provider, resume at read-only inspection of the existing remote sample/configuration. Revalidate identity, geometry and effective parameters; never blindly upload A/B/C or resubmit an uncertain side effect.
3. Establish at least the first provider's complete E2/explicit quote and changed-parameter result before entering task 02's product implementation; Xometry E2 is additionally required before task 03.
4. Keep tasks 02–05 approved but awaiting their documented dependencies. Do not replace the real-quote entry condition with a fixture, UI, generic Agent or static input check.
