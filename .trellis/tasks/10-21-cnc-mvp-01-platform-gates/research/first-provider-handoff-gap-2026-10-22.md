# Xometry US first-provider handoff: evidence gaps

Date: 2026-10-22. Scope: review of existing repository evidence only. No browser,
account, model, database, platform configuration or acceptance state was changed.
This report does not pass E2 or authorize enabling the draft adapter.

## Decision and acceptance boundary

[D-15/D-16/D-17](../../10-21-cnc-pricing-mvp/decisions.md) already authorize the
existing controlled work, the specified STEP directory's No declaration and the
Xometry US first / JLC-CNC China second order. Repeating those permission questions
is unnecessary. The recorded permission basis is user confirmation, not an
independently reviewed provider agreement or an independent export classification.
RapidDirect is deferred and its failed geometry is not a first-provider blocker.

The [01 PRD](../prd.md), [01 design](../design.md) and
[02 PRD](../../10-21-cnc-mvp-02-first-quote/prd.md) require the first-provider
G-01–G-07/E2 evidence before 02, while explicitly assigning product authentication,
encrypted sessions and context reconstruction to 02/03. They permit first-provider
handoff before the second provider passes. Full two-provider baseline acceptance,
E3, application persistence and actual Agent recovery are later deliverables.

The [SRS](../../../../CNC_Competitor_Pricing_Agent_SRS_Design_v1.0.md) is more precise
than some historical remaining-work lists:

- Section 2.1 defines E2 as an authorized account and uniform STEP manually walked
  through with timestamped evidence; E3 requires repeated automation and human checks.
- Section 2.4 G-03 requires at least one recognized sample for initial feasibility;
  both are required for the final frozen baseline. G-05 requires an explicit quote
  and explanatory lead time before formal order/payment. The ten-minute suggestion
  is not an observed SLA or a new mandatory duration threshold.
- Section 1.5 distinguishes production working days, shipment dates, arrival dates
  and calendar days. Sections 3.3 and 5.4 require the raw lead time and its type.
  Section 6.2.6 stores production/shipment/arrival types and permits nullable
  provider quote/expiry timestamps.
- Section 5.4 and Appendix B require source/evidence association, an anonymous
  account fingerprint, time, region, parameter version, quote reference, operator
  and conclusion. A remote byte checksum, legal-identity document, product DB row
  or successful live model call is not specified as an E2 prerequisite.

## Gate matrix

Statuses below concern the first-provider evidence package, not application success.
The coordinator subsequently supplied the same B quote's UI-opened PDF-viewer
findings listed below. The encrypted page-1 screenshot is now registered in
[PDF evidence](xometry-b-pdf-evidence-2026-10-22.md) and its
[sanitized JSON](xometry-b-pdf-evidence-2026-10-22.json). No raw PDF download succeeded
and no raw PDF archive is claimed. Findings retain their visual/accessibility
provenance and author/coordinator distinction.

