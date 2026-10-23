# Research: Xometry US lead-time, arrival and offer semantics

- Query: What can official US Xometry sources establish about the existing A/B quote arrival labels, production duration, business-day rules, order cutoff and offer validity?
- Scope: mixed; official public web-search evidence plus existing local A/B records and the shared quote contract. No browser interaction or external mutation.
- Date: 2026-10-22

## Findings

### Conclusion and evidence boundary

The public sources establish that production speed and shipping speed are separate concepts. They support preserving an arrival label as an arrival estimate, rather than converting it into a production completion date. They do **not** establish B's exact production duration, any A/B-specific cutoff, the day-count starting event, holiday calendar, promotion expiry or guaranteed arrival. Keep `production_lead_time_semantics_verified=false` for the existing observations.

This research used `web.search_query` results for primary sources only. No page-open, connected browser, quote UI, checkout, email, account or network-state inspection was performed. Dates below are source publication/update dates when returned, not independently verified full-page retrieval timestamps. Search excerpts may omit relevant content.

### Official source register

All sources were searched on 2026-10-22. These are general platform sources, **not evidence bound to XU-trial-01 or XU-trial-02**.

| Source | Source date returned | Supported finding and limit |
| --- | --- | --- |
| [Learn more about lead time and delivery options, article 681](https://community.xometry.com/kb/articles/681) | Updated 2024-07-11 | Distinguishes Expedite/Standard/Economy production speeds from assumed shipping: one day for Expedite, two days for Standard/Economy; shipping method can change at checkout. Speed selection applies to the order. This explains the separation of concepts; it does not map a current `leadTimeDays` field to a duration definition. Its blanket description of Standard as US manufacturing is outdated in light of the 2026 release below. |
| [Shipping Options Explained, article 651](https://community.xometry.com/kb/articles/651) | Updated 2026-10-07 | Shipping carrier/method/speed can be chosen to meet the promised delivery date. Domestic Standard/Economy CNC is eligible for free two-day shipping; non-domestic Economy CNC for international priority shipping. Self-managed shipping can select a carrier/method. The current source therefore does not justify subtracting two days from an international Economy arrival date. It also does not establish these quotes' destination, actual carrier, transit duration, taxes or landed cost. |
| [Product Release Notes](https://www.xometry.com/release-notes/) | Entries 2026-08-12; 2026-09-01; 2025-07-21 | August 12 allows eligible Standard-tier orders to route internationally under Manufacturing Region Control, so tier name alone cannot identify origin. September 1 gives a 2 pm EST order cutoff for eligible rush **3D printing**, which cannot be applied to CNC A/B. July 21 describes layout changes to the configuration price/lead-time box and quantity-savings table; layout information does not define an arrival-date-to-production-duration conversion. |
| [Answers to the Most Frequently Asked Questions](https://www.xometry.com/resources/blog/answers-to-most-frequently-asked-questions/) | Published 2025-11-03; updated 2026-08-26 | Typical expedited CNC service is listed as 3–4 business days. The article says complexity, quantity, material availability and other factors vary lead times and directs customers to their own quote. This is a generic range, not B's or A's selected duration. |
| [CNC Machining Services](https://www.xometry.com/capabilities/cnc-machining-service/) | No publication/update date returned | Its general feature table lists Standard lead time as 3–7 business days. This does not prove any tier of the live A/B quotes falls within that range. |
| [Precision CNC Machining](https://www.xometry.com/capabilities/cnc-machining-service/precision-cnc-machining/) | No publication/update date returned | Says lead time starts at three business days and increases with project requirements. This minimum cannot fill a missing per-quote lead time. |
| [Customer Service Agreement](https://www.xometry.com/service-agreement/) | Updated 2026-07-28 | Section 5.1 describes system-generated shipment dates as preliminary estimates, subject to conditions and extension. That legal description of shipment estimates does not establish that the observed UI arrival label is a ship date, nor provide its calculation formula. The distinction between shipment and arrival must remain explicit. |
| [Flexible, Transparent Pricing](https://www.xometry.com/resources/company/flexible-transparent-pricing/) | Search reports published approximately 1.4 years ago; exact date not returned | Advertises a general 30-day quote-price guarantee. This establishes a public pricing policy statement, but does not provide A/B's quote creation/expiration timestamps, the observed discount's rules, or a 30-day arrival commitment. |
| [Marketing Terms and Conditions](https://www.xometry.com/marketing_terms_conditions/) | No publication/update date returned | Returned promotions have named codes and specific limits/deadlines; e.g. SUMMERSAVINGS is 25% off with a $400 cap and a 2026-06-30 deadline. Those details do not identify the October A/B UI savings. Do not attach an unrelated campaign, eligibility condition, cap or expiry to the observed Save 25% label. |

The legal source and help text use different contexts: preliminary shipment estimates versus shipping choices intended to meet a delivery date. They do not jointly license a claim of guaranteed arrival or an exact arithmetic identity between quoted production days and an arrival label.

### Existing quote-specific evidence

| Evidence | What is actually established | What is still absent |
| --- | --- | --- |
| A report `xometry-live-quote-2026-10-22.md:70` and JSON `:165` | At quantity 2, the secondary component projection records `arrivalDate=2026-11-05`, `leadTimeDays=7`, Economy, Made Internationally. Visible cards and amounts were independently recorded at quantities 1/2/5. | No verified semantics for the raw value 7: production versus another measure, business/calendar basis, start event, cutoff, holiday calendar, or actual shipping duration. This private component projection is not a public API contract and is scoped to that quantity-2 Economy state. |
| A report `:100`, `:155` | At quantity 5, reference/savings amounts were recorded; one reload retained configuration, prices and arrival labels. | Reload persistence does not establish price validity or a promotion expiration date. No observed campaign identity establishes a regular undiscounted baseline. |
| B report `xometry-b-live-quote-2026-10-22.md:48`; JSON `:101`, `:128`, `:155` | Quantities 1/2/5 showed Nov 9 (Least Expensive), Nov 2 (Standard), Oct 29 (Fastest). Quantity 5 survived a same-quote reload. Dates are preserved as displayed without a year. | No B-specific numeric production duration or date-basis/cutoff/calendar evidence is recorded. No source permits copying A's 7 into B or interpreting B's arrival labels as manufacturing completion. |
| B report `:63`; JSON `:65`, `:217` | Reference/savings totals and a quantity-5 Economy Save 25% label are observed; no coupon or credit was applied by the continuation. | Discount attribution, duration and eligibility remain unknown. The label alone cannot distinguish campaign pricing, a tier reduction, an account offer or another pricing rule. |

Do not infer these unknowns by counting weekdays between October 22 and a card date. Observation time is not an order-placement/acceptance/start timestamp; actual destination, shipping calendar and cutoff are unverified. Likewise, the generic two-day shipping assumption cannot be treated as observed transit time.

### Local files, code patterns and related specs

- `xometry-live-quote-2026-10-22.md` / `xometry-live-quote-result-2026-10-22.json`: A evidence and its explicit lead-time/promotion limits; raw 7 is retained without normalized semantics (`JSON:165–171`).
- `xometry-b-live-quote-2026-10-22.md` / `xometry-b-live-quote-result-2026-10-22.json`: B cards, offer character and `production_lead_time_semantics_verified=false` (`JSON:217–223`).
- `backend/app/modules/cnc/browser/contracts.py:170`: `DayBasis` admits business or calendar days; `LeadTime` at `:182` requires numeric min/max and basis. A raw arrival label does not fill these fields.
- `backend/app/modules/cnc/browser/workflow.py:235`: validator rejects absent/invalid duration and day basis. There is no source-backed mapping from these A/B arrival labels to an accepted duration. No contract changes are proposed by this research.
- `.trellis/spec/backend/browser-executor.md`, section 3: current successful quotes require known lead time and verified freshness; platform integration needs independent live acceptance.
- `.trellis/spec/backend/cnc-validation.md`, sections 4–5: missing lead time stays unknown; catalog, configuration or local checks do not pass real quotation acceptance.
- Task `prd.md`, V-02 and V-BR-02: explanatory lead-time evidence remains required. This report supplies bounded generic context and does not mark acceptance passed.

### Remaining bounded read-only work for the coordinator

Inspect existing A/B quote-specific visible help, configuration or shareable quote details for an explicit production duration, business/calendar designation, shipment versus arrival label, order-by deadline and timezone. Preserve the observed state, quantity, tier, source date and evidence ID with any answer. A documented duration should still be tied to the same actual offer; hidden field names and generic service minimums are insufficient.

If the current quote does not expose this information, retain a semantic limitation rather than attempting checkout/order or deriving dates from unrelated service pages. Any future promotion or expiration evidence must identify the actual observed offer; the generic 30-day policy remains a separate source fact.

## Caveats / Not Found

- No official US source returned a universal CNC cutoff, universal business-day/holiday definition, or the A/B-specific start event. Search absence is not proof no documentation exists.
- No official US search result explicitly defined the literal current UI wording Arrives by as a production-day calculation. The arrival-versus-production distinction is supported by the separate production/shipping documentation, not by an exact per-field schema.
- No B-specific `leadTimeDays`, explicit full-year arrival date, observed offer expiry or promotion identity was found in the supplied records.
- The older help article's Standard=domestic statement conflicts with a newer release; use current observed origin when available and preserve this version caveat.
- Search results from other regional Xometry sites, unrelated third parties and unrelated customer quote screenshots were excluded as evidence. No external account details or secrets were collected into this report.
- No shared task metadata, platform config, source code, acceptance checkbox or existing evidence file was changed. This report is research only.
