# Xometry B quote PDF viewer evidence — 2026-10-22

The existing B quote's PDF viewer supplies quote-specific **8 business days**, a
conditional ship date, part reference and offer validity. The encrypted page-1
viewer screenshot is preserved locally. **No raw PDF download succeeded and no
raw PDF archive is claimed.** Full E2, G-02 and product acceptance remain unpassed.

The coordinator performed the browser navigation, visual inspection, accessibility
reads and DPAPI protection. This author transcribed the supplied observations and
checked local ciphertext, ignore status and structured-record arithmetic without
opening a browser, decrypting an image or inspecting credentials. The sanitized
[JSON record](xometry-b-pdf-evidence-2026-10-22.json) separates these evidence sources.
Prior upload/hash/quantity observations remain in the
[B controlled report](xometry-b-live-quote-2026-10-22.md) and
[prior B JSON](xometry-b-live-quote-result-2026-10-22.json).

## Provenance and preservation

The coordinator clicked the existing quote's **Download PDF** UI control. It
navigated to the observed `api.xometry.com` path
`/v2/quotes/Q78-4652-8737/generate_pdf` and displayed a two-page PDF viewer. This
was normal UI navigation, not a constructed/replayed API request or proof of a
public API contract. The newly observed host was not added to a runtime allowlist.

The page-1 quote-details area was missing from accessibility text. The
coordinator's visual read of that area is decisive for XU-BPDF-E01. Effective
configuration and page-2 restrictions were read from PDF-viewer accessibility text
(XU-BPDF-E02); no independent page-2 screenshot is claimed.

| Artifact fact | Recorded value |
| --- | --- |
| Capture time | 2026-10-22T07:05:33.819Z |
| Private relative reference | `evidence.local/xometry-b-economy-pdf-page1-20261022.png.dpapi` |
| Original PNG SHA-256 | `23ce1aea119136962137ee47d2be7a49cd4d43945bbb50006dc47c652cd2a835` |
| Encrypted-file SHA-256 | `0307025453ae9321147e783cddf0c0be1d9230703524ec21eb2003a2fb2b8cec` |
| Protection | Windows DPAPI CurrentUser; coordinator reports byte-identical encrypt/decrypt roundtrip PASS |
| Author checks | Encrypted-file byte hash matches; `git check-ignore` PASS; no image decryption/read |
| Preservation limit | Encrypted screenshot of page 1 only; raw PDF absent; these hashes are not PDF hashes |

The screenshot may contain private account fields. It stays in the ignored local
directory; this sanitized register stores no name, email, address or raw account
identifier. CurrentUser protection is local to the relevant Windows user and is
not a claim of portable backup, retention policy or product evidence storage.

## Same-offer visual fields

| Field | Coordinator-observed PDF value |
| --- | --- |
| Quote | Q78-4652-8737; research alias XU-trial-02 |
| Quoted on | 10/22/2026 3:04 AM EDT |
| Sample | `292.1301C (M12-TO-CS-ADAPTER).STEP` |
| Part / version | 4B3F930 / 0 |
| Origin | Made Internationally |
| Geometry | 28 × 25 × 9.50 mm; 1970.97 mm³ |
| Quantity / tier | 5 / Economy |
| Struck original unit amount | 78.96 |
| Current unit / part line | 59.22 / 296.10 |
| Shipping | Calculated at checkout |
| Lead time | 8 business days |
| Ship date | Tuesday, Nov. 03 |
| Online ordering condition | By 11:59 PM EDT on Thursday, October 22 |
| Email ordering condition | Order requests emailed to support after 8 PM EDT are processed the following business day |

USD retains its prior explicit documentary basis: XU-E12, official US Customer
Service Agreement §4.1, plus the US offer context. No direct PDF ISO-code extraction
is claimed. These are unit and parts-line amounts, not a landed/order total. Tax,
shipping amount and destination remain unknown. The struck amount is not a verified
undiscounted regular-price baseline; no campaign eligibility/expiry is inferred.

The 8–8 business-day range is directly observed. A production starting event is
not established, and the label is not silently expanded to “production duration.”
The ship date and ordering cutoff remain separate raw fields; the ship-date year
was not explicitly printed in the supplied observation and is not inferred here.
The 11:59 PM online cutoff and 8 PM email condition describe different paths.
No email was sent. No transit days, holidays, order acceptance time or guaranteed
arrival are calculated from them. This evidence applies only to B, quantity 5,
Economy; it does not overwrite A's raw 7 or any other tier/quantity.

