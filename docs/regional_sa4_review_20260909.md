# Regional SA4 review — 9 September 2026

This document records the first five regional reviews and their **historical
593-test checkpoint**. The [later review](third_review_actions_20260909.md) adds
Gilgandra and Narellan and gives current totals. The five original decisions and
their pinned evidence below remain unchanged.

Five source records have enough archived evidence to confirm their **SA4 at
official locality precision**, while their charger coordinates remain unresolved.
The original TfNSW addresses and operator are corroborated by government,
operator and venue publications. Each complete official NSW locality polygon
is contained in exactly one ABS 2026 SA4. This is a regional inference with an
explicit evidence boundary, not a surveyed charger position.

## Five reviewed assignments

The “before” column is the SA4 derived from the disputed source point and retained
in `location.sa4_code`. The “after” column is the separately reviewed SA4 exposed
by `regional_analysis_locations`; the review does not overwrite the source point
or its original point-derived region.

| Source row / record ID | Source address and operator | Before: source-point SA4 | After: reviewed SA4 | Official locality OBJECTID |
| --- | --- | --- | --- | ---: |
| 181 / `r_f52c4475d66d2f9baa40` | NRMA, 15 Victory St, Braidwood NSW 2622 | 105 — Far West and Orana | **101 — Capital Region** | 21591 |
| 380 / `r_1f8b175f54b73f63a5fb` | NRMA, 26 Neilly St, Walgett NSW 2832 | 112 — Richmond - Tweed | **105 — Far West and Orana** | 19506 |
| 395 / `r_78d9a81044a26cf7b6de` | NRMA, 28 Auburn Street, Moree NSW 2400 | 109 — Murray | **110 — New England and North West** | 29008 |
| 730 / `r_ec4d5b86478c54a3f5d0` | NRMA, 81 Hickory St, Dorrigo NSW 2453 | 105 — Far West and Orana | **104 — Coffs Harbour - Grafton** | 26253 |
| 823 / `r_24333f7d2b86c04fbe70` | NRMA, Car park, 51 Evans St (Victoria Park), Inverell NSW 2360 | 113 — Riverina | **110 — New England and North West** | 27888 |

All five original coordinates, postcodes and conflict flags remain unchanged.
There are still seven unresolved point/address conflicts in the source-location
data. The five reviews add regional evidence for these five records; they do not
clear all coordinate conflicts or claim complete ground-truth accuracy.

## Source and geometry method

The exact configuration is [`config/reviewed_regions.json`](../config/reviewed_regions.json).
It pins 15 originals: four existing source snapshots and 11 additional full
response bodies. Each has a `.meta.json` preserving requested/resolved URL,
retrieval time, actual byte count and SHA-256. The current geometry was retrieved
on **9 September 2026** from NSW Spatial Services, as complete Polygon features
with `outFields=*`, `returnGeometry=true` and `outSR=7844`. It is explicitly
GDA2020 (EPSG:7844), and it is not represented as a December 2025 snapshot.

The implementation in [`ev_pipeline/regional.py`](../ev_pipeline/regional.py)
requires a valid complete response, explicit CRS, finite valid nonempty
geometries, and one uniquely named locality with the configured OBJECTID and
postcode. All rings are retained. It compares the entire locality with the ABS
2026 SA4 polygons in a common CRS and requires both:

- Exactly one SA4 covers the entire locality.
- The set of all intersecting SA4 polygons contains that same single SA4.

No centroid, majority-area classification, buffer, geometry simplification or
numerical tolerance replaces these predicates. All five complete localities meet
these conditions. The full locality is a conservative geographic extent for the
regional conclusion; it is not a claim that the station occupies every part of
that locality. A locality touching or crossing another SA4 would fail this rule.

The archived NRMA publishing page must link the specific Google My Maps ID used
by the KML. Each review selects one uniquely named NRMA placemark for its town
and requires that point to lie inside the full official locality. These operator
points corroborate locality only; disagreements among KML, OSM, OCM and other
points are not resolved by selecting one as a bay.

## Complete originals and locators

Paths below are relative to the project. PDF page numbers are one-based file
pages; printed page numbers are distinguished where they differ. These are full
published responses, not isolated quotations, rendered-page transcripts or
manually drawn boundaries.

