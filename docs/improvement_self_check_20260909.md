# Improvement and final code self-check — 9 September 2026

Historical checkpoint before the later [regional SA4 review](regional_sa4_review_20260909.md).
The 526-test counts and five unresolved regional risks below describe that earlier
delivery. The subsequent review confirms those five regional memberships while
retaining their uncertain point coordinates; current generated evidence is authoritative.

This is technical change/verification evidence for the code deliverable, not the
required six-page project report. It supersedes the numerical checkpoint in the
continuation review. The original code/data delivery was backed up before changes.

## Applied changes

1. **Wollongong, source row 217.** Archived the complete NRMA Stewart Street article
   and government car-park planning PDF. Applied OCM191177, whose source-compatible
   address and point agree with the named NRMA KML within 8.394 m. SA4 changes from
   110 New England and North West to 107 Illawarra. The government PDF supports
   car-park identity, not a surveyed NRMA bay or a December 2025 observation.
2. **Walcha, source row 78.** Archived the official town map, council road-reserve
   record for 10W Apsley Street, and complete OSM police-building/street geometry.
   Applied OCM480135 as an approximate street-site point. SA4 changes from 105 Far
   West and Orana to 110 New England and North West. The audit explicitly records
   `mapped_landmark`; the police building is not a second charger. The old NRMA
   KML is not used as close corroboration for this decision.
3. **Four weak accepted associations.** Added archived council, centre and operator
   evidence for Mortdale/JOLT55, Leichhardt/OCM272673, Werrington/OSM11425340896 and
   Gosford/OSM11129535113. These support venue identity within documented limits;
   current operator equipment is not substituted for older source observations.
4. **Stanley Street, source row 216 / OCM192687.** Withheld this pair pending stronger
   bay-location evidence. Removed exactly one OCM match and its three attributed
   observations. JOLT52, operator details and the original OCM record remain.
   Full record values, four pinned originals and source metadata guard the
   exclusion; database validation rejects a missing ledger or restored attributes.
5. **JOLT status observations.** Parsed separate `networkStatus` and `evseStatus`
   fields already present in the map captured at `2026-09-06T05:00:00.972541+00:00`.
   The unchanged 41 accepted matches gain 82 source-linked observations. Missing
   states do not imply availability; legacy CMS `status` supplies no fallback.
   The script archived on 9 September supports field meanings, not a new value
   observation date. These fields are dated snapshots, not live availability.
6. **Verification gap found during self-check.** The first JOLT validation checked
   state values but could miss changed database snapshot metadata. It now compares
   the actual map bytes, manifest and database URL/hash/size/capture time. Four
   regression mutations cover all four persisted metadata fields. An independent
   in-memory reproduction changed from accepting a zeroed hash to rejecting it.
7. **Documentation.** Updated source roles, schema, output dictionary and current
   counts. Earlier review counts are identified as historical checkpoints.

No generic matching distance, similarity or ambiguity threshold was relaxed.
Raw source coordinates, postcode values and all 1,958 original records remain
available in the retained original fields and `raw_json`.

Detailed sources and contracts:
[coordinate reviews](reviewed_resolution_design.md),
[five association reviews](matching_evidence_improvement_20260909.md),
[JOLT meanings and snapshot limits](jolt_details_evidence_20260909.md).

## Result comparison

| Measure | Before this improvement | Delivered result |
| --- | ---: | ---: |
| Retained source records | 1,958 | 1,958 |
| Distinct project / DC locations | 1,940 / 430 | 1,940 / 430 |
| Automatic conflict resolutions | 11 | 11 |
| Individually reviewed conflict resolutions | 5 | 7 |
| Unresolved location conflicts | 9 | 7 |
| Accepted OCM / OSM / JOLT matches | 129 / 149 / 41 | 130 / 149 / 41 |
| Site attribute coverage | 231/430 (53.72%) | 233/430 (54.19%) |
| Non-identifier site coverage, including dated status | 199/430 (46.28%) | 233/430 (54.19%) |
| Station-code-only site coverage | 32/430 (7.44%) | 0/430 (0%) |
| Any scope coverage | 422/430 (98.14%) | 422/430 (98.14%) |
| Automated tests | 405 | 526 |
| Independent database checks | 30 | 33 |