| Gate / subject | Existing evidence | Exact remaining 01 evidence | Obligation belonging to 02 or later |
| --- | --- | --- | --- |
| G-01 permission and account identity | D-15 scope and D-16 No are confirmed. Subsequent direct settings reads at 07:37:43.336 UTC produced the anonymous account fingerprint in the PDF register; at 07:38:06.499 UTC an in-browser settings-email/PDF-Prepared-For comparison returned true. Observed account/PDF email association is complete. User answered “可以在浏览器中完成”, confirming browser takeover capability. Settings still state email unverified and email verification required to activate MFA; Email MFA is false. | Preserve the distinction between user-confirmed ability and successful verification/recovery, which has not occurred. Do not claim full account activation or legal ownership from the matching email. Do not infer inability to quote from the unverified-email label; existing quote reachability is observed. No verification/security mutation was made and no OTP is requested in chat. Preserve the user-confirmed permission basis; do not repeat D-15 authorization or invent agreement/identity facts. | Account DTO/grants, encrypted credentials, production identity verifier and security/ACL tests. No need to implement these to document 01 feasibility. |
| G-02 reachability and login feasibility | Official US entry and A/B quote pages were reached. Same-quote reload retained results. At approximately 07:11 UTC a clean Playwright identifier page showed Business Email, Continue and Google; no email was submitted and no password/OTP stage was observed. | Record the ordinary login/challenge mechanism's remaining unknowns and the feasible recovery path; identifier controls alone do not complete G-02. Original SRS G-02 asks for manual close/reopen context reuse **or** clearly implementable login recovery. The current parent/child clarification places product encrypted-state reconstruction in 02; a reload is neither manual context reconstruction nor proof of product reuse. | F-03 and TC-02/11 implement and demonstrate managed state, expiry, account isolation, challenge pause and reauthentication. These are not conditions to first write 02. |
| G-03 source identity, receipts and geometry | [A](xometry-live-quote-2026-10-22.md) has exact filename/v0, prior local fingerprints, quote XU-trial-01 and nonzero geometry. [B](xometry-b-live-quote-2026-10-22.md) records source SHA-256/size, one native upload, ready receipt, one start/No Continue, quote XU-trial-02 and nonzero geometry. The coordinator's later PDF read additionally binds B filename, part 4B3F930/v0 and geometry to the quantity-5 Economy offer. Local [kernel evidence](geometry-probe-2026-10-22.md) keeps source identity separate from remote parsing. | Consolidate authorized local hash/size/mm, actual selected filename, upload receipt, remote quote/part association and geometry in the same sample chain; register the PDF evidence. B is the stronger attributable chain; A's prior Continue actor stays unknown. Remote byte hash is unavailable and is **not** an invented gate. A has a thin-wall warning; B has eight Passed labels. Neither is a production guarantee. | Verified-buffer SDK upload, durable upload intent and receipt reconciliation, source ACL and runtime geometry validation. |
| G-04 parameters and mapping | A/B show CNC Machining, 6061-T6x (Best Available), No Preference, Standard finish, 0 threads/inserts, ±.005in, 3.2um Ra and Standard Inspection; quantities 1/2/5 were observed. [Control evidence](xometry-controls-2026-10-22.md) adds tolerance exceptions, switches and certificates. | Freeze the actual first-provider requested/effective snapshot and version, including all required/default fields, tier and commercial context; retain tolerance exceptions and the material's allowed temper variants. Establish a supported second-material selection/mapping and finish semantics/dependencies with evidence rather than the presence of dropdown labels alone. Existing Cancel-only reads do not prove saving a different material/finish. Cross-provider equivalence and the two-provider common set remain explicitly unfrozen; JLC completion is not required to hand off the first provider. | Trusted JSON loader, version/hash pinning, exact mapping, dependency rereads, Apply/save and runtime full-field assertions; TC-CFG and F-02/F-07. Runtime binding need not already exist in 01. |
| G-05 price nature | A/B have positive single-value unit/line tier offers, changed-quantity readings and savings/reference totals. They are observed discounted offers, not a verified regular-price baseline. No manual RFQ/checkout/order/payment was made. | Bind one current offer's visible amount, quantity, tier, price-nature/review indicators and stop boundary to its same configuration/evidence. Preserve any displayed validity/restrictions; where absent, record unknown rather than fabricate expiry. Confirm that the amount is an available configured quote rather than a reference-only estimate/range or pending review. Savings alone neither proves reference-estimate status nor establishes ordinary undiscounted pricing. | Deterministic nature classifier and validators; no promotion changes or inferred regular-price history. JLC's explicit reference-estimate disclaimer remains a separate second-provider failure. |
| G-05 currency and scope | XU-E12 records official US CSA §4.1 supporting USD; cards show $. Unit × quantity = line amount passed 9/9 for each sample. | Carry the documentary USD basis and the observed parts unit/line scope into the same snapshot. Tax, destination, shipping cost and landed total remain unknown unless actually evidenced. Record region/context limits; do not demand a checkout-derived landed total for a parts-only quote. | Decimal storage, scope/currency parsing and null handling; history grouping prevents strict comparisons when commercial context is unknown. |
| G-05 lead-time semantics | Earlier A/B evidence has month/day arrival labels; A quantity-2 raw `leadTimeDays=7` lacks verified meaning. The coordinator's later B PDF visually shows Economy, **8 business days**, **ship date Tuesday Nov 03**, conditional on online ordering by **11:59 PM EDT Thursday Oct 22**. The encrypted screenshot and sanitized register preserve this quote-specific evidence. | Carry the registered quote/part/quantity/tier association and conditions into the consolidated handoff. Do not keep searching for a missing duration as if the PDF evidence were absent. Retain the explicit business-day range 8–8 and raw shipping condition; do not invent a duration starting event or infer that the label explicitly means production if it does not say so. A and other tiers/quantities remain separately scoped unknowns. Raw PDF bytes remain absent, not an invented download success. | Ensure typed duration/start-event/date semantics preserve these limits. The existing numeric type can hold 8/business_days, but it cannot represent the full ship-date/cutoff distinction alone. Reconcile the wider SRS shape before enabling an adapter rather than manufacturing arrival-to-duration conversions. |
| G-06 deterministic controls | Native upload and quantity controls worked in controlled trials; Edit Configuration and tolerance options have scoped DOM projections. React option IDs are transient. | Verify unique scoped key controls/result regions and keep sanitized structure evidence. Current projections are candidates, not validated production bindings; full catalog enumeration is not itself a gate. The latest configuration Cancel lacks its own independent post-Cancel readback. | Implement stable Playwright locators and actual extraction bindings, tested variants and stop-on-ambiguity behavior. Do not freeze React-generated IDs as business constants. |
| G-07 freshness | A XU-E07–11 and B timestamped 1→2→5 changes show changed, settled amounts; both quantity-5 states survived one reload. | Preserve the actual mutation/readback linkage and any current quote version/update/recalculation completion evidence. Distinguish changed-quantity re-quote evidence from same-parameter repricing: a reload alone is not a new pricing event or a monitoring proof. | Runtime CURRENT_CONFIRMED/RECALCULATED proof, durable intent, restart behavior, and two independent monitoring cycles in 04; no replay of uncertain mutations. |
| Evidence completeness across gates | A/B Markdown and JSON contain quote aliases/IDs, timestamps, amounts and parameter labels. The new PDF register adds the locally encrypted page-1 screenshot, capture time, original/ciphertext hashes and part ID. Its sensitive raw image is ignored; no raw PDF exists. | Link this screenshot/register with parameter evidence and the consolidated local file SHA, anonymous account reference, region, parameter/mapping version, operator, observation time and quote/part reference. Full PDF parameter/page-2 fields are coordinator accessibility transcriptions, not captured page-2 screenshots. Do not claim all account/version evidence is now supplied by one image. | Transactional result/evidence persistence, ACL, retention and UI access. Private raw state/CAD/auth material must not be committed as research evidence. |
| V-07 SDK/provider/checkpoint conditions | [SDK probe](sdk-probe.md) executed real 0.7.29 factory, restricted fixture tools, typed decision and cross-process file-backed DeltaChannel checkpoint. Real provider tool calling was not run; settings presence booleans are not authentication evidence. [Runtime readiness](runtime-readiness-2026-10-21.md) retains its historical package snapshot. | Carry actual versions, isolation/tool lessons, Python compatibility and explicit NOT_TESTED provider/protocol/Skills/business-recovery conditions. V-07 accepts actual results **or recorded blockers**; do not substitute an old backend package snapshot for the later fixture result. | Resolve application dependencies together and recheck current stable metadata, bind server-owned model reference, run actual tool calling and guarded recovery, durable budgets/permissions/idempotency. Live model success and product Agent persistence are not 01 account/quote prerequisites. |