| Original | Publisher URL | Locator and role |
| --- | --- | --- |
| `data/raw/ev_20251216.csv` | [TfNSW CSV](https://opendata.transport.nsw.gov.au/data/dataset/be1c4de4-4517-4bd0-8a09-2965ddfc7179/resource/7bbb6461-e52d-4fe7-ace4-a15c30198de0/download/ev_20251216.csv) | Logical rows 181, 380, 395, 730 and 823; all twelve original fields are bound per record. The filename's historical-version interpretation remains subject to the existing source-version investigation. |
| `data/raw/SA4_2026_AUST_SHP_GDA2020.zip` | [ABS original](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-4-july-2026-june-2031/access-and-downloads/digital-boundary-files/SA4_2026_AUST_SHP_GDA2020.zip) | Full NSW SA4 geometries from ASGS Edition 4. |
| `data/raw/nrma_network.html` | [NRMA publishing page](https://www.mynrma.com.au/cars-and-driving/electric-vehicles/charging-network) | Embedded public map ID `1x7Qs_rCijBa-6hDJITFvBQNDN0lBkzk`; original redirect is retained in the manifest. |
| `data/raw/nrma_stations.kml` | [Published map KML](https://www.google.com/maps/d/kml?mid=1x7Qs_rCijBa-6hDJITFvBQNDN0lBkzk&forcekml=1) | Unique town placemarks named in the configuration. The map's older title does not establish present availability or accurate charger-bay coordinates. |
| `data/raw/reviewed/regional_nsw_suburb_layer_20260909.json` | [NSW layer metadata](https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/MapServer/2?f=pjson) | Official layer 2, Suburb, polygon geometry definition. |
| `data/raw/reviewed/regional_nsw_five_localities_20260909.geojson` | [Complete boundary query](https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/MapServer/2/query?where=suburbname+IN+%28%27BRAIDWOOD%27%2C%27WALGETT%27%2C%27MOREE%27%2C%27DORRIGO%27%2C%27INVERELL%27%29&outFields=%2A&returnGeometry=true&outSR=7844&f=geojson&orderByFields=suburbname) | Exact `suburbname` and OBJECTID from the assignment table above; all rings preserved. |
| `data/raw/reviewed/regional_nsw_nrma_opening_20231110.html` | [NSW ministerial release](https://www.nsw.gov.au/media-releases/more-ev-chargers-connecting-regional-nsw) | Published 10 November 2023. Article paragraphs identify the NRMA program and all five towns; cached HTML lines 431–438 contain the operator/locality context. |
| `data/raw/reviewed/regional_braidwood_fuelcheck_20260909.json` | [FuelCheck public EV query](https://www.fuelcheck.nsw.gov.au/fuel/api/v1/fuel/prices/bylocation?fuelType=EV&brands=SelectAll&suburb=BRAIDWOOD&postcode=2622&radius=4&bottomLeftLatitude=-35.46&bottomLeftLongitude=149.78&topRightLatitude=-35.43&topRightLongitude=149.82) | Array element 0: `ServiceStationID=20817`, NRMA, EV, 15 Victory Street, Braidwood; station name identifies the servicemen's club/golf course. |
| `data/raw/reviewed/regional_fuelcheck_app_20260909.html` | [FuelCheck application](https://www.fuelcheck.nsw.gov.au/app) | Public `VITE_API_URL` and linked application asset establish the API discovery chain. |
| `data/raw/reviewed/regional_fuelcheck_public_app_20260909.js` | [Public application script](https://www.fuelcheck.nsw.gov.au/assets/index-DbuG--gx.js) | GET `v1/fuel/prices/bylocation` and map-filter parameters. No key, login or cookie was used for the archived JSON. |
| `data/raw/reviewed/regional_walgett_community_carpark.html` | [Dharriwaa Elders Group tour](https://www.dharriwaaeldersgroup.org.au/index.php?id=11&view=category) | Caravan-car-park entry: Neilly/Pitt/Wee Waa access and EV charging. Community context, not council/operator authority or proof of number 26. |
| `data/raw/reviewed/regional_moree_visitor_guide.pdf` | [Moree Plains visitor guide](https://visitmoreeplains.com.au/downloads/moree-plains-visitor-guide.pdf) | File page 9 / printed page 7, arrival information: public EV charging at the Auburn Street council carpark. Number 28 and NRMA are not established by this passage alone. |
| `data/raw/reviewed/regional_dorrigo_pamp_2016.pdf` | [Council PAMP and Bike Plan](https://www.bellingen.nsw.gov.au/files/sharedassets/public/files/accessibility/bellingen-shire-pedestrian-access-and-mobility-plan-and-bike-plan-pamp.pdf) | File page 19 / printed page 14, action 3.12: Coronation Park at 81 Hickory Street, Dorrigo. |
| `data/raw/reviewed/regional_dorrigo_council_q1_2023.pdf` | [Council quarterly report](https://www.bellingen.nsw.gov.au/files/sharedassets/public/v/3/files/ipr/quarterly-reports/operational-plan-progress-report-jul-sep-2023-q1.pdf) | File page 38, PP3.3.1: installed NRMA charging points at Coronation Park. |
| `data/raw/reviewed/regional_inverell_victoria_park.html` | [Inverell Council venue page](https://www.inverell.com.au/venue/victoria-park-inverell/) | Cached HTML lines 300 and 330–337 name Victoria Park and Inverell NSW 2360; council publisher identity is in the footer. Its 81 Vivian Street venue entry is not a charger-address replacement. |

## Interpretation and remaining limits

Braidwood's official FuelCheck record independently confirms the source's exact
operator and street address. Dorrigo's two council originals separately bind
the source street address to Coronation Park and NRMA to that park. For Walgett,
Moree and Inverell, the conclusion is deliberately narrower: official/operator
sources confirm the town, and source/venue information agrees at locality scale.
Walgett's number 26, Moree's number 28, and Inverell's 51/59 Evans Street address
relationship are not independently resolved by these new publications. The
community Walgett page is supplementary context and is labelled accordingly.

The configured records keep their original points and point-derived SA4 values.
`reviewed_region` separately stores the reviewed code, full locality geometry,
method `official_locality_containment` and `coordinate_status='unresolved'`.
`reviewed_region_evidence` binds each source, role, locator and hash through
`source_snapshot`. The database validator reconstructs the expected audit from
the fixed source rows and original geometry, verifies the complete evidence
ledger, and compares full stored geometry rather than only a centroid or area.

`regional_analysis_locations` includes these five reviewed locations alongside
locations already eligible for analysis. It exposes `source_point_sa4_code`,
the reviewed `sa4_code`, method and review ID, while omitting latitude, longitude
and point geometry. `analysis_ready_locations` continues to exclude unresolved
point/address conflicts. This review changes neither matching eligibility nor
site-derived attributes and does not authorize distance-based analysis of the
disputed coordinates. The full database and DC denominator retain all source
locations.

The source CSV, historical publication dates, retrieval dates and current
geographic boundaries describe different observations. The archived 2026
FuelCheck response and locality shapes do not prove December 2025 hardware or
availability. Empty FuelCheck lookups for other towns and HTTP 403 research
attempts were not accepted as positive or negative station evidence. Public
access does not establish a shared reuse licence for all these publications;
retain original attribution and notices.

Only the reviewed bytes may restore a missing pinned GET original. A changed
source, missing manifest, incompatible record identity, incomplete polygon,
ambiguous locality or cross-SA4 locality fails the configured review. A future
observation requires documented re-review. No unresolved bay coordinate is
silently filled from a postcode, locality centroid or nearby operator pin.

## Verification of this revision

The complete Windows/Python 3.12 verification passed **593 tests and 37 integrity
checks**. An offline rebuild reproduced every base table, persisted schema
definition, generated CSV and the complete deterministic validation report.
The verified project fingerprint is
`c17c76528f8b47087c5abae72d39c66c912c5bf1af106a6ce04d47c8157685ed`;
see `outputs/test_evidence.json`, `outputs/validation.json` and
`outputs/reproducibility.json`.

A separate comparison with the immediately preceding delivery confirmed that
all 2,682 existing raw files and manifests, all original columns for the 1,940
locations, and all 18 preceding base tables other than the expanded
`source_snapshot` table were unchanged. The 1,958 source records, accepted
matches, site attributes, original points and point-derived SA4 codes are
preserved. All 14 example SQL statements execute successfully.

The five reviews have 43 source/evidence relationships. Regional analysis now
includes 1,938 locations, of which 428 are DC locations. Point analysis still
includes 1,933 locations, and seven point/address conflicts remain flagged.
The enrichment denominator remains all 430 DC locations, with site-specific
coverage unchanged at 233/430 (54.19%). None of the five region-only reviews
creates an accepted OCM, OSM or JOLT site match.

The test environment used exact requirements installed in an isolated Python
3.12 environment on 8 September 2026 and reused for this verification. This is
not a claim of a fresh installation or a complete live redownload of all
candidate sources.
