# Matching evidence follow-up on 13 September 2026

This AI-assisted review updates the documentary evidence for two existing OSM associations. It is not independently labelled human ground truth or a measured match-accuracy result. No source record, coordinate, accepted link, matching rule, equipment value or database result changes. The earlier dated review CSV and notes remain historical checkpoints.

## Parkes venue association now supported

Source row 1742 (location `l_96c745c3f95f444c2914`) names Tesla at 9-17 Short Street, Parkes. Its existing OSM association is `node/12221169446`, reference 34173, 71.204642 m away. The following sources complete a published venue-address chain:

| Source | Relevant evidence and retained material |
| --- | --- |
| Club homepage | Parkes Services Club at 9-17 Short Street. [Frozen original](../data/raw/reviewed/friend_matching_parkes_club_20260910.html), SHA-256 `ebf83d918e1999bf8bd2920b70a99c0a1eeea8ac315ce4be602839cecb307806`. |
| Club 2025 audited financial report | File page 5 / printed page 3 lists 9-17 Short Street as Clubhouse and 18-20 Caledonia Street as Club Carpark in the same property table. [Frozen original](../data/raw/reviewed/friend_matching_parkes_club_2025_financial.pdf), SHA-256 `9d44f17f5653569d3fa8e9e555396b630af88905bd3ee2c5e4f891ddbc0af285`. The complete page was visually checked. |
| Tesla official site 34173 | The [official page](https://www.tesla.com/findus/location/supercharger/34173) identifies Parkes Services Club at 20 Caledonia Street, within the carpark address range, with four Superchargers and CCS compatibility. [Saved readable text](evidence/tesla_34173_readable_20260913.txt), [extraction metadata](evidence/tesla_34173_readable_20260913.txt.meta.json), and [exact tool-return record](evidence/tesla_34173_web_open_capture.json) are included. |

**Current decision: venue supported; exact point and historical attributes remain unverified.** The shared venue name and property table connect the source address to the provider-identified carpark. They do not survey either point or prove equipment state at an earlier observation date. The current Tesla page mentions up to 300 kW and 24/7 access; these statements do not replace the source's 175 kW or retrospectively validate the frozen OSM attributes.

The Tesla evidence was acquired through `web.run open` between 07:10:18 and 07:10:44 UTC on 13 September 2026. It is the page's tool-readable text, not an HTTP-original HTML archive. The tool reported a crawl age of three days; neither its exact server-retrieval time nor Tesla's publication/observation date is known. No HTTP 200 or response headers are claimed for this extraction. A preceding normal direct request returned 403; no access restriction was bypassed. Engine citation markers are removed from the readable copy, with all source line labels L0-L37 and body content retained; the separate exact tool record preserves the original return. Its metadata binds the readable file's actual bytes and SHA-256.

This is a disclosed extension of the documentary review evidence to a saved, provider-identified readable-page extraction. The processing pipeline's frozen-original requirements are unchanged. This extraction is packaged under `docs/evidence`, not introduced as a new pipeline raw snapshot or a new augmentation observation. Reproduction can inspect the saved extraction and its property evidence; it cannot reconstruct an unavailable publisher HTTP response.

## Bega remains pending

Source row 422 names Chargefox at 3 Corkhill Place; OSM `node/12284563526` is 54.895419 m away and has no street address or specific venue name. Existing evidence identifies the Old Bega Hospital at number 3, while the neighbouring dealership uses number 1. The [earlier review](friend_matching_followup_20260910.md#bega-adjacent-address-question-remains-open) documents this unresolved distinction.

A bounded follow-up checked official Chargefox information and government property records. It found no direct operator/venue charger record linking this source observation to the OSM point. The [NSW Government AHIP archive](https://www.environment.nsw.gov.au/sites/default/files/2024-06/aboriginal-heritage-impact-permit-public-register-archive-2010-June2023.pdf), file page 62 / printed page 29, independently places Tarra Motors at 1 Corkhill Place, Lot 1 DP1077434. The hospital original identifies Lot 296 DP728021 at number 3. This contextual result does not locate a charger or establish a wrong match. The government PDF and official Chargefox pages remain research material, not additional active inputs or required evidence for a new matching decision.

The public [Chargefox network page](https://www.chargefox.com/charging-network) and its [station-finding guide](https://support.chargefox.com/hc/en-au/articles/15749970580751-Finding-Stations-and-Checking-Station-Availability-in-the-Chargefox-App) direct users to actual app station details, but did not provide this station's record in the reviewed content. A provider station ID/details record or direct venue publication, plus an explanation of numbers 1 and 3, would be useful next evidence. No message was sent to a provider. Missing evidence does not justify confirming or deleting the association.

## Review counts and coverage

The same 27-case cohort now has **16 venue-supported associations and 11 pending**. The original 10 September CSV had 14 supported and 13 pending; the [subsequent Goulburn planning review](friend_matching_followup_20260910.md#goulburn-an-official-bridge-between-the-two-street-addresses) added one, and the present Parkes review adds one. The supported group includes the previously recorded Cowra connector conflict; venue support does not resolve that equipment disagreement.

Actual site augmentation remains **245/426 = 57.51%**, and site information excluding identifiers and status remains **214/426 = 50.23%**. Among the two priority OSM-only contributors previously marked pending, only Bega remains pending. Hypothetically withholding its one contribution gives **244/426 = 57.28%** site scope and **213/426 = 50.00%** excluding identifiers/status. The earlier two-case scenario, 243/426 and 212/426, remains valid for its stated assumption but is not an applied exclusion. None of these coverage or sensitivity figures measures matching accuracy.