## Subsequent coordinator evidence: existing B quote PDF

During this review the coordinator used the existing B quote's **Download PDF**
UI control, without checkout. The coordinator visually inspected the quote-details
area, which the accessibility tree omitted, and reported:

| PDF field | Reported visual observation |
| --- | --- |
| Offer | Economy; B's full filename; part ID 4B3F930, version 0 |
| Geometry / quantity / USD unit and line | 28 × 25 × 9.50 mm / 1970.97 mm³; quantity 5; struck unit 78.96, current unit 59.22 / line 296.10 |
| Shipping | Calculated at checkout |
| Origin | Made Internationally |
| Lead time | 8 business days |
| Ship-date condition | Tuesday Nov 03, when ordering online by 11:59 PM EDT Thursday Oct 22 |
| Email condition | Order requests emailed to support after 8 PM EDT processed the following business day |
| Quote generation | QUOTED ON 10/22/2026 3:04 AM EDT |
| Footer limits | Price valid 30 days since generation; delivery window recalculated at actual order |

These are **coordinator-supplied findings**, not browser observations performed by
this report's author. The [registered screenshot](xometry-b-pdf-evidence-2026-10-22.md)
was captured at 07:05:33.819 UTC; its encrypted-file hash and ignored status were
verified locally by this author without decryption. Quote-details fields came from
visual inspection, configuration/restrictions from PDF accessibility reads. No raw
PDF was downloaded successfully. The screenshot's PNG/ciphertext hashes are not
PDF hashes; page-2 visual preservation is not claimed.

This narrows the immediate missing work substantially: B now has an actual
numeric business-day lead time and a distinct conditional ship date. It also has
an offer-specific validity statement, unlike the earlier generic public policy.
Do not copy 8 into A, other quantities or other tiers. Do not infer a production
start event, timezone beyond the printed EDT condition, a guaranteed arrival or
an arithmetic mapping to the earlier Nov 9 arrival label. Use the printed ship
date and quote-generation context without deriving an unstated calendar. A private
PDF can contain account/address details; only sanitized fields and private artifact
references belong in the evidence register.

