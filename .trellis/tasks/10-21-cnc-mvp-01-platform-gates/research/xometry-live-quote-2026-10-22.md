# Xometry US controlled quote evidence — 2026-10-22

Nonzero geometry and numeric quotes for A at quantities 1, 2 and 5 were reported
by the coordinator. USD is normalized from the official Customer Service
Agreement, rather than extracted as an ISO field from the price cards. Full E2
and product acceptance remain unpassed. A subsequent coordinator read after one
same-quote reload retained quantity 5, effective labels and the three tier amounts
(XU-E14); that provider UI persistence is separate from product persistence.

The initial writer transcribed coordinator observations without browser/network
access. The continuation coordinator later added direct browser evidence XU-E13/14
and the current readback appendix. No additional CAD upload or product change occurred.
Machine-readable observations and evidence IDs are in
[xometry-live-quote-result-2026-10-22.json](xometry-live-quote-result-2026-10-22.json).
Times below are UTC on October 22, 2026, with only the supplied precision.

## Authority, prior checkpoint and existing quote

Parent [D-16 user answer](../../10-21-cnc-pricing-mvp/decisions.md) confirms that
all STEP in `E:/AIWorkspace/3d_models` correspond to the page's **No** option,
including A/B/C. This is the user's factual confirmation, not an independent
export classification by this writer. D-16 is confirmed for that scope.

The earlier [live report](live-validation-2026-10-22.md) remains the historical
record of stopping before Continue. At the continuation's initial read,
**02:58:39.143**, the browser was already at an existing quote route
`/quoting/quote/{quote_id}/`, recorded here as **XU-trial-01** (XU-E01).
This continuation did not click a prior Continue, reupload A, or create another
quote; the preceding transition cannot be attributed to an actor from this read.
At **03:01:58.705**, the actual role switch for Controlled Handling read
`aria-checked=false` (XU-E02); it was retained without toggling.

The displayed filename was the known prior A,
`D14-TO-CS-ADAPTER_LP0335_P2002B.STEP`, uploaded once in the earlier trial, with
revision **v0**. Prior local fingerprints are in the
[local kernel evidence](geometry-probe-2026-10-22.md). A remote byte checksum is
unavailable: the same filename and broadly agreeing geometry do not prove
remote uploaded-byte identity. No new source-file read or fingerprint was
performed by this writer.

## Geometry and effective configuration

A displayed **28 × 25 × 5.47 mm** and **1860.85 mm³**. Sorted extents broadly
agree with the local A result at the UI's precision; this comparison is not a
remote checksum or proof of identical parser behavior.

| Field | Actual Xometry label/value |
| --- | --- |
| Initial quantity / process | 1 / CNC Machining |
| Material | Aluminum 6061-T6x (Best Available) |
| Preferred subprocess | No Preference |
| Finish | Standard |
| Threads / inserts | 0 / 0 |
| Tolerance | ±.005in (±0.13mm) |
| Roughness | Smallest 125uin/3.2um Ra |
| Inspection | Standard Inspection |

Edit Configuration at **03:02:11** showed **DFM Check Complete 8/8**, together
with a **wall thickness warning**: thin areas are cost-driving (XU-E03). This is
not a clean DFM pass or a manufacturability guarantee. No parameters were changed;
Cancel was used at **03:05:42.060** (XU-E05).

A read-only material dropdown inspection at **03:05:06** showed the selected
Aluminum 6061-T6x (Best Available), whose description allows any
6061-T6-tempered variant. Other available labels were Aluminum 6061-T651 Plate
and Aluminum 6061-T6/T6511 Bar/Rod (XU-E04). No selection changed. This record does
not declare equivalence to RapidDirect's exact 6061-T6 / ISO2768M configuration,
or equate Xometry Standard finish with the prior As machined trial intent.

## Prices, arrival labels and currency basis

All monetary amounts below are decimal strings in the JSON. They are displayed
unit prices and part line totals, not verified order totals. Arrival labels are
retained as supplied by the coordinator, without adding a year.

| Evidence / observation UTC | Quantity | Tier | Unit price | Line total | Arrival label as reported |
| --- | ---: | --- | ---: | ---: | --- |
| XU-E06 / 03:06:45.298 | 1 | economy | 170.17 | 170.17 | Nov5 |
| XU-E06 / 03:06:45.298 | 1 | standard | 401.05 | 401.05 | Oct29 |
| XU-E06 / 03:06:45.298 | 1 | fastest | 570.79 | 570.79 | Oct28 |
| XU-E08 / 03:07:12.179 | 2 | economy | 98.88 | 197.76 | Nov5 |
| XU-E08 / 03:07:12.179 | 2 | standard | 287.59 | 575.18 | Oct29 |
| XU-E08 / 03:07:12.179 | 2 | fastest | 414.07 | 828.14 | Oct28 |
| XU-E11 / 03:09:13.763 | 5 | economy | 48.74 | 243.70 | Nov6 |
| XU-E11 / 03:09:13.763 | 5 | standard | 150.43 | 752.15 | Oct30 |
| XU-E11 / 03:09:13.763 | 5 | fastest | 220.81 | 1104.05 | Oct29 |

