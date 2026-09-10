# Final code optimization — 10 September 2026

Historical checkpoint: the counts below describe the Ampol integration before
the later [external-review fixes](external_review_followup_20260910.md). Use
`outputs/validation.json` and the README for the current rebuilt snapshot.

This review strengthens site attributes, audits weak matches and verifies setup
from a new environment. It does not replace the separate assignment report or
establish a grade. The preceding checkpoint is
[the third review](third_review_actions_20260909.md).

## Site-specific connector observations

Fifteen complete official Ampol location pages are pinned with individual GET
manifests. Thirteen were newly downloaded on 10 September; Werrington and
Gosford Eastbound reuse complete earlier originals without changing those files.
Python decodes each page's one `currentLocation` object and its own
`services.EVCharging` array. Explicit CCS/CHAdeMO descriptions supply the
additional `dc_connector_types` attribute only after an accepted location match.

The existing matching thresholds and external-site reuse rule are unchanged.
There are 13 accepted Ampol links, including eleven previously lacking
non-status site information. The source rows newly covered are listed in
`outputs/ampol_matching_candidates.csv` and can be joined through `location_id`
to the source records. The parser retains the publisher's original
station ID, GUID, address and full EV service list. Individual source URLs,
capture times and hashes are available in `config/ampol_sources.json`,
`source_snapshot` and the generated site CSV.

| Coverage measure | Before | After |
| --- | ---: | ---: |
| All retained distinct DC locations | 428 | 428 |
| Site augmentation, including dated status | 233 (54.44%) | 244 (57.01%) |
| Excluding station identifiers and network/EVSE status | 202 (47.20%) | 213 (49.77%) |
| Any scope, including operator information | 421 (98.36%) | 421 (98.36%) |

The narrower measure is still **one distinct DC location short of a strict 50%**
threshold. The rubric does not explicitly exclude dated status, and the broader
site measure remains above 50%. These are disclosed composition measures, not
independent accuracy or completeness estimates.

## Evidence limits and retained exclusions

- Penrith Coreen Avenue is a candidate for source rows 188 and 826. Both are
  withheld under the existing external-site reuse rule. This review does not
  authorize a source identity merge or acceptance of one arbitrary candidate.
- Eastern Creek Eastbound source row 976 has a short 14.58 m separation but
  different motorway wording; retain the address similarity and original text.
  Charmhaven source row 927 has a larger 189.64 m separation with matching
  numbered street evidence. Neither is a surveyed charger-bay position.
- Seven Hills Abbott Road lacks a published AmpCharge EVCharging service
  category and supplies no interface augmentation. This is not proof of no
  physical charger: older OCM/OSM observations at that address identify Evie.
- Repeated Bay 01/02 descriptions are shared website service definitions.
  Werrington/Gosford OSM and Penrith OCM support both interface types, but
  Penrith's old OCM powers differ from the website. Eastern Creek OSM also lists
  more interfaces than the two website service labels. No device totals, plug
  counts, powers, current availability or charging opening hours are inferred.
- Exploren map data and the previously archived details did not support a
  sufficient new attribute at the investigated uncovered locations. Device IDs,
  repeated source power and generic app instructions do not inflate coverage.

## Matching evidence review

The complete current queue of accepted OSM matches without an external street
address and at least 50 m separation contains 27 cases, including Cowra. The
[case-by-case review](final_matching_review_20260910.md) and
[machine-readable ledger](final_matching_review_20260910.csv) record supporting
and contrary evidence, original IDs, current distances and unresolved limits.
This is an AI-assisted source-document review, not independent human fieldwork,
a representative random sample or a precision/recall measurement. Cowra's
CCS1/CCS2 discrepancy remains a separately attributed source conflict.

## Integration and verification

`amp_charge_site` and `amp_charge_site_match` retain observations and accepted
relationships separately. Each Ampol augmentation has one provider key and its
source snapshot. Three additional integrity checks reconstruct publisher
observations, matching decisions and complete attributes from pinned originals.
They detect deleted, altered or reassigned persisted evidence independently of
database constraints. The attribute check includes rows referencing an Ampol
raw file even if their provider key is wrongly labelled as OSM, so an accepted
OSM match cannot disguise an invented Ampol observation. Missing provider manifests require restoration of the
supplied archive; changed online content cannot silently replace a pinned body.

Comparison with the preceding submission preserved all 2,730 existing raw
files/manifests byte for byte, all 1,958 cleaned source records, the 1,938
locations, all earlier identity and regional decisions, all three earlier
providers' accepted match files, and every one of the 2,472 original augmentation
IDs and values. Thirteen additional connector observations were added. The seven
uncertain points retain independently reviewed regional membership.

The [fresh-environment record](fresh_environment_20260910.md) verifies installation
of all 22 pinned dependencies into a new Python 3.12 environment, first download
of the official DuckDB spatial extension and reproducible rebuilding. Full test
counts and the exact executable/input fingerprint are published in
`outputs/test_evidence.json`; current integrity and coverage results are in
`outputs/validation.json`. The reproducibility report compares every base table,
persisted schema, generated CSV and deterministic validation report.

Final integrated verification passed **776 tests and 45 integrity checks**;
all **19 example SQL statements** executed. Every offline comparison passed.
The verified executable/input fingerprint is
`d4fffc5ca34a175ce7fbaa25d606328ce4a7cd2cf17c724bc76a6ee20edfa37a`.
An independent memory-only regression also confirmed that the misattributed
Ampol-to-OSM observation now fails while the valid baseline passes. The final
attribute-difference audit retains 25 rows and the connector-quality audit 19;
no source conflict was silently overwritten to improve coverage.

Formal report writing, actual member contributions, the separate AI-use report
and clarification of the December 2025 source interpretation remain separate
work. No message was sent to course staff or publishers.