The site sets overlap between providers; their match counts must not be summed.
If both status fields and station codes are excluded, other site attributes cover
**200/430 (46.51%)**. Thus the 54.19% figure is not a claim that half the stations
gained stable connector, price or access information. Dated status is genuine
additional per-site data, with a shorter useful life than equipment information.

## Verification actually performed

- Full offline build passed, followed by `scripts/verify_project.py`: **526 tests
  passed**, zero failures; all **33** database integrity checks passed.
- Offline rebuilding produced identical logical base-table contents, persisted
  table/view/index definitions, all generated CSVs and the deterministic validation
  report. Physical DuckDB file bytes and execution timestamps are not compared.
- Verification fingerprint:
  `446640015ae18509744bdb61d20d4a6c2a6b97b8d2933b6acb93620b3a671060`.
- Checked **2,628 original raw files and manifests** against the preserved baseline:
  all byte hashes unchanged. Compared every retained `raw_json` with its CSV row:
  all **1,958** exactly preserved. Added evidence has its own manifest and identity.
- Independently checked the exact Stanley Street exclusion and retained JOLT52,
  all 41 accepted JOLT states against the raw publisher values, all 82 attributed
  status rows, the two new SA4/role pairs, and all seven unresolved DC records.
- Repeated a GeoPandas point/SA4 join over all final record points. The only
  non-contained record remains the explicitly labelled coastal case, source row
  1835, whose location receives the independently checked nearest SA4 at about
  1.311 m. No additional per-record/representative SA4 discrepancy was found.
- Three separate review streams checked location evidence, matching exclusions
  and augmentation provenance. Their review does not establish ground truth for
  every source charger.

The environment is Windows/Python 3.12 with the exact requirements installed in
an isolated review environment on 8 September and reused for this verification.
This is not a claim of a new dependency installation, Linux/macOS execution, or
a fresh live download from every provider. Generated evidence is in
`outputs/test_evidence.json`, `tests.xml`, `test_run.log`, `validation.json`,
`reproducibility.json` and `clean_environment_verification.json`. The package
process separately produces ZIP checksum and extracted-package verification in
`submission/`.

## Remaining issues after self-check

Seven explicit source-coordinate/address conflicts remain. They stay in the
source database and the complete 430-DC-location denominator, but are excluded
from automatic site enrichment and `analysis_ready_locations`.

| Source row | Place | Remaining evidence gap |
| ---: | --- | --- |
| 181 | Braidwood | Club address is established; NRMA bay-to-point identity is not. OSM/KML differ by about 766 m. |
| 380 | Walgett | Address-labelled OCM point differs by about 173 m from OSM/KML; no archived authoritative plan chooses the bay. |
| 395 | Moree | Council address/operating-site leads exist, but required originals returned 403; OSM/KML differ by about 382 m. |
| 650 | Gilgandra | New-site council page could not be archived; candidate points disagree even though their SA4 is the same. |
| 730 | Dorrigo | Council reports and park plans are archived; the two OSM candidates still need a completed point-to-plan comparison. |
| 820 | Narellan | Centre/Evie documents identify the South Side venue, but the intersection address and selected map point need a completed location comparison. Both lie in the same SA4. |
| 823 | Inverell | Precise council site/parcel leads could not be archived; park/fire-station proximity alone does not establish the charger bay. |

Five of those records — 181, 380, 395, 730 and 823 — have named candidate points
in a different SA4 from the source point. Correct point-in-polygon processing
therefore does **not** establish that every real charger is in its correct SA4.
This remains the main obstacle to the rubric's “all chargers” cleaning standard.

The TfNSW filename still says December 2025 while official metadata says effective
April 2026. No retrieved original certified an unchanged December 2025 dataset;
the discrepancy is preserved in the [version review](source_version_review_20260908.md).
Automated matching, dated operator observations and approximate site positions
also retain the limits documented above. The technical checks passed; these
source-evidence uncertainties remain and a full-mark outcome cannot be guaranteed.
