# External review: decisions and changes

Historical checkpoint: the counts and decisions below describe the preceding
358-test delivery. The [continuation review](continuation_review_actions_20260909.md)
records the subsequent fixes, additional evidence and current validated counts.

Review input: [independent AI review](https://chatgpt.com/s/cx_6aa0b9b7c9848191a16155a2efd8cfa9), read 9 September 2026. Findings were checked against the supplied source rows and executable behavior. Severity describes the demonstrated effect, not a promise about marks. The reviewer found no demonstrated P0 failure in the preceding deliverable.

## 1. Adopt: three individually verified location identities

The original six-decimal-coordinate/address key left three same-site pairs separate. Each pair has the same operator, street and postcode and positions less than one metre apart:

| TfNSW source rows | Street | Approximate separation | Fixed whole-row representative |
| --- | --- | ---: | ---: |
| 575 / 1565 | 47–49A Cleary St | 0.068 m | 575 |
| 223 / 1308 | 179 Gillards Rd | 0.069 m | 1308 |
| 599 / 1590 | 51 Bathurst St | 0.104 m | 1590 |

`config/reviewed_identities.json` binds the full original values, record IDs, source rows, original location IDs and exact membership. `reviewed_identity` and `outputs/reviewed_identity.csv` persist the mapping and its source. Only three nonrepresentative location IDs change. All 1,958 source records and all original coordinates remain available; the two AC pairs retain their differing `22 kW` and `AC` power observations. The ordinary identity rule is not expanded into proximity clustering. Any later membership or value drift disables the local exception or fails its input guard.

## 2. Adopt: explicit address contradictions at every matching distance

A short distance no longer overrides a parsed contradiction in house-number intervals or street type on the same street. Other gates still require operator agreement, source/postcode consistency, DC evidence, bounded distance, an unambiguous score and no external-site reuse.

| Source row / external candidate | Decision and evidence limit |
| --- | --- |
| 70 / OCM 172921 | Withhold: 1067 versus 1063 Oxley Hwy is not independently reconciled. |
| 193 / OCM 238125 | Withhold: 15620 versus 15597 Hume Hwy is not independently reconciled. Other source evidence may still enrich this location. |
| 613 / OCM 190706 | A specific reviewed exception is supported by the official Dan Murphy’s address range 51–53A Orient St. It proves compatible premises, not current connector or tariff accuracy. |
| 682 / OCM 190757 | Withhold this OCM candidate: 7 versus 2 Bungan St is unexplained. Separate accepted JOLT evidence remains eligible. |
| 961 / OCM 306016 | Withhold: Stuart St versus Stuart Rd remains unexplained. |
| 85 / JOLT 310 | Withhold: 11 versus 3 Scott St remains unexplained despite almost identical coordinates. |
| 614 / JOLT 62 | Withhold: 54 versus 110 Brighton St remains unexplained. |

The Dan Murphy’s evidence is an explicitly attributed extraction of the official rendered page, not an address-bearing downloaded HTML original: the HTTP response was an application shell. The reviewed exception is bound to the precise source/external records and evidence hashes. It waives only that address contradiction and cannot bypass the other match gates. Candidate CSVs preserve the contradiction, exception and review reason; accepted OCM matches link their review ID and evidence snapshot in the database.

The complete candidate selection is rerun. Removing one candidate can expose an alternative, create a reuse conflict or release an external record for another location. It is therefore incorrect to subtract seven from the previous number of matches and call that the new result. Rejected matches indicate insufficient evidence; they are not all proven false matches.

## 3. Adopt: case-insensitive operator identity

The reviewer demonstrated that `Chargefox` and `CHARGEFOX` produced the same operator ID but different display rows, causing a primary-key collision. The fix makes normalized operator display values consistent with the case-insensitive identity and tests the actual database insertion. Raw operator text remains in the source JSON. This is a future-input boundary defect; no such collision was present in the supplied snapshot.

## 4. Adopt: validate external counts before insertion

DuckDB can round a fractional value such as connector `Quantity=1.5` when inserting into an integer column. Validate `Quantity` and `NumberOfPoints` before conversion: null is allowed; Boolean, fractional, negative, non-finite and out-of-range values are rejected. Zero remains a preserved source value and is not invented as a positive count. Database nonnegative checks add a second boundary but cannot by themselves detect already-rounded input. No invalid fractional counts were found in the current source snapshot.

## 5. Adopt: do not override explicit locality disagreement with a postcode

A synthetic same-street/same-postcode Northside-to-Southside candidate could previously trigger a coordinate move of about 144 km. Known, unreconciled locality disagreement must disqualify automatic correction. Different spellings alone do not prove conflict: city/suburb hierarchy and aliases require explicit handling, while missing or unparsed locality remains unknown. Current corroborated corrections must retain their evidence requirements; a higher textual score is not enough to authorize a move.

The implemented parser requires a clear postal suffix and declines street/venue
fragments. Arbitrary different known localities are withheld as
`locality_not_verified`, not asserted to be different physical sites. The one
configured hierarchy is Sydney/Parramatta, only with both postcodes 2150 and an
external point inside a small Parramatta CBD review window. The configuration
links the NSW Planning explanation of Greater Sydney's Central City, and states
that the window is not an official suburb boundary or an LGA-containment claim.
No current automatic correction relies on this exception; all 11 remain unchanged.

## 6. Partially adopt: versioned refresh candidates

Keep the immutable raw cache and reviewed evidence hashes. They correctly reject changed evidence, including an OSM response whose features are unchanged but whose response timestamp has changed. Add a separate candidate-download command under `.runtime/source_candidates/<label>/`. It refuses to overwrite a previous candidate, records source/manifests and differences, and reports incomplete acquisition. It does not replace the supplied cache, build a new database or authorize old reviews for new bytes.

Promotion remains a deliberate new project version: inspect the changed source, revisit affected evidence/record guards, update the paired snapshots and reviewed configuration only after review, then build, verify and package. Never delete hashes or bypass reviewed corrections merely to make a fresh online run pass. A mock-tested candidate workflow is not a claim that every live provider was successfully downloaded again.

## 7. Retain and disclose: ten unresolved source-location conflicts

The existing 11 automatic and four individually reviewed corrections remain distinct. Ten unresolved locations stay in the database and full DC denominator, and remain excluded from `analysis_ready_locations` and site matching. A non-null SA4 classifies the stored point; it does not prove the point is the true charger address. Do not claim that every charger has independently verified physical placement. Further corrections require suitable source evidence, not fabricated coordinates or forced matching.

## 8. Adopt disclosure; retain legitimate station-code enrichment

JOLT station codes are new site-level information relative to the supplied empty station names. The rubric does not explicitly exclude identifiers. Keep the valid attributes and their provenance; do not declare them invalid or replace them with guessed prices/access values.

`outputs/augmentation_composition.csv` partitions all distinct DC locations into three nonoverlapping categories: at least one non-identifier site attribute, station-code-only enrichment, and no site enrichment. `outputs/augmentation_attribute_coverage.csv` reports distinct locations and source observations per attribute/scope. Attribute rows overlap and must not be summed. The non-identifier percentage is a disclosed sensitivity measure, not a silently substituted rubric definition. `fee` is not a tariff, and usage/access text does not independently establish non-Tesla eligibility.

## 9. Retain and disclose: source-version ambiguity

The supplied official CSV has a December 2025 filename but April 2026 effective-date metadata. Existing archived sources do not establish the historical December content. Do not rename a newer file to look historical or silently substitute it. The investigation and unsent course question remain in `docs/source_version_review_20260908.md`. A definitive interpretation requires course clarification; no message has been sent on the user's behalf.

## Validation and remaining submission work

| Final built measure | Result |
| --- | ---: |
| Original rows / retained source records | 1,958 / 1,958 |
| Locations / explicit DC locations | 1,943 / 430 |
| Point-in-polygon / separately labelled coastal assignments | 1,942 / 1 |
| Reviewed identity groups / member audit rows | 3 / 6 |
| Accepted OCM / OSM / JOLT matches | 129 / 148 / 41 |
| Distinct DC locations with site augmentation | 230 / 430 (53.49%) |
| With at least one non-identifier site attribute | 198 / 430 (46.05%) |
| With station-code-only site augmentation | 32 / 430 (7.44%) |
| Automatic corrections / reviewed corrections / unresolved | 11 / 4 / 10 |
| Passing tests / database integrity checks | 358 / 28 |

The integrated run reproduced every base table, persisted schema definition,
generated CSV and complete deterministic validation report offline. It reused
the isolated Windows/Python 3.12 environment installed for the earlier review;
this is not a new dependency-installation or fresh live-source test.

SQL and configuration-backed database checks also reject missing identity audit
members, mismatched representatives, fabricated review labels and cleared review
columns on conflicting accepted addresses. Original raw snapshots are checked
against the pre-review hashes, and each retained `raw_json` is compared with its
original CSV row before the submission package is generated.

Use the current `outputs/validation.json`, `outputs/test_evidence.json`, `outputs/reproducibility.json` and `submission/package_verification.json` for measured final results. Earlier review documents describe earlier snapshots. Tests cover changed membership/coordinates, operator case collisions, invalid counts, localities, close conflicting addresses, exception evidence drift, candidate download failures, coverage overlap and database invariants.

These changes improve demonstrated correctness and auditability; they cannot guarantee full marks or establish every external observation as ground truth. The project report, real member contributions and separate genAI usage report remain separate required submission items.
