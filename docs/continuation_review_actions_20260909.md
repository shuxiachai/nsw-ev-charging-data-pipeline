# Continuation review: verified changes and retained uncertainties

Historical checkpoint before the later improvement. Counts below describe that
405-test delivery. See [the subsequent changes and self-check](improvement_self_check_20260909.md)
and current generated validation/test evidence for the delivered state.

Review input: [follow-up independent review](https://chatgpt.com/s/cx_6aa0c6c1f5708191ae18ef9e102d4029), read 9 September 2026. The preceding 358-test delivery was preserved before these changes. This review adds two reproduced P2 boundary fixes; neither was demonstrated to corrupt the preceding database snapshot.

## 1. Fix locality names containing “Entrance”

The previous normalizer discarded every locality containing `entrance`. This
removed `The Entrance` from source and external address evidence. With the same
street and postcode but a different external town, the correction stage then
treated the source locality as unknown and could move the record approximately
204 km in a synthetic test. The test does not assert that a charger exists at
the synthetic addresses.

The [Central Coast Council page](https://www.centralcoast.nsw.gov.au/recreation/recreational-area/entrance-beach)
uses The Entrance NSW 2261 as its location. The actual TfNSW source row 1215 also
contains this locality; it has no address conflict and did not enter the faulty
correction path.

The fix preserves names such as `The Entrance` and `The Entrance North`, while
recognizing explicit entrance instructions such as `Main entrance` and
`Entrance via Bay Road`. Existing rules for missing/unparsed town evidence
remain in place. Tests require a same-postcode The Entrance/Long Jetty mismatch
to remain unresolved, preserve all source values on rejection, and allow
compatible locality evidence. The current 11 automatic corrections remain
unchanged. This is a conservative address parser, not a complete locality gazetteer.

## 2. Make candidate selection work with the actual official catalogue

The archived official catalogue contains the current CSV (resource
`7bbb6461-e52d-4fe7-ace4-a15c30198de0`) and a CSV explicitly labelled no longer
current and for historic purposes (resource
`66a7ef4c-aece-4732-bc22-e95fc8613522`). Requiring exactly one CSV regardless of
these labels stopped candidate staging immediately after the catalogue download.
The original frozen build remained functional.

Candidate staging now distinguishes explicit publisher current/historical
labels and supports `--tfnsw-resource-id` for an exact selection. Filename dates,
resource order and CKAN's generic active state do not determine which observation
is current. Genuine ambiguity remains an error. A historical resource selected
explicitly remains labelled historical in the candidate report; this does not
authorize adopting it as the assignment input.

The frozen `acquire()` path still selects the specified December-named resource.
Candidate data remain in a new version directory, with paired manifests and a
report; they do not overwrite raw inputs, reviewed hashes, database outputs or
the submission ZIP. Testing uses the real archived catalogue with simulated
downloads, and does not claim a complete fresh live download from every provider.

## 3. Review the four additional identity candidates

Four additional near-coordinate groups were treated as candidates for review,
not automatically accepted duplicates: source rows 244 with 817/1012; 906/1562;
937/1398; and 818/1703. The complete existing membership must be considered:
817 and 1012 already share one location. Centimetre-scale coordinate agreement
does not establish identical physical sites when addresses, equipment or source
descriptions differ. Review decisions and the evidence limits are recorded below.

| Complete source membership | Decision | Evidence and retained differences |
| --- | --- | --- |
| 244 / 817 / 1012 | Adopt one reviewed location, representative 817 | Exploren location 845 explicitly names Kempsey Shire Council at 19 Buchanan Dr, bridging the numbered source address and the named council observations. The official map point about 49 m away is supporting context; source coordinates are retained. |
| 906 / 1562 | Adopt one reviewed location, representative 1562 | Exploren location 1437 identifies Ingenia/Merry Beach Caravan Park at 46 Merry Beach Rd, with a map point matching row 1562. The named source observation and centimetre-close unnumbered observation refer to the same reviewed venue. Retain source 6 kW versus unknown `AC`; current official 7 kW is not substituted. |
| 937 / 1398 | Adopt one reviewed location, representative 1398 | Exploren location 1380 names Milton Ulladulla Exservos Club at 212–222 Princes Hwy and the map point matches row 1398. The venue's own site corroborates its address. Retain source 22 kW versus unknown `AC`. |
| 818 / 1703 | Keep separate pending evidence | Centimetre-close Chargefox points do not resolve different door-number precision, 40/50 kW and Randwick/Waverley source labels. Public Heffron Centre material does not establish the 801–899R/2036 source identity. |

The operator's [public map](https://exploren.com.au/find-a-charger/) and the
published detail responses for locations 845, 1437 and 1380 are preserved as
original response bytes with request method, action, location ID and hash
metadata. These are source-specific reviews, not new AC/DC enrichment coverage.
Current details list two chargers at each of Merry Beach and Exservos, while the
source lists four plugs. The units and observation dates differ; no plug counts
are summed or overwritten. All source records and their whole raw JSON survive.

The reviewed identity configuration pins the full member sets and source values,
the named operator-map elements and detail evidence. A separate
`reviewed_identity_evidence` table links review groups to their archived sources;
the equivalent CSV makes these evidence relationships inspectable without DuckDB.

## 4. Correct Wagga using two newly archived council originals

Source row 727 (`r_873bc05df3ccbde0e683`) was correctly excluded from the generic
correction stage because `8/24 Cross St` cannot normally be equated with street
number `8`. The continuation investigation obtained two complete HTTP 200
originals, each with its original bytes, URL, hash and retrieval manifest:

- The [Wagga Riverside council attachments](https://meetings.wagga.nsw.gov.au/Open/2024/05/OC_13052024_AGN_4963_AT_ExternalAttachments/OC_13052024_AGN_4963_AT_Attachment_20853_2.PDF),
  retained in full (429 pages), connect 8–24 Cross Street to Lots 3/4 DP828377 and
  the car park. PDF pages 128, 255 and 318 were visually checked. This PDF alone
  does not identify the NRMA charger.
- The [7 November 2022 council agenda](https://meetings.wagga.nsw.gov.au/Open/2022/11/OC_07112022_AGN_4883_AT.htm)
  identifies the existing NRMA fast charger in Cross Street Car Park, central
  Wagga, separately from the Evie installation it discusses.

The address relationship is a documented inference across those originals.
OSM `node/7932870081` and the named NRMA Wagga KML point corroborate position
within 10.915 m. The dedicated reviewed stage therefore corrects this record to
the OSM point, approximately 394 km from the original stored point, and changes
postcode 2827 to source-address postcode 2650. All original values remain in the
raw source and audit. This does not introduce a general slash-address shortcut,
prove surveyed charger-bay accuracy or claim live charger status.

`reviewed_resolution` now retains both a required primary address source and an
optional supporting source/locator pair. For Wagga both originals are required
by the pinned configuration. Foreign keys and an independent full-evidence
comparison detect missing, cleared or mispointed links. The previous four
reviewed corrections and all 11 automatic corrections are unchanged.

## 5. Retain nine unresolved conflicts until evidence supports a correction

The remaining unresolved address/coordinate records are a separate evidence problem.
A geometrically valid SA4 for a stored point is not proof that it is the real
charger position. Keep unresolved records in the database and DC denominator,
withhold automatic site matches and exclude them from the analysis-ready view
until adequate address and coordinate evidence is available.

| Source row / locality | Reason for retaining the conflict |
| --- | --- |
| 78 / Walcha | Address-specific charger position remains unestablished; existing OCM/KML positions disagree by about 258 m. |
| 181 / Braidwood | Existing OSM/KML points disagree by about 766 m; no adequate matching NRMA OCM point. |
| 217 / Wollongong | Council originals remain unavailable for archiving; close OCM/KML points do not resolve the street-number and charger-venue evidence gap. |
| 380 / Walgett | Venue and car-park entrance descriptions do not establish the numbered source's particular NRMA charger position. |
| 395 / Moree | Auburn car-park context does not establish the source's numbered address; OSM/KML disagreement is about 382 m. |
| 650 / Gilgandra | Cooee venue context does not establish the source's 6 Castlereagh address; OSM/KML disagreement exceeds 1.1 km. |
| 730 / Dorrigo | Coronation Park context does not establish 81 Hickory Street; candidate OSM/KML points disagree by more than 230 m. |
| 820 / Narellan | Somerset entrance/venue evidence is available but the specific charger position remains unverified. |
| 823 / Inverell | The Evans Street 51/59 difference remains unexplained; a park label alone is inadequate address evidence. |

This continuation performed bounded new retrievals for Wagga, Wollongong and
Walgett and reread the existing evidence for the other seven candidates. It does
not claim an exhaustive new search of all publishers.

## 6. Keep coverage and version limitations explicit

Keep the explicit breakdown of site enrichment and station-code-only enrichment.
The rubric does not explicitly exclude station codes. Also retain the unresolved
December-filename/April-effective-date limitation; no source version has been
silently substituted and no course enquiry has been sent on the user's behalf.
Report and genAI usage-report obligations remain separate from these code fixes.

## Verified current result

| Measure | Previous delivery | After continuation review |
| --- | ---: | ---: |
| Retained source records | 1,958 | 1,958 |
| Distinct locations | 1,943 | 1,940 |
| Explicit DC locations | 430 | 430 |
| Reviewed identity groups / members | 3 / 6 | 6 / 13 |
| Reviewed identity evidence rows | Not a separate table | 6 |
| Automatic / reviewed / unresolved conflicts | 11 / 4 / 10 | 11 / 5 / 9 |
| Point-in-polygon / coastal approximation | 1,942 / 1 | 1,939 / 1 |
| Accepted OCM / OSM / JOLT matches | 129 / 148 / 41 | 129 / 149 / 41 |
| Site enrichment, distinct DC locations | 230 / 430 (53.49%) | 231 / 430 (53.72%) |
| At least one non-identifier site attribute | 198 / 430 (46.05%) | 199 / 430 (46.28%) |
| Station-code-only site enrichment | 32 | 32 |
| Any enrichment, including operator scope | 422 / 430 (98.14%) | 422 / 430 (98.14%) |
| Passing tests / integrity checks | 358 / 28 | 405 / 30 |

The full Windows/Python 3.12 verification passed and an offline rebuild reproduced
every table's logical content, every generated CSV, the schema and deterministic
validation report. All 2,628 original raw files/manifests retain their baseline
hashes; all 1,958 source rows have identical full `raw_json` in the database.
The verification reused the exact-requirements isolated environment installed
on 8 September. It is not represented as a new dependency installation or a
complete live download test. Packaging and extracted-archive proof are recorded
separately in `submission/package_verification.json`.
