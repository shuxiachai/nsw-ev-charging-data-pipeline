# Evie Council carpark identity reviews — 10 September 2026

Two additional, individually guarded identity reviews consolidate duplicate **project locations**, while retaining every source observation. This is an AI-assisted review of published primary evidence, not an independent field survey or proof that two observations describe the same physical connector serial numbers. Neither a generic proximity rule nor a Sydney/suburb alias rule has been introduced.

## Decisions and source observations

| Review | Source rows | Retained whole-row representative | Original point separation | Conclusion |
|---|---|---|---:|---|
| RI09 | 512, 1528 | 1528 | 15.380338 m | One Evie site at the 3A Cowell Street Council carpark, Gladesville |
| RI10 | 69, 1861 | 1861 | 18.004425 m | One Evie site at the Parraween Street Council carpark, Cremorne |

Distances are ellipsoidal WGS84 distances between the two original source points, computed with the existing `GEOD.inv` implementation. Each review permits only its two explicitly listed observations, with a maximum separation of 20 m. That bound validates the selected members; it does not search for other nearby records.

| Row | Stable record ID | Original location ID | Original address | Raw operator | Original latitude, longitude |
|---:|---|---|---|---|---|
| 512 | `r_87087bde4ca0ce4d15e0` | `l_29f355d832a72df5981b` | 3A Cowell St, Sydney, 2111 | Evie | -33.83281286, 151.1277918 |
| 1528 | `r_414226d0528ed81a9d83` | `l_cf2fd012b6b93bd68f29` | 3A Cowell St / Gladesville NSW 2111 / Australia | Evie Networks | -33.8329216, 151.1276887 |
| 69 | `r_18eff170ad77e27b68fb` | `l_f0baf3917a54b5836f6a` | 106 Parraween St, Sydney, 2090 | Evie | -33.8273504, 151.2303373 |
| 1861 | `r_7eb57f92ab6f23667688` | `l_6e3d9ca76b87b7e64a7a` | 106 Parraween St / Cremorne NSW 2090 / Australia | Evie Networks | -33.8272794, 151.2301624 |

Slashes in the address table represent original line breaks; the full original strings and all 12 CSV fields are guarded in [the identity configuration](../config/reviewed_identities.json). Rows 512 and 69 use `Existing Fast Chargers`; rows 1528 and 1861 use `Kerbside Charging R1`. Both observations in each pair have the same LGA and postcode. Cowell observations each report two DC plugs at 75 kW; Parraween observations each report four DC plugs at 75 kW. Existing operator normalisation maps both raw Evie labels to the same canonical operator.

The later-source rows are the fixed representatives because their addresses explicitly name Gladesville and Cremorne. This does **not** establish that their coordinates are more accurate. The representative remains one entire original row: no address, coordinate, power, plug count or other field is assembled from multiple observations. Repeated plug counts and power ratings are not added together.

## Primary evidence and its limits

### RI09: Cowell Street

