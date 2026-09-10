# External review follow-up — 10 September 2026

This note records the implemented response to the latest external review. The
current build retains all 1,958 TfNSW records and groups them into 1,936 project
locations, including 426 DC locations. Earlier dated reviews and the earlier
report draft describe historical checkpoints; their counts are not the current
snapshot. The generated [validation report](../outputs/validation.json) and
[attribute coverage](../outputs/augmentation_attribute_coverage.csv) provide the
current results. Coverage is not a measure of independently verified accuracy.

## Adopted: two individually justified same-site identities

The follow-up adds four complete council HTML originals and their adjacent
manifests. Previously archived raw files are unchanged. The two additional
groups in `config/reviewed_identities.json` bind all original source fields,
record IDs, membership, selected representative and pinned evidence. They are
specific reviewed decisions, not a general nearby-point clustering rule.

| Review | Source rows | Fixed representative | Supporting evidence and limit |
| --- | --- | --- | --- |
| RI09 — Cowell Street | 512 and 1528 | 1528 | Hunters Hill Council's 4 March 2025 update endorses the Evie installation at 3A Cowell Street carpark, with one charger and two bays. A separately published Council FAQ identifies an existing Evie charger at that carpark. The source records share address, postcode, operator and equipment descriptions; their points differ by 15.380338 m. The council evidence supports the venue identity, not a new measurement of 75 kW or a more accurate representative point. |
| RI10 — Parraween Street | 69 and 1861 | 1861 | North Sydney Council's 17 June 2025 installation table lists Evie, four spaces and 75 kW at Parraween Street, Cremorne. Its carpark directory confirms two dual 75 kW chargers and four bays. The source records both specify 106 Parraween Street and differ by 18.004425 m. The directory does not independently publish number 106; that common number comes from the source observations. |

The four originals, each with GET request metadata, successful HTTP response,
SHA-256 and byte count, are:

| Original under `data/raw/reviewed/` | Publisher and evidence locator |
| --- | --- |
| `identity_cowell_council_proposal_20260910.html` | [Hunters Hill proposal](https://connect.huntershill.nsw.gov.au/electric-vehicle-charging-proposal), 4 March 2025 update and the 3A Cowell Street / Evie / two-bay proposal passages. |
| `identity_cowell_council_operation_20260910.html` | [Hunters Hill FAQ](https://connect.huntershill.nsw.gov.au/ev/widgets/464182/faqs), the paragraph identifying the existing Cowell Street carpark charger as owned and operated by Evie. Other proposed chargers, generic hours and pricing passages are not observations of this site. |
| `identity_parraween_council_installation_20260910.html` | [North Sydney announcement](https://www.northsydney.nsw.gov.au/news/article/310/north-sydney-powers-up-with-60-new-ev-charging-stations), published 17 June 2025, Parraween Street row in the installation table. |
| `identity_parraween_council_carpark_20260910.html` | [Council carpark directory](https://www.northsydney.nsw.gov.au/directory-record/134/parraween-street-car-park-cremorne), address and electric-charging-bays fields. |

Original source coordinates, plug counts, ratings and source-programme labels
remain in `charger_record`; repeated equipment observations are not summed.
An independent field-by-field comparison against the preceding ZIP confirmed
that all 1,958 records retain their previous values except for the `location_id`
of rows 69 and 512. All 2,798 prior raw files and companion manifests were
retained byte-for-byte; this revision adds only the four new HTML/manifest pairs.
Rows 1528 and 1861 are fixed whole-row representatives whose addresses name
Gladesville and Cremorne. Selection does not establish that their coordinates
are more accurate. The previously unsuccessful Cowell webpage request is not
used as evidence. See [the detailed identity review](identity_evie_council_20260910.md).

There are now ten reviewed groups with 21 members, and 21 locations with multiple
source records overall, including one three-record location. The original source
row count remains 1,958 and the explicit DC source-record count remains 433.
This follow-up changes the distinct DC denominator from 428 to 426. Cowell reduces
SA4 126 (Sydney - Ryde) from eight to seven DC locations; Parraween reduces SA4 121
(Sydney - North Sydney and Hornsby) from 41 to 40. The seven separately reviewed
regional memberships and all seven unresolved point conflicts remain unchanged.
The regional view now contains 1,936 locations and the point-eligible view 1,929.
The resulting Cowell OSM association (`node/13073547942`) is 30.927149 m from the
representative point and has no external street address; its heuristic score is
0.582991. The council documents support consolidating the two source records,
not independent precision certification of this OSM point. The accepted link
still follows the existing matching rule and retains that evidence limitation.

## Adopted: explicit URL scope and revised coverage reporting

Recognized operator homepages and generic network maps are operator information,
not evidence of an individual site's services. The semantic classifier now
recognizes the two exact NRMA network-page paths supported by the archived NRMA
publication: `/cars-and-driving/electric-vehicles/charging-network` and
`/electric-vehicles/charging`. Operator identity and known host must agree;
station-detail paths, query strings and fragments are not generalized by this
rule. This adds no new charger observations and does not assert that a generic
network page verifies individual site access or hardware.

| Current measure | Result |
| --- | ---: |
| Source records / project locations | 1,958 / 1,936 |
| Explicit DC source records / distinct DC locations | 433 / 426 |
| Site augmentation, excluding identifier-only coverage | 245 / 426 = 57.51% |
| Site augmentation excluding both identifiers and status | 214 / 426 = 50.23% |
| Additional site coverage dependent on dated status | 31 / 426 = 7.28% |
| Operator information only | 174 / 426 = 40.85% |
| No augmentation | 7 / 426 = 1.64% |
| Any augmentation, including operator information | 419 / 426 = 98.36% |
| Accepted OCM / OSM / JOLT / Ampol links | 131 / 149 / 41 / 13 |
| DC locations with connector types / cost text / opening hours | 211 / 103 / 44 |
| DC locations with site website / operator network-map URL | 31 / 2 |

The non-status numerator, status-dependent group, operator-only group and
unaugmented group are mutually exclusive and total 426. Provider links and
attribute-specific counts overlap; they must not be summed. No site qualifies
only through an identifier. The denominator change follows evidence-bound
identity consolidation; it does not remove unaugmented records to improve a
percentage. Matching distance, address-similarity and ambiguity thresholds were
not widened to obtain these results.

## Not adopted: unsupported withdrawal or stronger truth claims

The existing targeted review of 27 address-missing accepted OSM links found
venue-level support for fourteen, including one retained connector conflict,
and left thirteen pending stronger site evidence. It was AI-assisted evidence
review, not independently labelled human ground truth or a precision estimate.
No confirmed wrong-site relationship was established by that bounded review.
Missing web evidence alone is not a reason to call a link incorrect or silently
remove its observations. See [the per-case ledger](final_matching_review_20260910.csv)
and [its evidence discussion](final_matching_review_20260910.md).

Three pending cases contribute non-status site information only through OSM:

| Source row | OSM object | Remaining issue |
| --- | --- | --- |
| 422 — Bega | `node/12284563526` | The venue page supports 3 Corkhill Place but does not establish the Chargefox charger-to-OSM relationship. |
| 1309 — Goulburn | `node/12564147445` | A Tesla reference is present in OSM, but the source's Hume Street address has not been adequately bridged to the named Tesla venue in authoritative material. |
| 1742 — Parkes | `node/12221169446` | The OSM Tesla reference and source equipment description agree, while independent source-address/site confirmation remains incomplete. |

As a conditional sensitivity calculation, excluding the non-status contribution
of all three would give `(214 - 3) / 426 = 49.53%`. This is neither an applied
database exclusion nor an estimate of match precision. It shows that the current
50.23% non-status coverage has little margin under this specific assumption.
The actual stored site coverage remains 57.51%, with its separately identified
status observations. No geographic truth, current availability or uniform
historical price is inferred from either percentage.

## Still open: the assignment's December 2025 source interpretation

The assignment requests the most-recent version from December 2025. The official
resource filename is `ev_20251216.csv`, but its catalogue description says
effective 20 April 2026 and its documentation is April 2026 v2.1. The PDF's page 3
changelog says "Revised data format"; it does not establish that only formatting
changed or that every station observation refers to December 2025.

A further bounded read-only check on 10 September 2026 confirmed:

- [TfNSW](https://opendata.transport.nsw.gov.au/api/3/action/package_show?id=ev-charging-locations),
  [Data.NSW](https://data.nsw.gov.au/data/api/3/action/package_show?id=2-ev-charging-locations)
  and [data.gov.au](https://data.gov.au/data/api/3/action/package_show?id=nsw-2-ev-charging-locations)
  still link to the same current resource. TfNSW's catalogue bytes also match
  the existing cached catalogue.
- The current CSV returned 283,033 bytes and SHA-256
  `43970e7751b951ab459a1be7bfd6141756c60ff8aa797debf11c5a597109865a`,
  exactly matching the project's immutable source.
- The [TfNSW public activity history](https://opendata.transport.nsw.gov.au/api/3/action/package_activity_list?id=ev-charging-locations&limit=100&include_data=true)
  returned 33 events. The December-named spreadsheet/CSV appears in April 2026
  records; the previous visible named CSV is September 2025. Data.NSW returned
  nine activity events and data.gov.au none. These records did not provide an
  independently recoverable December 2025 snapshot.
- Testing the historical December XLSX and September CSV download paths again
  returned the same current CSV bytes. A historical filename and HTTP 200 do not
  establish historical content. Responses were inspected in memory; no source
  file or manifest was replaced and no message was sent to the course staff.

These observations confirm correct acquisition of the currently published
resource. They cannot decide whether the course accepts it as the required
December 2025 version, or prove that no unpublished historical version exists.
The current inputs remain unchanged. The minimum next step is a course ruling
on this exact resource, or an authoritative historical download/checksum if a
different snapshot is required. Altering a filename, manifest or claimed date
would not resolve this issue. See the [earlier version investigation](source_version_review_20260908.md)
and [official metadata PDF](https://opendata.transport.nsw.gov.au/data/dataset/be1c4de4-4517-4bd0-8a09-2965ddfc7179/resource/ff3c1d7d-cebe-4882-a5c3-9f0b4ebe11c8/download/ev-charging-locations-v2.1.pdf).

## Verification and remaining delivery work

The full Windows/Python 3.12 verification passed **815 tests and 45 integrity
checks**. Offline rebuilding reproduced the logical contents of all 23 base
tables, 40 generated CSVs, persisted schema definitions and the complete
deterministic validation report. Test and reproduction evidence are bound to
project fingerprint
`55e1befdae06b33ba5b648d492580f1e27d38040cfd999ebd218da3bb5fb2e6c`.
Archive-specific verification is recorded beside the ZIP in
`submission/package_verification.json`. Match its archive SHA-256 to
`submission/SHA256.txt` before relying on it: a previous archive's result does
not verify a new one. That check uses a fresh extraction, an already installed
environment and a verified spatial-extension cache; it is not another fresh
dependency installation. Earlier fresh-environment evidence remains a historical
checkpoint.

The separate report draft is synchronized with these results and rendered as a
PDF outside the code package. It remains a draft until the group details are complete.
Group names, student identities, actual individual contributions and the genAI
usage declaration require the group's real information; they are not invented
by this code package. AI assistance in this work included code and prose
generation. A prepared disclosure does not itself satisfy the course's
authorship conditions: members must accurately verify that involvement, their
own contributions, and the originality of the submitted assessable work against
the assignment's rules. Course confirmation of the source version remains a
separate open item even if all software checks pass. These delivery and evidence
limits prevent any claim that the project is guaranteed a particular mark.