## Can an arrival date satisfy the explanatory lead-time requirement?

**Yes, for the SRS G-05/E2 lead-time semantic slice, if it is verified as this
offer's platform-reported arrival estimate.** The SRS definition expressly includes
arrival dates; G-05 does not require every provider to expose production duration.
A typed arrival estimate with raw text and documented limitations is different
from “no lead-time semantics.” Unknown production days do not justify calculating
them from observation time or subtracting generic transit days. An estimated
arrival date does not itself make an otherwise explicit price a reference estimate;
price nature must be classified from its own evidence.

This is a source-contract interpretation, not a declaration that the existing
month/day labels already complete E2. The later B PDF offers a stronger duration
route, so an arrival-only interpretation is no longer necessary to fill B's
numeric evidence gap now that its visual screenshot and sanitized register are
preserved. The other matrix
gaps still require disposition. Do not infer B's year from A or
extend A's quantity-2 hidden value to another tier/quantity. General official
shipping help and a hidden field name cannot establish a specific production SLA,
cutoff, holiday calendar or guaranteed arrival. Preserve unknowns where the SRS
does not require a conversion. The SRS's nullable `valid_until` similarly does not
license inventing an offer-specific expiry from a generic policy. B's newly
observed PDF validity statement must instead be bound to its own generation event
and any stated conditions.

There is an actual downstream conflict. The implemented
[LeadTime](../../../../backend/app/modules/cnc/browser/contracts.py) has required
`minimum_days`, `maximum_days` and `DayBasis` (business/calendar). Its
`ValidatedQuote.as_dict()` serializes that duration-only shape. The implemented
[validate_quote](../../../../backend/app/modules/cnc/browser/workflow.py) rejects
absent/nonpositive ranges or unknown basis. Neither supports a typed arrival date.
The [browser spec](../../../spec/backend/browser-executor.md) requires known lead
time, while the [CNC spec](../../../spec/backend/cnc-validation.md) explicitly
assigns this duration-only mismatch to 02 before adapter enablement.

Historical A/B remaining lists and the 01 checklist specifically seek *production*
semantics, whereas the SRS allows production/shipment/arrival distinctions. The
coordinator must record the evidence-backed interpretation and reconcile affected
implementation contracts when 02 consumes the handoff. This report changes none
of those artifacts, lowers no gate, and cannot make the current duration validator
accept dates. Requiring product code first to document 01's manual feasibility
would invert the current task boundary.

## Minimum safe next reads

1. Reuse the registered encrypted B PDF-viewer screenshot and sanitized fields;
   preservation of that image is complete. Raw PDF absence remains explicit and
   does not justify repeating the quote or pretending a download succeeded. If
   resuming after another tool failure, first
   read the existing B route/dialog state and quantity rather than replaying an
   action. No new upload/start/Continue/Apply is needed.
2. Reuse the now-registered anonymous settings/PDF email linkage; do not repeat the
   identity read merely to produce a fingerprint again. Record the account holder's
   now-confirmed browser takeover capability and preserve the unverified-email/
   disabled-MFA labels. Successful verification is not claimed and no OTP is
   requested in chat. No verification/security change is implied. Do not export
   Cookie/storage state or copy raw identity. Managed context reconstruction remains
   a product test rather than evidence already supplied by these account reads.
3. Use the same-quote PDF's actual duration, ship condition and validity evidence;
   inspect any still-missing discount/review restrictions in read-only details.
   Keep arrival versus shipment distinct. Stop before checkout,
   purchase, formal order, manual RFQ or security changes. If details are absent,
   retain the absence and limitation; do not seek them through an order flow.
4. Read current effective configuration and scoped controls/option descriptions
   without selecting/saving; after closing an already-inspected panel, independently
   read back the same quote. Capture/redact the required result/parameter evidence
   privately and register its source/version/account association. Current option
   descriptions can narrow mapping gaps but cannot prove an unexecuted save.

These reads can complete documentation and semantic gaps. A supported second
material/finish save and fresh re-quote, if still required after the read, is a
separate bounded existing-scope mutation with receipt/readback guards; it is not
pretended to have happened in this read-only report. Any unknown mutation receipt
requires reconciliation before another action. Existing authorization continues;
there is no recommendation to repeat D-15/D-16/D-17 approvals.

## Local verification

The document's local Markdown targets and required gate references were checked.
No application tests were needed for this research-only addition; existing live,
SDK, component and product tests were not rerun or promoted to a broader pass.
