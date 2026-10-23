# Xometry B controlled quote — 2026-10-22

B now has nonzero platform geometry and numeric quotes at quantities 1/2/5,
with quantity 5 retained after a same-quote reload. This is controlled feasibility,
not product automation, a regular-price baseline or two-provider acceptance.
Machine-readable evidence is [the B result](xometry-b-live-quote-result-2026-10-22.json).
All times below are UTC on October 22, 2026.

## Identity, authority and actions

Original B, `292.1301C (M12-TO-CS-ADAPTER).STEP`, was read-only rechecked as
1,929,001 bytes and SHA-256
`d3884475c50c336e3f13e5ca1665605104dc1ccc4113e962c62bff46b21e25e6`.
D-15 covers the existing controlled quotation scope. D-16 is the user's explicit
confirmation that STEP in the supplied directory use the page's No classification;
no independent legal/export classification was made.

The dashboard initially listed only A's existing quote. At 03:33:43.405 the
coordinator opened Get an Instant Quote once. Original B was selected once via
the observed native input; the exact filename and 1 part ready were read before
Start Instant Quote was clicked once at 03:35:23.716. The declaration dialog was
read at 03:35:37.143, confirming No selected (`confirmed-not-itar`). Continue was
clicked once at 03:35:49.616 on D-16's basis. This is an actual B declaration
submission, unlike the unknown earlier actor for A's transition.

New quote Q78-4652-8737 (alias XU-trial-02) was observed analyzing geometry.
The browser wait request returned after an anomalously long tool delay, despite
its 30-second timeout setting; no parsing duration/SLA is measured from this gap.
The first settled direct read was at 04:33:05.206. No retry upload/start/Continue
was attempted. Remote byte checksum/identity remains unproved.

## Effective parameters and DFM

The page displayed one part, v0, CNC Machining, Aluminum 6061-T6x (Best Available),
No Preference subprocess, Standard finish, threads=0, inserts=0,
±.005in (±0.13mm), 125uin/3.2um Ra and Standard Inspection.
Geometry: 28 × 25 × 9.50 mm; 1970.97 mm³. Local B volume was about 1970.919831
mm³; the small difference is recorded, not treated as exact equality or proof of
remote byte identity. No requested functional thread/fit was inferred from filename.
Exact equivalence to RapidDirect 6061-T6/ISO2768M has not been established.

Edit Configuration was opened at 04:35:21.536 only to read DFM. At 04:35:32.809,
DFM Check Complete (8/8) listed Passed for Void, Large Part Dimension, Wall
Thickness, Model Fidelity, Floating Parts, File Type, Model Shell Count and Part
Exceeds Maximum Size for This Finish. These are platform checks, not a production
manufacturability guarantee. No configuration changed; Cancel at 04:35:45.383.

## Numeric offers and arrival labels

Amounts are decimal strings, unit / part line total. The cards show $ without
an ISO field. The currency is normalized to USD using the official public CSA
basis from A's XU-E12; at 04:37:31.907 the coordinator fetched the public agreement
with credentials omitted (HTTP 200) and confirmed its US Dollars phrase.
Arrival labels are retained as displayed, without inferring a year, production
lead time, calendar/business-day convention or starting point. Taxes, destination
and landed cost remain unknown.

| Quantity | Observed UTC | Least Expensive unit / line | Arrival | Standard unit / line | Arrival | Fastest unit / line | Arrival |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 04:33:05.206 | 206.56 / 206.56 | Nov 9 | 583.64 / 583.64 | Nov 2 | 833.71 / 833.71 | Oct 29 |
| 2 | 04:34:18.024 | 119.88 / 239.76 | Nov 9 | 412.08 / 824.16 | Nov 2 | 594.57 / 1189.14 | Oct 29 |
| 5 | 04:35:10.438 | 59.22 / 296.10 | Nov 9 | 213.13 / 1065.65 | Nov 2 | 314.87 / 1574.35 | Oct 29 |

These are current offers with displayed savings and reference line totals,
all retained in the JSON. The configuration page also displayed Save 25% for
quantity-5 economy. Promotion eligibility/duration and undiscounted regular-price
semantics are not verified; do not call these a regular-price baseline or infer
that future differences arise only from market-price changes. No coupon/credit
was entered or applied by this continuation.

At 04:33:16.888 quantity changed 1→2 once; at 04:34:30.104 it changed 2→5 once.
Settled cards changed accordingly. After Cancel, the quote still showed 5 at
04:36:00.731. One Page.reload(ignoreCache=false) followed; 04:37:08.244 readback
retained quantity 5, geometry, full effective labels and the three prices/arrival
labels. Visible controlled switches remained false. This is provider UI reload
persistence only; no product database, managed session recovery or Agent run.

Decimal checks: 9/9 unit × quantity = line total and 9/9 reference total minus
savings = displayed line total. No checkout, order, payment, RFQ/manual-review
request or account-security change occurred. Task 01 still lacks RapidDirect
geometry/real-price and other documented product/semantic gates; 02–05 stay planning.
