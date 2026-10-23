# Research: G-01 official terms and authorization readiness

- Query: Identify current official RapidDirect and Xometry US restrictions on automated access, competitive use, and uploaded-content authority; distinguish stated exceptions from unverified permission.
- Scope: mixed (official public documents and repository acceptance criteria); factual terms research, without a legal conclusion about enforceability or the project's legal classification.
- Date: 2026-10-21, Asia/Shanghai; retrieval window approximately 17:22-17:30 +08:00; recorded at 2026-10-21T17:30:30+08:00.
- Active task: `.trellis/tasks/10-21-cnc-mvp-01-platform-gates`.
- Boundary: no platform browser/account operation, upload, quotation, external message, credential access, product edit, or task-state change by this researcher.

## Findings

### 1. Evidence and source selection

The current public documents contain express restrictions relevant to the proposed automation and price-monitoring use. Platform-specific permission and the relationship between the actual customer account, intended purpose, and applicable agreement remain **unknown**. This record does not mark G-01 as passed and does not conclude that all ordinary purchasing comparisons are prohibited or that the entire MVP has failed.

| Source ID | Official document / provenance | Version evidence and retrieval result |
| --- | --- | --- |
| RD-ENTRY | [RapidDirect official homepage](https://www.rapiddirect.com/), footer Terms and Conditions link | Footer points to RD-CURRENT, rather than the old on-site `/terms-conditions/` page |
| RD-CURRENT | [RapidDirect Terms and Conditions, official-footer-linked Termly viewer](https://app.termly.io/policy-viewer/policy.html?policyUUID=658e05ae-a1fc-48e3-8b5a-6e59c7156558) | Document states Last updated January 24, 2024; public content fetched successfully, HTTP 200 |
| RD-OLD | [Old RapidDirect on-site page](https://www.rapiddirect.com/terms-conditions/) | Displays November 2, 2021 and privacy-policy material despite its title; not used to establish current permission |
| XOM-INDEX | [Xometry official legal index](https://www.xometry.com/legal/) | Explicitly links the Customer Service Agreement and General Terms; establishes document provenance |
| XOM-CSA | [Xometry, Inc. Customer Service Agreement](https://www.xometry.com/service-agreement/) | Last Updated July 28, 2026; document body successfully read |
| XOM-GENERAL | [Official-index-linked General Terms PDF](https://xometry-marketing.cdn.prismic.io/xometry-marketing/895c7155-a7e9-4299-bc0a-26f78a02223d_Terms+%26+Conditions+04_04_2017.pdf) | Link verified from official HTML; web extraction returned 403. The filename's date is not treated as a verified document revision date |

Only platform-published terms and their official linking pages support the findings. Search snippets, robots rules, marketing pages, automated-quoting advertisements, and vendor comparison articles are not permission evidence.

### 2. RapidDirect: exact scope of the located provisions

The current document names Shenzhen Rapid Direct Co., Ltd. and covers its site plus related services referring/linking to these terms. The quotation app's separate incorporation or supplemental agreement remains unverified.

| Provision | Factual paraphrase |
| --- | --- |
| Section 2 | Internal-business/personal access is conditional on the terms. Other commercial content exploitation needs express prior written permission; requests may be addressed to the listed support contact. |
| Section 3(5) | Users represent they will not access through **“automated or non-human means”**. |
| Section 7 | Prohibits automated use/data extraction and using services in efforts to compete or revenue-generating enterprises. Its automated-system bullet excepts standard search-engine/browser usage. |
| Section 7, systematic retrieval bullet | Creating collections/databases through systematic retrieval requires written permission. This exception does not expressly waive every other restriction. |
| Sections 2, 8, 9 | Submissions/contributions require adequate rights and confer substantial reuse rights; contribution provisions address potentially public material. Applicability to private CAD uploads is unresolved. |

Source for this section: [RD-CURRENT](https://app.termly.io/policy-viewer/policy.html?policyUUID=658e05ae-a1fc-48e3-8b5a-6e59c7156558).

There is no established blanket automation/competition waiver in the collected evidence. Browser accessibility is not proof that the proposed Playwright monitoring is within the standard-browser exception. Resolving that scope requires applicable platform authorization; a user's account-use instruction alone does not document a platform exception.

### 3. Xometry US: exact scope of the located provisions

XOM-CSA covers Website/services across access channels and incorporates General Terms.

| Provision | Factual paraphrase |
| --- | --- |
| Sections 7.1.1-7.1.3 | Forbid reverse-engineering pricing/geometry technology; manual or automated scraping/downloading of webpage data; and access to build a similar/competitive website, application, or service. This is not wording that simply bans every automated access or every supplier comparison. |
| Sections 1.2.2, 7.3 | Uploaders need rights/dissemination authority compatible with their confidentiality obligations. Customers retain content ownership but grant service-related, partner-sublicensable use rights. |
| Section 7.4 | Permits internal/enterprise AI model development using Buyer Data/Content, while excluding public or third-party model training. |
| Sections 2, 7.1.7 | Restrict account/password sharing or providing designated account access to another person. Actual authorized account/operator arrangements are unknown. |
| Section 12.12 | An existing bilateral signed MSA covering services/parts takes precedence. Sections 7.1.2-7.1.3 do not themselves give a general written-consent exception; no applicable MSA/waiver was inspected. |

Source for this section: [XOM-CSA](https://www.xometry.com/service-agreement/).

The purpose restriction specifically concerns building a similar or competitive site/application/service. Whether the intended price-monitoring activity falls within that scope is not determined here. Scraping restrictions are a separate clause and should not be collapsed into that purpose test.

### 4. G-01 evidence status and open inputs

Repository contract: `CNC_Competitor_Pricing_Agent_SRS_Design_v1.0.md:197` requires current terms, access method, intended monitoring use, account ownership/authorization, and activation to be verified. `:233` makes G-01/G-02 prerequisites to account/session automation. The task's `prd.md` links these gates; this research does not amend them.

| Evidence needed | RapidDirect | Xometry US |
| --- | --- | --- |
| Current publicly linked terms located | Yes; RD-CURRENT | Yes; XOM-CSA |
| Explicit relevant restriction found | Automated access/retrieval and competing-use provisions | Scraping/downloading and competitive-site/application/service provisions |
| Permission matching automated monitoring purpose/access method | **Unknown**; no written authorization inspected | **Unknown**; no applicable signed MSA/exception inspected |
| Account owner/entity/operator authorization | **Unknown to this research**; user-reported account availability does not establish all scope | **Unknown**; reaching the quote dashboard does not establish account identity/authority |
| Rights to disclose particular A/B/C CAD files under applicable agreements | **Unknown to this terms review** | **Unknown to this terms review** |
| G-01 cleared for proposed automation/monitoring | **Not established** | **Not established** |

Coordinator update received during this research: further automated collection on both candidates was paused, and the user was asked whether platform permission covers the intended use. That is a main-session workflow decision, not a new legal finding or an independently verified platform action by this researcher.

An account owner or organization can supply an existing applicable authorization reference for review without placing secrets or confidential agreement contents in this directory. Useful scope evidence identifies the platform/entity, authorized customer/account, automated access channel, price collection/monitoring and intended competitive/internal use, limits, and validity period. Whether a supplied document resolves the restrictions must be assessed against its actual text; an informal assumption, successful login, no CAPTCHA, a marketing claim, or `robots.txt` is insufficient evidence of permission.

Work independent of these platform actions may continue under its existing task authorization. These findings concern candidate-specific G-01 readiness, not SDK readiness, code quality, the truth of collected page observations, or the overall feasibility of all possible authorized service providers.

### 5. Retrieval details, files, and reproducibility

RD-CURRENT's public viewer initially returned only a JavaScript shell to the web extraction tool. A read-only HTTPS fetch of that official linked viewer identified its `/hosted.min.js`; the viewer code specifies the public content API. The following GET returned the HTML document as JSON without cookies or authentication:

```text
https://app.termly.io/api/v1/consumer/policies/658e05ae-a1fc-48e3-8b5a-6e59c7156558/content
HTTP: 200
JSON keys: content, created_locales, locale
content length: 154961 characters
SHA-256 of decoded content encoded as UTF-8:
05342535c55d9ba07c8872372fcadb641da41940e38764d9f3360f05e245884b
```

Requests used ordinary User-Agent and referring-viewer headers; no login state, challenge solution, or credentials were supplied. HTML was parsed in process with Python's standard `HTMLParser`; no external text, terms cache, dependencies, or product files were written. The content API is a delivery detail of the verified official link, not evidence of an authorized quotation API.

Related files read:

- `.trellis/tasks/10-21-cnc-mvp-01-platform-gates/{prd,design,implement}.md`: validation responsibility and scope.
- `.trellis/tasks/10-21-cnc-pricing-mvp/{prd,design}.md`: project use, acceptance scope, and unknowns.
- `CNC_Competitor_Pricing_Agent_SRS_Design_v1.0.md:195`: G-01-G-07 table and platform-specific handling.
- `.trellis/workflow.md` and relevant backend/guide specs: role-isolated research and persisted-evidence conventions, loaded earlier in this research session.

## Caveats / Not Found

- No legal conclusion about enforceability, jurisdiction, statutory exceptions, or the intended project's classification is given. Textual restrictions and unresolved scope are recorded separately.
- This is the current publicly linked text retrieved on this date. Account-specific accepted versions, the precise incorporation into each quotation app, supplemental conditions, signed permissions, private agreements, and actual account ownership were not inspected.
- RapidDirect's ordinary-browser exception, systematic-retrieval written-permission wording, and conditional internal-business license coexist with its other restrictions. No automatic resolution among them is assumed.
- Xometry's General Terms are incorporated, but their linked PDF body could not be read through the web tool. The current CSA's express restrictions are independently readable; a claim that every incorporated document was fully reviewed would be incorrect.
- Full source documents are linked rather than reproduced. Direct quotations from each terms source are kept below 25 English words; findings primarily paraphrase numbered provisions.
- No third-party/marketing/robots document is used as a substitute for applicable platform permission. No contact with either company was made.
