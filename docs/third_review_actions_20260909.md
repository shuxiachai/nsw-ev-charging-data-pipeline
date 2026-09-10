# Current code review decisions — 9 September 2026

This revision follows a read-only [external review](https://chatgpt.com/s/cx_6aa1580f03448191a065ba8341d1d10b).
Its score estimates are opinions, not a course ruling. Changes are based on the
specific source evidence and reproducible defects below. This document supports
the code deliverable; it is not the required six-page report.

## Decisions

| Review item | Decision and scope |
| --- | --- |
| 1. Formal report, contributions and AI-use report | Required separate deliverables, still outstanding. Do not invent member names, contributions or a complete AI-use history. The code documentation does not replace them. |
| 2. Possible duplicate DC and AC locations | Review individually against operator and venue originals. Keep all source records. Same address or proximity alone does not authorize merging; changes and retained ambiguities are detailed below. |
| 3. Gilgandra and Narellan regional evidence | Accept. Add independently supported regional reviews using complete official locality polygons; preserve uncertain points and conflict flags. |
| 4. Dapto address-internal postcode inconsistency | Accept a source-linked quality review. Missing PCODE does not validate the postcode inside an address. Distinguish this issue from proof that the point is wrong. |
| 5. Truncated operator labels | Mark the unresolved labels explicitly. A site-specific identity decision does not authorize a global owner-to-network alias. |
| 6. More non-status site attributes | Extract only real site information available in the reviewed sources. Two JOLT map addresses contain explicit carpark-hours notes; no generic network-wide equipment claim is copied to all sites. Report the non-status/non-identifier coverage separately. |
| 7. Fees expressed under different attribute names | Accept. Compare fee semantics across `fee` and `usage_cost_text`, retain both observations, and flag possible contradictions without deciding which time or fee component is correct. |
| 8. Connector quantity and status | Accept. Preserve connection-level status ID, label and source operational classification. Keep zero-count rows, exclude them from the connector-type summary, and audit zero counts and site/connection status differences. |
| 9. Connector differences, including Cowra | Classify terminology differences, incomplete/subset observations and physical-type conflicts separately. Preserve the Cowra CCS1/CCS2 disagreement; do not select a winner from prevalence or geography. |
| 10. Weak matches and manual accuracy review | Keep conservative matching thresholds, complete candidate audits and weakest-match samples. Add a direct SQL queue for accepted address-less OSM matches at least 50 m away. This is a review aid, not independent human labels or an accuracy estimate. |
| 11. Old verification dates and prices | Preserve OCM's original `last_verified` and add a strictly parsed UTC `last_verified_at`. It describes source verification, not price validity; retrieval and export dates remain separate. |
| 12. December 2025 interpretation | Keep the published source and the documented unresolved version issue. A renamed download path or fresh download cannot prove a historical snapshot. Course acceptance remains an external question; no message is sent. |
| 13. Timezone-sensitive hashes | Fix. Pipeline connections use UTC and canonical hashing converts aware timestamps to UTC; naive timestamps retain their original meaning. Tests include Sydney summer/winter, UTC, New York and Kathmandu sessions, and a true one-microsecond change. |
| 14. Complete redownload versus cached rebuild | Retain the distinction. Pinned response bodies support deterministic offline rebuilding. Changed URLs/bodies and non-GET evidence can require a new review; hashes do not prove factual truth or permanent retrievability. |
| 15. Missing representative-row power | Add `location_power_observations`, retaining each available source-record rating and its provenance. Preserve the representative row and unknowns; do not aggregate heterogeneous plug observations into station capacity. |
| 16. Website/map scope | Classify independently identified operator homepages and network maps as operator observations while retaining their source-site reference. A URL alone is not an access restriction. |
| 17. Optional DDL hardening | Add finite, positive and paired charger-power bounds, nonnegative finite external power, unique logical source rows and hexadecimal SHA-256 checks. Keep the existing relational design and useful operator-detail redundancy. |
| 18. Reading cost and historical numbers | Add a short current-document navigation in README, retain historical audit checkpoints with explicit labels, and regenerate current counts from the database. Operator coverage remains separately reported; overall coverage does not imply uniform completeness. |

## Evidence-bound identity decisions

| Source rows | Decision | Evidence and limit |
| --- | --- | --- |
| 307 / 1077, Campbelltown | Merge at project-location grain, with row 307 as representative | The council visitor page identifies 12 Tesla Superchargers at Campbelltown Catholic Club; the club contact page identifies 20–22 Camden Road. Both source records have this address, canonical network and plug count. Their approximately 108 m point difference is individually guarded. Preserve the differing source ratings and both original points; do not sum the plugs. |
| 361 / 1088, Mount Annan | Merge at project-location grain, with row 361 as representative | Shell's site 10110865 identifies 241 Waterworth Drive and EV charging. SwitchDin, the installation's technology supplier, separately identifies the Viva/Reddy Express Mount Annan project. Both source points are within the reviewed 25 m venue bound. The supplier's current equipment description is not substituted for historical source ratings or counts. |
| 255 / 1051, Balgowlah | Retain separate, unresolved identity candidates | The property owner's 2025 announcement describes relocation from P3 to P2 and changed equipment. Same address and short point separation do not establish whether the source rows describe one historical installation or different site observations. |
| 969 / 1063, University of Wollongong | Retain separate, unresolved identity candidates | The university's six-DC-port statement identifies P8, but the two source points lie 309.12 m from the complete official P8 polygon (shortest distance in EPSG:3577). This evidence cannot bind the source rows to that installation. Neither location currently has an accepted OCM/OSM site match. `University of` is not globally aliased to Chargefox. |

The two applied groups are RI07 and RI08 in
[`reviewed_identities.json`](../config/reviewed_identities.json). All twelve raw
fields, record IDs, source rows, fixed representative choices, explicit distance
bounds and complete source bodies are checked before applying them. The earlier
identity decisions remain unchanged. A same-site conclusion does not prove that
two observations describe the same individual devices or time period.

The five AC candidate pairs are also left separate. Rows 120/1204 and 777/1281
have park-level charging evidence but incomplete point/equipment linkage;
416/1240 has venue evidence without sufficient device-group identity;
702/1071 conflicts on theatre/winery naming and network;
984/1604 lacks verified linkage between its network labels. Their source rows
remain available for later evidence-based review.

The source register links all four applied DC originals and the three archived
Balgowlah/UOW counterevidence originals. No failed download is used as evidence.

## Address and operator quality

SQ01 checks Dapto source row 1000 against the complete official DAPTO polygon
(OBJECTID 26918) and its postcode 2530. The original point is inside the locality,
but the source address contains 2023 and PCODE is blank. The new warning retains
the address, extracted 2023, null PCODE and original point. This is an internal
address inconsistency, not proof of a wrong point; `address_conflict` is not
changed. The source type is UPCOMING, so it does not affect the DC denominator.

Seventeen `Fast Cities A` records, one `Energy Austra` and one `University of`
record now have explicit operator-label warnings. No full company name or
network replacement is guessed. The independent database checks reconstruct
these warnings and SQ01, so deleting the warning rows cannot hide the issues.

## Two additional regional confirmations

| Source row | Locality / official OBJECTID | Source-point SA4 | Reviewed SA4 |
| --- | --- | --- | --- |
| 650 | GILGANDRA / 28743 / postcode 2827 | 105 | 105 — Far West and Orana |
| 820 | NARELLAN / 26470 / postcode 2567 | 123 | 123 — Sydney - Outer South West |

Both complete official polygons are covered by exactly the indicated SA4 and
intersect no other SA4. These are independent confirmations of coincidentally
unchanged region numbers. Gilgandra uses the government street-address listing
and separate NRMA publications; Narellan uses Evie's published public GET site
3525 plus property-owner directions and services pages. The JSON identifies the
same Camden Valley Way/Somerset Avenue intersection in Narellan 2567. The site's
operator point is checked inside the locality but is not adopted as a bay.

[`reviewed_regions.json`](../config/reviewed_regions.json) now pins 22 sources
for seven reviews and 60 evidence relationships. The original five decisions
and their 15 source pins remain unchanged. Exact sources are listed in
[the source register](sources.md). The new Evie parser has explicit publication,
operator, endpoint, identity, address and point guards; it does not create a
generic trust rule for arbitrary operator responses.

## Attribute changes

The cross-field fee review identifies source rows **613, 947 and 822**. The first
two combine a no-fee flag with positive cost text; the third combines a fee flag
with an unequivocal `FREE` observation. Conditional statements about free
allowances, membership or future charges do not establish a general free status.
All values and source references remain available in
`outputs/cross_source_attribute_differences.csv`.

Cowra source row **709** retains its unresolved CCS Type 1/Type 2 disagreement.
Tesla labels remain uncertain naming/hardware observations instead of being
converted to one physical standard. Quantity zero at OCM191280 is retained in
`external_connector` but no longer contributes a reported connector type.
Berry OCM161845 and Innovation OCM131610 retain their separate site and connection
status observations. See `outputs/connector_quality_issues.csv`.

Source rows **304/456** retain their OSM homepage observations as operator
websites; row **355** retains its OCM network map as an operator-level link.
Source IDs and original values are preserved. JOLT source rows **859/860** gain
the literal note `Carpark open 8:30-19:00` from the unchanged map captured on
6 September 2026. These notes do not specify weekdays or guarantee charger
availability, and are not reinterpreted as 24-hour access.

## Interpretation

`analysis_ready_locations` means that a location passed the implemented point-use
checks. It is not certification that every source field is correct. Regional
analysis uses `regional_analysis_locations`. Neither a successful spatial join
nor a passing automated test proves the real-world accuracy of every station.

OCM's `IsOperational` is retained as supplied by the reference table; some status
categories such as temporary unavailability may still carry a true value. It
must not be interpreted as live availability. Historical connector reports,
zero counts, planned equipment and old price strings remain observable instead
of being silently converted to present-tense claims.

## Integrated result and verification

| Measure | Preceding delivery | This revision |
| --- | ---: | ---: |
| Retained source records | 1,958 | 1,958 |
| Distinct locations / DC locations | 1,940 / 430 | 1,938 / 428 |
| Regional-analysis locations / DC locations | 1,938 / 428 | 1,938 / 428 |
| Point-analysis locations | 1,933 | 1,931 |
| Regional-only reviews / unresolved point conflicts | 5 / 7 | 7 / 7 |
| Accepted OCM / OSM / JOLT links | 130 / 149 / 41 | 131 / 148 / 41 |
| Site-specific and non-identifier site coverage | 233/430 (54.19%) | 233/428 (54.44%) |
| Coverage excluding station codes and network/EVSE states | 200/430 (46.51%) | 202/428 (47.20%) |
| Any-scope coverage | 422/430 (98.14%) | 421/428 (98.36%) |
| Attribute-difference reviews | 23 unclassified text differences | 22 connector reviews + 3 fee reviews |
| Automated tests / integrity checks | 593 / 37 | 733 / 42 |

The regional view now includes every retained project location under its
documented rules. This does not certify every location field or remove the
seven point conflicts. The same regional totals across revisions reflect both
two new regional confirmations and two identity merges. Point-analysis counts
fall because the two confirmed duplicates are consolidated, not because new
coordinate conflicts were introduced. Site coverage changes only after the
full matching pipeline is rerun; provider totals cannot be added together.

The generated attribute review has 25 rows; the separate connector-quality file
has 19 observations across 11 locations. The non-status/non-identifier measure
remains below 50%, and is not a count of independently verified or complete
equipment inventories. Coverage is uneven: JOLT is 41/49, Tesla 40/55 and
Exploren 3/23; see `outputs/coverage_by_operator.csv` for all operators.

All **733 tests and 42 integrity checks passed**. Offline rebuilding reproduced
every logical base table, persisted schema definition, generated CSV and the
complete deterministic validation report. The verified code/input fingerprint
is `5b4431560c57d84687ab5213f98c83c06d04308a76f4882642db6713500497a2`.

A separate comparison with the preceding submission checked all **2,704**
pre-existing raw files/manifests: every byte hash is unchanged. Every original
record ID and pre-existing cleaned-record field is unchanged except the two
approved member location IDs at source rows 1077 and 1088. The previous five
regional audit CSV rows are identical. All **18** example SQL statements run,
and actual full-database hashes agree in UTC, Sydney, New York and Kathmandu
sessions. These checks supplement, rather than replace, the original-source
and provenance tests.

Verification used the isolated Windows/Python 3.12 environment whose exact
requirements were installed on 8 September 2026. It is not a fresh dependency
installation or a full new live download. Formal report content, individual
contributions and AI-use reporting remain separate work; no grade guarantee
or course interpretation was inferred from successful tests.
