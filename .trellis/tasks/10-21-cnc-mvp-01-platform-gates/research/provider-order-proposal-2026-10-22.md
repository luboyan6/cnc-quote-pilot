# Provider order review — 2026-10-22

Status: historical proposal, superseded by the user's answered D-17 decision.
Current order is Xometry US first, JLC-CNC China second, RapidDirect third and
deferred until all first-two functionality is complete. See parent decisions.md
D-17 and task-map.md. The proposal below records the earlier recommendation,
not current provider metadata; children 02–05 still await their technical gates.

## Evidence and consequence

- RapidDirect A/B previously Apply/saved but no numeric price; A/B/C display zero
  geometry. C remains unconfigured. Local kernel measured valid nonzero solids;
  bounded provider UI/component readback did not establish a root cause. No repeated
  upload or source conversion/healing is proposed as an unverified cure.
- Xometry US has controlled A/B nonzero geometry, numeric offers at 1/2/5 and
  quantity5 provider UI reload persistence. A has a wall-thickness warning; B's
  eight DFM labels Passed. Arrival labels, discounted current offers and provider
  UI state remain distinct from production lead-time semantics, regular-price
  baseline and product E2/E3. Full primary-provider acceptance is not yet frozen.
- SRS §2.4 requires bounded diagnosis then an explicit fallback decision. The
  provider table in §2.2 specifies that replacing RapidDirect with Xometry US
  requires a second non-Xometry provider; China/US Xometry cannot count twice.
  Parent decisions D-08 specifically selected Xometry US as the second candidate.
  Switching order or retiring RapidDirect therefore needs a recorded scope decision,
  not a fabricated technical pass. This is a provider-selection decision, not a
  renewed request for the D-15/D-16 permissions already supplied.

## Recommendation and exact change boundary

Recommend prioritizing Xometry US for the first adapter once its remaining
account/session, effective parameter mapping, production/arrival semantics and
promotion metadata conditions have been recorded/verified. Keep all RapidDirect
failures and the source STEP unchanged. Review the second independent provider
separately: retain RapidDirect only if its real geometry/price gates can pass;
if replacing it, obtain the user's available non-Xometry account/platform choice
and permission before new provider operations. Do not silently add another site.

Upon user confirmation of provider order, update parent task metadata, task-map,
parent/01/02/03 PRDs/designs/implementation context consistently, then finish the
first-provider evidence gate before starting 02. No implementation authorization
needs to be asked again; the existing sequential authorization persists.

The immediate single decision for the user is whether to prioritize Xometry US
as the first-provider implementation candidate. A positive answer changes order,
not completion criteria; it does not authorize purchase, payment, registration,
contacting providers or treating an unverified second provider as delivered.

Rollback: retain current order and bounded RD investigation, with 02 waiting on
RD geometry/explicit price. Neither path lowers the two-provider requirement.
