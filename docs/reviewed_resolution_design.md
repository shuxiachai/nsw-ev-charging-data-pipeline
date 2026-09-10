# Archived evidence corrections - 9 September 2026

The reviewed-resolution stage applies seven individually justified corrections:
Tenterfield, Nyngan, Narrabri, Coonamble, Wagga Wagga, Wollongong and Walcha.
It supplements the generic OCM/OSM rule without weakening its address or distance
requirements. The verified build resolves 11 original conflicts automatically and
seven through this separate stage, leaving seven of the original 25 conflicts
unresolved. The 8 September review files describe an earlier investigation;
this document and `config/reviewed_resolutions.json` describe the implemented
seven-record review. The earlier Wollongong council-minute URLs returned HTTP
403 and remain historical research leads. Later successful NRMA and government
originals provide the evidence now applied; the 403 responses are not evidence.

All new source originals were acquired programmatically through public HTTP
requests, with successful responses, complete bytes and adjacent URL,
retrieval-time, SHA-256 and size manifests. The seven downloaded PDFs were opened,
their relevant text extracted, and the relevant complete pages visually checked.
Three HTML originals identify the Nyngan and Wollongong operator sites and the
existing Wagga council charger venue. These ten address/venue originals are
supplemented by a separately archived OSM map for Walcha's landmark and road.
Original PDF
files are retained in full, including their surrounding context, rather than
replacing them with clipped extracts.

## Evidence actually applied

| Source record / row | Authoritative address or venue evidence | Coordinate source | Corroboration | Distance |
| --- | --- | --- | --- | ---: |
| `r_adaa6f8f055ae8bae26b` / 195 | Tenterfield Council agenda, 26 February 2020, PDF page 50 (printed page 49): NRMA proposal at the source address behind the visitor information centre | OSM `node/8209129030` | Named NRMA KML Tenterfield placemark | 31.130213 m |
| `r_1e59f65ff126f6e02daf` / 226 | NRMA road-trip article identifies its Nyngan charger on Dandaloo Street; the conflicting OCM Cobar Street label is not used as address evidence | OSM `node/10048386532` | Named NRMA KML Nyngan placemark | 5.190775 m |
| `r_0983acf0fda42653dc7c` / 756 | Council-prepared planning statement, PDF page 3: source address is the Town Hall car park and the NRMA installation is described on the same site | OSM `node/12583296437` | Named NRMA KML Narrabri placemark | 32.173123 m |
| `r_4a1ff1bb4413b75bd478` / 956 | Coonamble Council 2020-2021 annual report, PDF page 20: installed NRMA chargers in the source-named Skillman Lane car park | OSM `node/9278715200` | Named NRMA KML Coonamble placemark | 5.139333 m |
| `r_873bc05df3ccbde0e683` / 727 | Wagga Riverside business-case attachments, PDF pages 128, 255 and 318, connect 8–24 Cross Street to Lots 3/4 DP828377 and the car park; the council's 7 November 2022 agenda separately identifies the existing NRMA charger in Cross Street Car Park | OSM `node/7932870081` | Named NRMA KML Wagga Wagga placemark | 10.915 m |
| `r_84de52950c87598dd45f` / 217 | NRMA article identifies its installed Stewart Street site; government gateway report page 5 maps Stewart Street East / Bank Street car park | OCM `OCM-191177`, 17 Stewart Street, Wollongong 2500 | Named NRMA KML Wollongong placemark | 8.393113 m |
| `r_8c4ebd56a9eefd59533d` / 78 | Official visitor town map page 1 marks the EV street block; Council business paper page 107 records NRMA works on the road reserve adjacent to 10W Apsley Street | OCM `OCM-480135`, 10W Apsley Street, Walcha 2354 | Police building OSM `way/737228454`, with Apsley Street `way/80476703`; mapped landmark, not another charger | 76.756006 m to building centroid |

