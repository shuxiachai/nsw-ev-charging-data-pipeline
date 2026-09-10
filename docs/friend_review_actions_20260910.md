# Follow-up to the group's external review

This 10 September 2026 follow-up evaluates the supplied REVIEW_20260910.md
against the current implementation. The supplied review describes an earlier
1,938-location / 428-DC / 776-test checkpoint; its counts and statement that no
report exists do not describe the present deliverables. Reviews and fixes were
AI-assisted and are not independent human field verification.

## New Italy geographic conflict

Source row 1711, record `r_b8849ef769b7c91abce5`, identifies Tesla at
8275 Pacific Highway, New Italy NSW 2472. Both postcode fields agree, but the
original point (-30.8015492, 152.8689544) is about 185.89 km outside the entire
official New Italy locality. The stored point intersects SA4 108; the entire
official locality is covered only by SA4 112, with no other intersecting SA4.
This is a missed source-quality conflict, not a failed point/polygon calculation.

Three complete originals and paired capture manifests establish regional identity:

- [Official locality geometry](../data/raw/reviewed/regional_new_italy_locality_20260910.geojson):
  NSW Spatial Services, NEW ITALY, OBJECTID 27006, postcode 2472.
- [Museum's own page](../data/raw/reviewed/regional_new_italy_museum_20260910.html):
  the venue identifies its Tesla charging station and 8275 Pacific Highway.
  It uses Woodburn as its postal town; this is not substituted for a legal locality.
- [Council decision table](../data/raw/reviewed/regional_new_italy_council_20260910.html):
  the unique DA2021/0125 row connects the same museum and street address to New Italy.

The full original CSV row, identity, point, evidence hashes, publisher hosts,
visible venue statement and council record are guarded. The geographic check
runs before augmentation, sets the current conflict flag and records
`source_point_outside_reviewed_locality`. The original false postcode-conflict
result and point remain unchanged. A separate `reviewed_region` assigns 112;
its evidence supports a locality, not an accurate charging-bay coordinate.
An OCM point with a different street number is not adopted as a correction.

All 1,958 records, 1,936 locations and 426 DC locations remain. Point-eligible
locations decrease from 1,929 to 1,928. The seven unresolved postal conflicts
remain and the new geographic conflict brings the identified unresolved total
to eight; all eight have separate regional reviews. Regional counts decrease
by one in SA4 108 and increase by one in 112. This evidence-bound check does not
claim to have verified the official locality of every other source record.

## Explicit OSM contradictions cannot support an automatic correction

The automatic source-resolution stage now checks OSM address/full-address,
street-number/type and explicit postcode evidence before accepting a nearby
same-operator corroborator. A known contradiction disqualifies that corroborator
and remains in the rejected-evidence reason. Compatible unit/range addresses
and missing address fields retain their earlier semantics. Another compatible
corroborator can still be selected; the closest rejected one does not end the search.
The eleven accepted automatic corrections are unchanged for the frozen inputs.

## Independent SQL and operator identity

Both SQL entry points install and load the official spatial extension. Ordinary
INSTALL reuses an installed version/platform-specific binary. A clean extension
directory was tested directly, as was cached offline reuse. Follow
[the standalone guide](standalone_sql.md), including the project-versus-default
extension directory distinction and read-only spatial queries on the deliverable.

The [Counties Energy review](operator_identity_review_20260910.md) withholds one
unverified Richmond AC location's assignment to the OCM operator website. The
original TfNSW name and candidate value remain traceable in `quality_issue`.
No company is guessed from a country domain, and DC augmentation is unaffected.

## Design and evidence clarity

OCM connection details and attributed connector-type summaries have different
granularity. Summaries are deterministically rebuilt, not used to count plugs;
the report and [design explanation](design.md) now make that redundancy explicit.
Sixteen same-operator/address pairs are not automatically merged: distinct
points, equipment observations or installation periods need individual evidence.

The obsolete clean_environment_verification.json remains a labelled local
historical record and is excluded from the final ZIP. Current test and rebuild
evidence must match the current project fingerprint; historical counts are not
rewritten to appear current. Archive-specific verification is supplied beside
the final ZIP. The large evidence PDFs remain because no course-specific 200 MB
limit has been established, and some decisions depend on their maps and figures.

The [targeted matching follow-up](friend_matching_followup_20260910.md) records
new evidence and remaining uncertainty for the three previously highlighted
OSM-only links. Matching thresholds, accepted provider associations and the
245/426 site and 214/426 non-status coverage counts are unchanged by this review.
The latest generated validation and test evidence provide exact check counts.

## Outstanding course and group decisions

The [December 2025 source-version interpretation](source_version_review_20260908.md)
still requires course confirmation; a filename and hash cannot establish the
observation period. Group names, SIDs, actual contributions and a complete,
truthful AI-use declaration require the group's information. No course message,
Canvas submission or collaborator invitation is sent by this follow-up.