[Hunters Hill Council's public proposal](https://connect.huntershill.nsw.gov.au/electric-vehicle-charging-proposal) has a 4 March 2025 update reporting Council endorsement of the charging installation at its 3A Cowell Street carpark in Gladesville. The background identifies Evie Networks, one fast charger and two charging bays, under NSW Kerbside Charging Round 1. This establishes an approved site and proposed configuration, rather than proving installation by the proposed completion date.

[Council's separately published FAQ](https://connect.huntershill.nsw.gov.au/ev/widgets/464182/faqs), in its background answer, identifies an available public charger at Cowell Street carpark, owned and operated by Evie. Together with the exact 3A street address, two-plug observations and source-programme labels, this supports one project location. The FAQ is a captured current statement with no inferred historical observation date. Its unrelated ChargePost pricing, operating hours and equipment guidance are not assigned to this Evie site. These texts do not independently verify the source's 75 kW rating.

The originally suggested May 2025 Council news URL returned HTTP 403 during this review. That response remains only in the local research directory and is excluded from the accepted evidence. The public Council proposal and FAQ were accessed normally and both returned complete HTTP 200 bodies.

### RI10: Parraween Street

[North Sydney Council's 17 June 2025 announcement](https://www.northsydney.nsw.gov.au/news/article/310/north-sydney-powers-up-with-60-new-ev-charging-stations) identifies the Parraween Street, Cremorne Evie installation in a site-specific table row with four charging spaces and 75 kW DC charging. The parser verifies all three cells of that row together, so another carpark's count cannot supply the evidence.

[Council's carpark directory](https://www.northsydney.nsw.gov.au/directory-record/134/parraween-street-car-park-cremorne) gives Parraween Street, Cremorne 2090 and describes two dual 75 kW DC chargers, four bays, operated by Evie. The directory does **not** independently state street number 106. That number is shared by the two source observations; the Council sources establish the named carpark, operator and charging configuration. The evidence supports site identity without claiming a precisely surveyed bay or an equipment history covering every date. No separate-site or relocation evidence was found within these four accepted originals; this is not a claim that the site has never changed.

## Frozen originals and provenance

All four complete response bodies and paired `.meta.json` files are retained under `data/raw/reviewed/`. Manifests record requested/resolved URL, retrieval time in UTC, GET method, HTTP status, content type, response length and SHA-256. Source hashes are also pinned in the configuration.

| Original, relative to `data/raw/reviewed/` | Bytes | SHA-256 | Semantic locator |
|---|---:|---|---|
| [identity_cowell_council_proposal_20260910.html](../data/raw/reviewed/identity_cowell_council_proposal_20260910.html) | 34774 | `63e8ced4341788926a9510762a4e12a61ab4e3ccee8114357cc0a232ffd07ffb` | 4 March update and background: exact site, Evie, one charger/two bays |
| [identity_cowell_council_operation_20260910.html](../data/raw/reviewed/identity_cowell_council_operation_20260910.html) | 41610 | `ae3c8b5465c6a345a85d43610ec41c59b5be17f389f7178d5e8cac7bbbc703e8` | Background FAQ: existing Cowell carpark charger and Evie ownership/operation |
| [identity_parraween_council_installation_20260910.html](../data/raw/reviewed/identity_parraween_council_installation_20260910.html) | 33912 | `71a72609d38abf1a3f157d389a6781af8fa7e1bce0d3bfb1a585eaac1f56a787` | Carpark table: Parraween Street, Cremorne (Evie), four spaces, 75 kW DC |
| [identity_parraween_council_carpark_20260910.html](../data/raw/reviewed/identity_parraween_council_carpark_20260910.html) | 58486 | `b38117e318be8f056400e27b40ce117848a280414a1a852c68613674a6135120` | Directory 134: Address and Electric charging bays fields |

The two Hunters Hill originals were captured on 10 September 2026 at approximately 07:32:54 UTC; the two North Sydney originals at approximately 07:28:38 UTC. Exact timestamps remain in the manifests. Four additional evidence rows link RI09/RI10 to these originals through `reviewed_identity_evidence`; `source_snapshot` records their provenance in the rebuilt database.

## Implementation, verification and rebuild effect

[identity.py](../ev_pipeline/identity.py) retains the earlier Exploren, Tesla and Viva evidence branches. Its two new Council branches enforce exact source-row membership, reviewed street-address variants, source categories, canonical Evie operator, postcode, DC class, plug count and unchanged source rating. The existing full-member guard additionally checks stable record ID, every raw field, original location ID and coordinates. Both originals for each venue must pass pinned URL/hash/manifest checks and their semantic checks before any record or issue is changed.

`acquire_identities()` validates the frozen evidence in both online and offline acquisition. It deliberately does not refresh a missing or changed reviewed page: restore the reviewed snapshot or perform a new explicit review. New groups use review date 10 September 2026, while the eight earlier groups retain their original dates. Audit tables retain their existing columns.

Targeted regression tests in [test_reviewed_identity.py](../tests/test_reviewed_identity.py) and [test_council_identity.py](../tests/test_council_identity.py) cover all-observation preservation, exact whole-row representatives, other groups remaining unchanged, both coordinate-resolution stages, complete evidence provenance, source and metadata drift, missing originals, rehashed semantic tampering, fixed review dates and refusal to broaden the pair-specific bound or locality mapping.

Relative to the preceding build, these decisions remove exactly two location identities and two DC location identities, retaining all 1,958 charger records: 1,938 to 1,936 locations and 428 to 426 DC locations. The identity ledger expands from eight groups/17 members to ten groups/21 members, with 14 evidence links covering 12 distinct originals. Only rows 512 and 69 change their location ID in this increment. These are the deterministic identity-stage effects; final spatial, regional and enhancement counts must be taken from the coordinated rebuilt outputs, not inferred here.