The Wagga decision is a documented inference across two council originals. The
PDF establishes the street range and parcels; it does not itself name the NRMA
charger. The agenda supplies that separate venue relationship. Together with the
selected OSM/KML points, this supports interpreting this particular source's
`8/24 Cross St` as the reviewed property range. The generic parser continues to
treat slash expressions conservatively; no general `8/24` to `8` equivalence was
introduced. The original point about 394 km away and postcode 2827 remain in the
audit, while the corrected point and source-address postcode 2650 are used
downstream. The documents do not establish surveyed charger-bay coordinates or
present-day availability.

Wollongong is an explicit inference across the NRMA article, government car-park
map and address-labelled OCM point. The government PDF does not itself label
NRMA or establish number 17 as a charging bay. Its 2026 planning evidence locates
the site, not the charging state in December 2025. No OSM match is fabricated.

Walcha's official map places its EV icon on Apsley Street west of Derby Street
near Police Station (1). Council's 25 October 2023 business paper, actual page
107, item 3.3, identifies NRMA construction beside 10W Apsley Street. The matching
OCM point is approximately 76.76 m west-southwest of the police-building centroid,
at 258.07 degrees from building to point, and within 1 m of the mapped Apsley
Street road line. The complete building and road ways, tags, node order and
coordinates are pinned and parsed. Checks require 60-90 m from the building,
bearing 250-270 degrees and at most 5 m from the street in EPSG:3577. These are
guards for this individually reviewed map interpretation, not generic matching
thresholds. Police is a mapped landmark, not a second charger. The selected OCM
point is approximate within the documented road-reserve site; it does not
establish a surveyed bay or a particular side of the road. The old KML is about
258 m away and is not used to corroborate this correction. OCM created its
Walcha record in March 2026; historical Council evidence does not make this a
December 2025 network observation.

Five selected coordinates are parsed from OSM during every build; Wollongong
and Walcha are parsed from their pinned OCM originals. OCM IDs, operator IDs and
operator-reference lookup, title, street, town, postcode and country are guarded.
Coordinates are not configured as replacement constants. Six reviews use exact,
unique named KML placemarks with `corroborating_role='same_operator_charger'`;
Walcha uses the parsed police-building centroid with `mapped_landmark` and the
additional map-relation checks above. Ellipsoidal WGS84 distances are recomputed
with `pyproj.Geod`; a distance greater than 150 m aborts the reviewed stage.
The landmark distance is not agreement between two charger positions. The source
address supplies the reviewed postcode only after record and evidence guards pass.

The cached NRMA network HTML is also pinned, and the implementation verifies that
it publishes the same Google My Maps map ID as the pinned KML URL. This records
why that public Google-hosted KML is operator-published evidence. Its title alone
is not treated as proof of authority or positional accuracy.

## Immutable review contract

`config/reviewed_resolutions.json` contains:

- `sources`: source path relative to the project, original HTTPS URL, and the
  SHA-256 of the bytes actually reviewed. These include the ten address originals,
  cached OSM chargers, OCM POIs and operator references, KML and its publishing
  NRMA page, and the new Walcha OSM landmark/road XML.
- `resolutions`: a stable source record ID, original row number, operator,
  address, postcode, coordinates, address postcode and charger type; selected
  coordinate/corroborating source elements; the address evidence file; its page
  or short text locator; optional supporting address evidence and its locator;
  and the review rationale. Wagga, Wollongong and Walcha each require two distinct
  pinned address files. The two OCM corrections additionally guard equality of
  every original CSV field in `raw_json`.
- `map_publication`: the operator-page/map relationship used by the stage.
- `excluded_candidates`: currently empty. Other records remain unresolved without
  requiring an entry in this list; only the seven selected records can be changed.

`acquire_reviewed(offline=False)` uses `fetch(..., expected_sha256=...)` for every
source. The expected review hash is checked for both fresh downloads and cached
files. Fresh contents at the same URL are not automatically considered reviewed.
A changed source requires a new evidence review and an explicit updated
configuration. Missing originals, missing manifests, incorrect URLs, byte counts
or hashes fail closed. Paths must remain inside the project's `data/raw` tree.