## Configuration and PDF restrictions

The PDF accessibility read gives the same B configuration labels as the prior
controlled report: CNC Machining, No Preference, Aluminum 6061-T6x (Best Available),
Standard finish, threads 0, inserts 0, ±.005in (±0.13mm), Smallest 125uin/3.2um Ra
and Standard Inspection. JSON normalizes formatting for review; it is not a claim
of a byte-for-byte full PDF transcript or new material/finish selection test.

The coordinator read the following page-2 restrictions: price valid for 30 days
since generation; estimated delivery window recalculated at actual order; the
model does not automatically extract threads or nongeometric specifications;
duties/fees are the customer's responsibility. These are scoped transcriptions,
not reproduced full PDF text. No expiry timestamp, delivery guarantee, tax amount
or landed amount is invented from those statements.

The explicit generation label does not prove a new pricing calculation. Current
unit/line amounts match the earlier quantity-5 UI offer. Prior changed-quantity
freshness and same-quote reload evidence keep their original limited meaning;
this PDF is not a new automatic monitoring cycle.

## Separate clean login-entry observation

At approximately **07:11 UTC**, the coordinator's clean Playwright page reached
`login.xometry.com/u/login/identifier` and showed Business Email, Continue and
Google controls. No email was submitted. Password/OTP stages, account identity,
login recovery and managed-session restoration were not observed. This narrows
the G-02 entry-page unknown; it does **not** complete G-02 or F-03/TC-02/11.

## Subsequent account-to-PDF association

The coordinator's restored CDP channel read the same profile's `/user-settings`
at **07:37:43.336 UTC** (XU-ACCOUNT-E01). The observed email was normalized to
lowercase and fingerprinted **inside the browser** using SHA-256 of the prefix
`cnc-task01-xometry-account-v1:` followed by that normalized email. Only the
anonymous fingerprint was returned and recorded:

`e2c0d68bdb99a33f28381a7b97598e5b2d0692ef13d7d722feb6fe3dc308affa`

At **07:38:06.499 UTC**, an in-browser comparison between that settings email
and the PDF's Prepared For email returned **true** (XU-ACCOUNT-E02). No raw name,
email or account identity was saved in the sanitized evidence. These direct
browser observations establish the observed account-to-PDF email association;
they are separate from the earlier PDF screenshot capture and do not independently
establish legal ownership or a new permission basis.

Settings visibly stated **Your email is not verified** and **Verify your email to
activate Multi-Factor Authentication**; the Email MFA switch was false. This
prevents claiming a fully verified/activated account or enabled email MFA. It
does not establish inability to quote: existing B quote reachability was already
observed. No verification was sent and no security setting changed.

The account holder answered **“可以在浏览器中完成”**: ability to complete email
verification/challenge in the browser is now user-confirmed
(`user_confirmed_browser_takeover_available`). This is a factual capability
confirmation, not successful verification or a repeat D-15 permission request.
No OTP is requested in chat. Password/OTP stages,
ordinary login recovery and managed-session restoration remain untested; these
reads do not complete G-01/G-02. The screenshot-only preservation and absent raw
PDF limits above remain unchanged.

## Checks and handoff

Local checks passed encrypted artifact SHA-256, ignore status, strict JSON loading,
evidence-reference/link consistency, Decimal `59.22 × 5 = 296.10` and exact match
to the prior B quantity-5 Economy amounts. Supplemental checks passed the exact
account fingerprint/timestamps, email-match boolean, unverified-email/disabled-MFA
state, user-confirmed browser takeover status and absence of email values in the JSON. The DPAPI roundtrip and original PNG
hash are coordinator-reported; this author did not rerun decryption. No application
tests, model calls, database access or browser actions were performed by the author.

The [handoff gap matrix](first-provider-handoff-gap-2026-10-22.md) now references
this registered screenshot and account-linkage evidence. The observed account/PDF
email association and user-confirmed browser takeover availability are recorded;
successful verification/challenge recovery, activation limits,
mapping/version, price-nature/review-state and consolidated same-observation evidence
gaps retain their own requirements. A remote source-byte checksum is unavailable and is not
invented as a prerequisite. No checkout, formal order, payment, manual RFQ or
account-security change occurred to collect this PDF-viewer evidence. Actual
runtime/DB/secure-session/Agent integration remains 02 work.
