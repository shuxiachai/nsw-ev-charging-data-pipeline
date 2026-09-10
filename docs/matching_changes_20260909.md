# Matching rule review and changes — 2026-09-09

> Historical stage: the later [external review](external_review_actions_20260909.md)
> extends explicit-address conflict rejection to all matching distances and adds
> one guarded, reviewed address-range exception. This document's measurements
> describe the earlier stage; current results are in `outputs/validation.json`.

This change addresses reproducible weaknesses in the matching rules. It does not
claim that an uncertain association has been proved to link two different real
stations. It does not change the distance thresholds, the definition of JOLT
station-code enrichment, source coordinates, or database outputs.

## What changed

### Extended-distance matches need compatible explicit address evidence

The existing rule accepts a same-operator candidate within 100 metres, or within
250 metres when street-address similarity is at least 0.65. Postcode conflicts
and unresolved source-address conflicts disqualify both routes.

The fuzzy score previously allowed incompatible house numbers to support the
100–250 metre route: `1 Test Street` versus `999 Test Street` scores 0.8. A high
string score alone is insufficient evidence that those numbered premises are
the same site.

`extended_address_conflict()` now checks simple, explicitly parsed streets:

- On the same named street, incompatible street types such as Park Road versus
  Park Street cannot support the extended-distance route.
- On the same named street and street type, disjoint house-number intervals
  cannot support that route.
- Intervals may overlap: `17` and `17-25`, or `17-25` and `25-27`, are compatible.
- Unit prefixes are not street numbers: `1/10 High St` and `2/10 High St` both
  provide street number 10. This does not prove their individual devices are the
  same; it only avoids a false street-number contradiction.
- Missing numbers, venue labels, intersections, lot numbers and unparsed forms
  remain unknown. They are not automatically declared conflicting. Number
  suffixes such as `15c` versus `15` likewise do not establish a contradiction.
- Street numbers on differently named roads are not compared: a venue may have
  more than one street entrance.

The candidate audit includes `extended_address_conflict`, containing
`house_number_conflict`, `street_type_conflict`, or an empty string. The conflict
is reported even for a nearby match, but only blocks the route that relies on
address evidence beyond 100 metres. A nearby accepted match remains an
automated, uncertainty-bearing association.

The original `address_similarity()` function is unchanged. In particular, the
coordinate-resolution module's use of this shared function has not been
silently altered. Match scoring, ambiguity margins, and external-POI reuse
rejection are also unchanged. The new audit column does not require a change to
the database match tables; the pipeline already selects their existing columns
explicitly.

### Missing operator values cannot establish identity

`match_sites()` normalizes missing operator values through the existing `text()`
helper before comparison. Two `None` values previously reached `.casefold()` on
`None`, and pandas `NA` could produce an ambiguous truth-value error. Missing
values now consistently fail the operator-equality evidence gate. This does not
invent an operator or infer it from proximity.

### OSM socket-presence parsing is order independent

The previous generator inside a single `try` block returned true for `2;bad`
but false for `bad;2`. It also treated `inf` as a positive count. The parser now
examines tokens individually and requires at least one explicit `yes` or finite
positive number. Invalid tokens do not suppress a later valid positive
observation. Zero, negative values, NaN and infinity do not establish socket
presence. Raw tags remain stored; this function establishes presence, not a
resolved number of sockets when source observations conflict.

The existing snapshot's socket values, including `1;2`, retain their previous
presence interpretation. No CCS Type1/Type2 value is relabelled based on country
or an assumed standard. JOLT parsing and valid station-code enrichment are
unchanged.

## Reproducible examples and observed impact

The following comparison was computed in memory from the existing processed
CSV files. It did not run `build` or overwrite `outputs/` or the database.
Source rows refer to the pipeline's logical source-row identifiers.

| Source row / record ID | External record | Existing evidence | New decision |
|---|---|---|---|
| 543 / `r_c8f1afaf5fc5db4552c7` | OCM 299879 | 42 Camden Rd versus 38 Camden Rd; 107.555 m | Reject extended-distance address evidence; house numbers are disjoint |
| 1563 / `r_4be59958d3b0794536b1` | OCM 460625 | 46 Wynter St versus 37 Wynter Street; 226.995 m | Reject extended-distance address evidence; house numbers are disjoint |

Neither row is labelled a proved wrong-station match. Both require additional
site or entrance evidence before their different numbered premises can support
this distance. No record-specific exception, hand-selected match, increased
threshold, or coverage-driven fallback was introduced.

| Snapshot metric | Before | After rule change in memory |
|---|---:|---:|
| Accepted OCM matches | 134 | 132 |
| Accepted OSM matches | 148 | 148 |
| Accepted JOLT matches | 43 | 43 |
| Unique DC locations with site enrichment | 233 | 232 |
| Site enrichment with the snapshot's 431-location denominator | 54.06% | 53.83% |

The two removed OCM associations cause a net loss of one enriched location
because one still has an observation from another source for the same location. No new OCM matches
were introduced. These are before-integration snapshot figures; final metrics
must come from the full rebuilt pipeline after all concurrent changes.

## Relationship to the 28-case review

See `matching_review_20260908.md` and its CSV evidence snapshot. They remain a
dated record of the decisions then in effect and should not be rewritten to
make the previous review appear to have used today's rules.

| Earlier uncertain case | Classification after code review |
|---|---|
| MR02, Taree | A real rule weakness: incompatible explicit numbers were treated as supporting a match beyond 100 m. Now excluded by the generic gate. The actual station identity still needs evidence. |
| MR03, Peakhurst | A remaining source-position limitation. 17 and 17-25 overlap, and the cached official JOLT point supports the source site. The OCM pin discrepancy is not resolved by a general house-number rule. |
| MR05, Leichhardt | A remaining position/venue limitation. Both sources use 128 Flood Street. The large distance alone does not prove a different site or justify inventing a replacement coordinate. |
| MR15, Werrington | A remaining evidential limitation. A same-operator OSM point within 100 m has no external address; the nearby route is explicit, not a claim of independent verification. |
| MR17, West Gosford | The same nearby, missing-address limitation. Additional official station identity evidence would improve confidence. |
| MR19, Mortdale | A remaining alternate-address/position limitation within 100 m. The official map is a valid source of the station code; that does not independently prove that Cook Lane and Cooks Street identify the same source point. |

The existing ambiguity and reuse cases do not justify broadly merging nearby
records. They can represent a station versus a device, several devices at one
address, or duplicated source records. Their conservative exclusions remain.
Coordinate corrections that reuse an OCM pin still cannot serve as independent
zero-distance accuracy measurements. The Cowra connector conflict remains
explicit source disagreement and requires stronger attribute evidence, not a
string normalization that silently changes one connector type into another.

## Targeted validation

Command, from the code project directory:

```powershell
..\.review\venv\Scripts\python.exe -B -m pytest tests/test_matching.py -q -p no:cacheprovider
```

Result: **53 passed**. Tests cover the existing evidence gates and ambiguity/
reuse behavior, missing operators, disjoint and overlapping house-number
intervals, unit-address handling, uncertain address forms, the nearby route,
missing external addresses, and socket token order/non-finite values. Synthetic
coordinates use WGS84 `Geod.fwd` to exercise the extended-distance branch.

The in-memory comparison separately confirmed the two affected OCM records and
unchanged OSM/JOLT counts. These checks validate program behavior and snapshot
impact. They are not a precision/recall study, independent ground truth, or a
guarantee of a rubric score. Full build, storage, reproducibility and packaging
validation are left to the integrating task.