The cards displayed **$**, without an explicit ISO currency code. The coordinator
verified the current official source on **2026-10-22**: Xometry's Customer Service
Agreement, section **4.1**, states **“All prices are calculated in US Dollars”**
(XU-E12; seven quoted words). The quote page footer links Customer Service
Agreement. Accordingly, this record normalizes currency to **USD** with an
explicit documentation basis; it does not claim direct live-card extraction.
The supplied source address is retained in XU-E12. This writer did not fetch it.
Taxes, destination and landed cost remain **null**; generic section 4.2 is not
used to infer them.

XU-E14 also displayed reference line totals and savings: economy 324.93 / 81.23,
standard 1002.86 / 250.71, fastest 1472.07 / 368.02 (reference / savings).
These are current discounted UI offers, not a verified regular-price baseline.
Promotion eligibility/duration and undiscounted-price semantics remain unknown;
quantity-1/2 savings were not transcribed and must not be inferred. See the JSON
for the preserved reference/savings fields.

## Quantity freshness and secondary state

At **03:06:59.174**, quantity changed **1→2 once** using native input, change and
blur (XU-E07). At **03:07:12.179**, quantity 2 had settled enabled tier cards with
the changed amounts above (XU-E08).

A safe read-only React price-card projection at **03:08** provided secondary
corroboration (XU-E09): `quantityOrdered=2`, `selectedTier=economy`, unit `98.88`,
extended `197.76`, actual `arrivalDate=2026-11-05`, `leadTimeDays=7`,
`productionLocation=Made Internationally`, `freeShipping=true` and
`requiresPreCheckoutReview=false`. This is not a trusted public API contract.
No cookies or tokens were accessed. The explicit year belongs only to this
quantity-2 economy state; it is not copied onto other arrival labels.

Arrival dates are not production completion dates. The meaning of
`leadTimeDays=7` (including calendar/business days and its starting point) remains
unverified. Free shipping and the pre-checkout-review flag from this secondary
state do not establish taxes, destination, landed cost or an order commitment.

At **03:09:00.830**, quantity changed **2→5 once** (XU-E10). At
**03:09:13.763**, quantity 5 had settled enabled tier cards with changed amounts
(XU-E11). The frontend remained at quantity 5 at the coordinator's last supplied
checkpoint. Subsequent verification belongs to the coordinator.

These observations support short-interval changed-quantity price freshness,
with quantity 2 additionally corroborated by component state. XU-E14 subsequently
verified quantity 5/configuration/tier readback after one reload. No validity
period, product database persistence or managed-session recovery is established.

## Checks and acceptance limits

A local Python `Decimal` check passed all **9/9** unit-price × quantity = line-total
comparisons, plus the quantity-2 economy component projection against its visible
card. JSON parsing/serialization and evidence references were checked locally.
These checks validate the recorded arithmetic and structure only.

This is controlled manual quote evidence, distinct from product acceptance.
Full E2 is not claimed: provider UI reload persistence is now observed, but
production lead-time semantics, broader baseline and product integration remain unfinished.
Promotion eligibility/duration and regular-price semantics are unverified; the
recorded discounted offers cannot be used as a verified regular-price baseline.
No product DB, Agent, automatic integration, order, checkout or
payment was exercised. Remote byte identity, cross-platform parameter
equivalence and the two-sample/two-provider baseline remain unproved. The earlier
RapidDirect zero-geometry/no-price result is not changed by this Xometry record.
The original research writer changed no shared task/configuration files or
acceptance boxes. The coordinator subsequently synchronized current records;
full acceptance criteria remain unpassed.


## Coordinator direct reload readback — 2026-10-22

XU-E13 at 03:21:18.159 UTC found quantity 5 enabled. One same-quote
Page.reload(ignoreCache=false) was then performed, without checkout or mutation.
XU-E14 at 03:23:37.878 UTC retained quantity 5, 28 × 25 × 5.47 mm / 1860.85 mm³,
all effective configuration labels above, and economy 48.74 / 243.70 (Nov 6),
standard 150.43 / 752.15 (Oct 30), fastest 220.81 / 1104.05 (Oct 29).
This confirms provider UI reload persistence for this checkpoint, not a new price
validity guarantee, remote checksum, product DB write or authenticated recovery test.
No earlier Continue/create actor can be inferred from this reload.
