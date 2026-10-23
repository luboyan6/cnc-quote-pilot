# RapidDirect bounded zero-geometry readback — 2026-10-22

The existing RD-trial-01 C Configure page was inspected without uploading,
configuring, Apply, Save, deletion, manual-review request or purchase. At
03:24:36.109 UTC it still displayed C filename, 0mm × 0mm × 0mm and 0mm³,
unselected material/finish/roughness and quantity 1. No canvas was present in the
current DOM. The original A/B no-price results remain in the prior live report.

At 03:31:32.993 UTC, a bounded read-only projection of the already loaded
RdwebAppCncConfigure Vue component found isLoading=false and three list entries:

| list index | volume | analysised | analysisProgress | priceOk | unit_price | p_process_type | price_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 (current C, configureIndex=0) | string 0 | true | 0 | true | 0 | string 0 | 1 |
| 1 | string 0 | true | 0 | true | 0 | string 1 | 2 |
| 2 | string 0 | true | 0 | true | 0 | string 1 | 2 |

The index-to-A/B mapping was not independently frozen in this projection.
No errorMsg was present in these entries. Size was non-scalar and was not
serialized; fileKey, IDs, private download URLs, account information, cookies
and tokens were excluded. This is secondary component state, not a supported
provider API or verified enum specification. price_status/process numeric codes
are retained without assigning undocumented meanings. analysisProgress=0 and
analysised=true do not establish whether server parsing completed or failed.

The coexistence of priceOk=true and numeric unit_price=0 while the visible page
has no explicit numeric quote means the boolean alone is unsuitable as a success
condition. Retain the existing nonzero-geometry and visible-real-price guards;
do not normalize this into a free quote, repeat an uncertain submission or infer
a root cause from these flags. Local OCP and Xometry evidence remain independent.

This bounded diagnosis has not resolved RapidDirect or satisfied task 01's
primary-provider gate. Next work needs a documented fallback/provider-order
review or independently justified further diagnosis. No new provider was chosen
and Xometry was not silently promoted to the planned primary provider.