`apply_reviewed_resolutions(records, issues)` returns a new DataFrame plus an
audit DataFrame. It is called after `resolve_conflicts` has preserved original
fields. The reviewed stage checks those originals and requires one source record
per configured ID. Only records still flagged as conflicting can be changed;
already resolved records are skipped, and a second application does not add
duplicate changes. Unrecorded intermediate coordinate or postcode changes cause
an error. Neither the caller's DataFrame nor its quality-issue list is partly
modified if any guard fails.

Applied changes retain `original_latitude`, `original_longitude`,
`original_postcode`, `original_address_conflict`, and the raw row. They set
`resolution_method='coordinates_reviewed_primary_evidence'`, update coordinates
and postcode, clear the resolved conflict, and append an attributed quality issue.

## Independent audit table

The generic `source_resolution` table describes the automatic stage and can
still show `unresolved` for a record subsequently resolved through reviewed
evidence. The separate `reviewed_resolution` table records the later stage.
Final remaining conflicts must therefore be counted from the final records or
locations, not from automatic-stage decisions alone.

The audit contains 21 fields, in the order exposed by
`ev_pipeline.reviewed.AUDIT_COLUMNS`:

```text
record_id, source_row, decision,
old_latitude, old_longitude, old_postcode,
new_latitude, new_longitude, new_postcode,
coordinate_source_file, coordinate_element_id,
corroborating_source_file, corroborating_element_id,
address_source_file, evidence_distance_m, coordinate_change_m,
reason, review_date,
supporting_address_source_file, supporting_address_locator,
corroborating_role
```

Each emitted row has `decision='resolved'`; skipped records do not create
duplicate audit rows. `record_id` should reference the retained charger record;
all three required evidence-file fields reference `source_snapshot`. An optional
fourth source-file foreign key records supporting address evidence and requires
a paired non-null locator. Independent validation compares the complete applied
address evidence and hashes against the configuration, detecting a deleted or
mispointed relationship even if ordinary foreign keys still pass. The non-null
`corroborating_role` allows only `same_operator_charger` or `mapped_landmark`;
the implementation derives it from evidence kind. Independent validation also
checks that Walcha's landmark cannot be relabelled as another charger. The review
date is fixed by the reviewed configuration, not the time of each rebuild.
Source element IDs are explicitly typed by their original source and are not
fabricated OCM or OSM matches. Downstream spatial assignment and site matching
must run again on the corrected records.

## Sources and verification

- [Tenterfield Council original agenda](../data/raw/reviewed/tenterfield_council_20200226.pdf)
  ([original URL](https://www.tenterfield.nsw.gov.au/content/uploads/2020/02/Agenda-_-Feb-26-2020.pdf)).
- [NRMA Nyngan road-trip original HTML](../data/raw/reviewed/nrma_nyngan_road_trip.html)
  ([original URL](https://jss.sitecore.prod.svc.mynrma.com.au/open-road/road-trips/ev-dubbo-to-broken-hill)).
- [Narrabri Council planning original PDF](../data/raw/reviewed/narrabri_89_barwan_planning.pdf)
  ([original URL](https://apps.planningportal.nsw.gov.au/prweb/PRRestService/DocMgmt/v1/PublicDocuments/DATA-WORKATTACH-FILE%20PEC-DPE-EP-WORK%20PAN-378965%2120231017T043350.514%20GMT)).
- [Coonamble Council original annual report](../data/raw/reviewed/coonamble_annual_2020_2021.pdf)
  ([original URL](https://www.coonambleshire.nsw.gov.au/__media_downloads/annual-reports/2020-2021_1_Annual_Report.pdf?downloadable=1)).
- [Wagga Council full Riverside business-case attachments](../data/raw/reviewed/wagga_riverside_business_case_2024.pdf)
  ([publisher file](https://meetings.wagga.nsw.gov.au/Open/2024/05/OC_13052024_AGN_4963_AT_ExternalAttachments/OC_13052024_AGN_4963_AT_Attachment_20853_2.PDF)); one-based PDF pages 128, 255 and 318 were visually checked.
- [Wagga Council original 7 November 2022 agenda HTML](../data/raw/reviewed/wagga_council_agenda_20221107.html)
  ([original URL](https://meetings.wagga.nsw.gov.au/Open/2022/11/OC_07112022_AGN_4883_AT.htm)).
- [NRMA Wollongong article](../data/raw/reviewed/spatial_nrma_ev_charging_game_plan_20260909.html)
  ([original URL](https://jss.sitecore.prod.svc.mynrma.com.au/open-road/advice-and-how-to/ev-charging-game-plan)); Stewart Street operating-site passage.
- [Wollongong government gateway report](../data/raw/reviewed/spatial_wollongong_planning_gateway_20260216.pdf)
  ([original URL](https://apps.planningportal.nsw.gov.au/prweb/PRRestService/DocMgmt/v1/PublicDocuments/DATA-WORKATTACH-FILE%20PEC-DPE-EP-WORK%20PP-2025-2560%2120260216T010043.077%20GMT)); actual page 5, section 1.4 and Figure 1.
- [Walcha official town map](../data/raw/reviewed/spatial_walcha_town_map_202503.pdf)
  ([original URL](https://walchansw.com.au/wp-content/uploads/2025/03/Walcha-Town-Map.pdf)); page 1, EV and Police Station (1).
- [Walcha Council business paper](../data/raw/reviewed/spatial_walcha_council_20231025.pdf)
  ([original URL](https://walcha.nsw.gov.au/wp-content/uploads/2023/10/October-2023-Ordinary-Meeting-Business-Paper-25102023.pdf)); page 107, item 3.3.
- [Walcha OSM map XML](../data/raw/reviewed/spatial_walcha_osm_map_20260909.osm)
  ([original API request](https://api.openstreetmap.org/api/0.6/map?bbox=151.587,-30.988,151.598,-30.977)); police `way/737228454` and road `way/80476703`. This is additional landmark geometry, not an address original or charging-station object.

The adjacent acquisition manifests and configured review hashes bind these links
to the exact local originals. `tests/test_reviewed_resolution.py` checks the real
seven records, original-field preservation, derived coordinates, immutable review
hashes even when download metadata changes, missing evidence, changed source
identities/values, repeated calls, operator mismatches, excessive spatial
disagreement, complete landmark geometry/tags/nodes, map-relative direction and
street corridor, role mislabelling, and atomic failure without partial issues.

The generic stage resolves 11 original conflicts. Applying the seven fully
archived reviewed corrections leaves seven of the original 25 conflicts
unresolved. Remaining uncertainty is retained explicitly rather than addressed
by broader thresholds or unverified coordinates.

## Limits that remain

Council plans and annual reports establish historical address/venue context, not
surveyed charger-bay coordinates or live status. KML and OSM agreement is published
source corroboration, not a claim that their upstream observations are independent.
The KML title says November 2022, while the original cached KML/OSM retrievals are dated
6 September 2026; neither date is the per-station verification date. These sources
do not prove the exact state of the network in December 2025.

Corrected points subsequently matched to the same OSM or OCM objects are dependent
evidence. A zero-distance match to the correction source must not be presented as
an independent accuracy check. The street discrepancy in Nyngan remains documented
even though the reviewed venue and two coordinate sources justify its correction.

The original four reviewed corrections are unchanged. Source row 727 remains
ineligible under the generic unit/street-number rule; its later dedicated review
requires the two full council originals above. The unresolved seven records remain
in the source database and DC denominator, with no fabricated corrections.

Five remaining point conflicts now have a separate [regional membership review](regional_sa4_review_20260909.md).
The full official locality polygons and archived operator/venue evidence support
their reviewed SA4 codes. This does not certify candidate point positions or
change the seven coordinate conflicts described here. Successfully placing all
input points inside SA4 polygons does not prove that all original coordinates
represent the actual charger sites.

The final build has 233 of 430 DC locations with site observations and the same
233 with non-identifier site observations (54.19%). Accepted links are OCM 130,
OSM 149 and JOLT 41; these overlap and cannot be summed as unique locations.
[JOLT snapshot semantics](jolt_details_evidence_20260909.md) explains the dated
network/EVSE values included in that coverage. The separate
[association evidence review](matching_evidence_improvement_20260909.md)
documents four retained venue associations and the withheld Stanley Street OCM
association. Those decisions do not certify the remaining source coordinates.
