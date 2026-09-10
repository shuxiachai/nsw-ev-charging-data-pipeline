# Sources and attribution

Retrieval timestamps and SHA-256 checksums are in the `.meta.json` files next to
each raw input and in the database's `source_snapshot` table. These links identify
the publishers; the stored snapshot is the evidence used by this run.

| Source | Publisher URL | Usage |
| --- | --- | --- |
| NSW EV charging locations | [TfNSW dataset](https://opendata.transport.nsw.gov.au/data/dataset/ev-charging-locations) | Base CSV and metadata; catalogue identifies Creative Commons Attribution. Retain TfNSW attribution and its data-validation caveat. |
| ASGS Edition 4 digital boundaries | [ABS official downloads](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-4-july-2026-june-2031/access-and-downloads/digital-boundary-files) | ABS 2026 SA4 shapefile, GDA2020. Retain ABS attribution and bundled source metadata. |
| Open Charge Map export | [Publisher's export](https://github.com/openchargemap/ocm-export) | Official POI export and reference data pinned to one commit. Two individually reviewed corrections use parsed OCM points and guarded operator-reference data. Per-provider licensing is preserved in `external_site.data_license`; see `data/raw/ocm_source_readme.md` and `ocm_reference.json`. Do not assume every POI has an identical license. |
| OpenStreetMap | [Copyright and attribution](https://www.openstreetmap.org/copyright) | Copyright OpenStreetMap contributors, ODbL. Preserve attribution and review ODbL obligations before further distribution of a derived database. |
| Overpass API | [Public retrieval API](https://wiki.openstreetmap.org/wiki/Overpass_API) | Query and response are cached in `data/raw/osm_chargers.json` and its manifest. Explicitly selected OSM elements also supply the five reviewed coordinates. |
| OSM map API | [Archived Walcha map request](https://api.openstreetmap.org/api/0.6/map?bbox=151.587,-30.988,151.598,-30.977) | Complete XML supplies the police-building and Apsley Street geometry for one reviewed map interpretation. Police is a landmark, not a charging station. The new map does not replace the original charger snapshot. |
| Charging-station tags | [OSM tag documentation](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dcharging_station) | Socket/access/fee/opening-hours tag meanings. Only explicit source values are used; missing tags are not inferred defaults. |
| JOLT Australian map | [Operator map](https://joltcharge.com/au/find-a-charger/) | Public embedded station codes and separate per-station network/EVSE status snapshots. The linked script is archived as evidence of field semantics, not a source of current availability. No open license is inferred for the operator page. |
| Ampol individual station pages | [Public station directory](https://locations.ampol.com.au/en) | Fifteen complete individual-page originals and GET manifests are pinned in `config/ampol_sources.json`. The parser extracts only each location's explicit CCS/CHAdeMO service statements. Shared service labels are not a surveyed inventory; powers, bay totals and charger opening hours are not inferred. No open license is inferred. Exact URLs, body hashes and capture times remain in configuration, source_snapshot and `amp_charge_site`. |
| NRMA public network map | [Operator network page](https://www.mynrma.com.au/cars-and-driving/electric-vehicles/charging-network) | Cached webpage and its linked public KML. Six reviews use selected named points to corroborate five OSM and one OCM point within 150 m, with separate address originals. Walcha uses official map/landmark evidence instead; its old KML point is not corroboration. Other pins are not automatically street-coordinate truth. |
| NSW Spatial Services Suburb boundaries | [Official administrative-boundary layer](https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/MapServer/2) | Complete current locality polygons, retrieved in GDA2020 on 9 September 2026, bound seven regional-only reviews. Entire polygons must fit within one ABS 2026 SA4; no centroid, simplified outline or charger coordinate is substituted. |
| NSW FuelCheck public EV map | [Official application](https://www.fuelcheck.nsw.gov.au/app) | A complete public GET response independently identifies NRMA at the Braidwood source address. Archived application HTML and JavaScript document the public endpoint; no login, key or cookie was used. |
| Exploren public map and location details | [Operator map](https://exploren.com.au/find-a-charger/) | One original map HTML and three original public POST responses corroborate the explicitly reviewed identity groups RI04–RI06. They do not supply replacement source coordinates or current charger-count assumptions. |
| DuckDB spatial | [Official extension documentation](https://duckdb.org/docs/stable/core_extensions/spatial/overview) | Spatial extension for stored geometry, indexes and SQL checks. |

## Additional originals for reviewed corrections

All ten address originals below are retained in full under `data/raw/reviewed/`, with
adjacent download manifests. `config/reviewed_resolutions.json` pins their exact
URLs and reviewed SHA-256 values, together with the reused OSM/OCM/KML snapshots,
OCM operator reference, the NRMA map-publishing page and the new Walcha OSM XML.
They support seven reviewed corrections: Tenterfield, Nyngan, Narrabri,
Coonamble, Wagga Wagga, Wollongong and Walcha. The last three each require two
distinct address originals. The reviewed stage uses these records only after
the original source identity and evidence guards pass.

| Source and local original | Publisher URL | Role and limit |
| --- | --- | --- |
| Tenterfield Council agenda, 26 February 2020; `tenterfield_council_20200226.pdf` | [Council agenda](https://www.tenterfield.nsw.gov.au/content/uploads/2020/02/Agenda-_-Feb-26-2020.pdf) | PDF page 50 supports the NRMA proposal at the source address behind the visitor information centre. A proposal is historical address/venue context, not live status. |
| NRMA Nyngan road-trip article; `nrma_nyngan_road_trip.html` | [NRMA article](https://jss.sitecore.prod.svc.mynrma.com.au/open-road/road-trips/ev-dubbo-to-broken-hill) | Identifies the Nyngan charger at 18 Dandaloo Street. The conflicting OCM Cobar Street label is not used as an address synonym. |
| Narrabri Council planning statement; `narrabri_89_barwan_planning.pdf` | [NSW Planning Portal original](https://apps.planningportal.nsw.gov.au/prweb/PRRestService/DocMgmt/v1/PublicDocuments/DATA-WORKATTACH-FILE%20PEC-DPE-EP-WORK%20PAN-378965%2120231017T043350.514%20GMT) | PDF page 3 identifies 89 Barwan Street and describes the NRMA installation at the Town Hall car park. Planning/construction evidence does not establish current availability. |
| Coonamble Council annual report 2020–2021; `coonamble_annual_2020_2021.pdf` | [Council annual report](https://www.coonambleshire.nsw.gov.au/__media_downloads/annual-reports/2020-2021_1_Annual_Report.pdf?downloadable=1) | PDF page 20 confirms installed NRMA chargers at Skillman's Lane car park. It does not provide surveyed charger-bay coordinates. |
| Wagga Wagga Council Riverside business case, 2024; `wagga_riverside_business_case_2024.pdf` | [Council business-case attachment](https://meetings.wagga.nsw.gov.au/Open/2024/05/OC_13052024_AGN_4963_AT_ExternalAttachments/OC_13052024_AGN_4963_AT_Attachment_20853_2.PDF) | Complete PDF; file pages 128, 255 and 318 connect 8–24 Cross Street and 8 Cross Street with Lot 3 DP828377, its car park and the Cross/Tarcutta Street site map. The PDF alone neither names NRMA nor supplies charger-bay coordinates. The original request URL and redirect target are retained in its manifest. |
| Wagga Wagga Council agenda, 7 November 2022; `wagga_council_agenda_20221107.html` | [Complete council agenda](https://meetings.wagga.nsw.gov.au/Open/2022/11/OC_07112022_AGN_4883_AT.htm) | Complete HTML response; cached lines 2043–2047 identify an existing NRMA fast charger at Cross-Street Carpark. This supplies the separate operator-at-venue link needed alongside the 2024 address/parcel PDF. |
| NRMA Wollongong article; `spatial_nrma_ev_charging_game_plan_20260909.html` | [NRMA article](https://jss.sitecore.prod.svc.mynrma.com.au/open-road/advice-and-how-to/ev-charging-game-plan) | The Stewart Street passage identifies the operator's first installed, operating Wollongong site. This is archived operator text, not a current availability query. |
| Wollongong gateway report; `spatial_wollongong_planning_gateway_20260216.pdf` | [Government planning original](https://apps.planningportal.nsw.gov.au/prweb/PRRestService/DocMgmt/v1/PublicDocuments/DATA-WORKATTACH-FILE%20PEC-DPE-EP-WORK%20PP-2025-2560%2120260216T010043.077%20GMT) | Page 5, section 1.4 and Figure 1, maps Stewart Street East / Bank Street car park. It does not itself label NRMA or establish number 17 as a charging bay. The 2026 report supports site identity, not December 2025 charging state. |
| Official Walcha visitor map; `spatial_walcha_town_map_202503.pdf` | [Town map](https://walchansw.com.au/wp-content/uploads/2025/03/Walcha-Town-Map.pdf) | Page 1 shows an EV icon in the Apsley Street block west of Derby Street near Police Station (1). It is a street/venue schematic, not a georeferenced survey of a charger bay. |
| Walcha Council business paper, 25 October 2023; `spatial_walcha_council_20231025.pdf` | [Council business paper](https://walcha.nsw.gov.au/wp-content/uploads/2023/10/October-2023-Ordinary-Meeting-Business-Paper-25102023.pdf) | Page 107, item 3.3, records NRMA construction on the road reserve adjacent to 10W Apsley Street. This binds the source address to the map context; it does not establish live operating state. |

The original PDF page numbers above are one-based file pages. These are reviewed
location corrections, not additional independently verified augmentation matches.
Five selected coordinates are read from OSM; Wollongong and Walcha use their
original OCM POIs, with ID/operator/reference and address guards. Six reviews
use named NRMA KML corroboration. Walcha's additional
[`spatial_walcha_osm_map_20260909.osm`](../data/raw/reviewed/spatial_walcha_osm_map_20260909.osm)
supplies police `way/737228454` and road `way/80476703`, including all nodes and
geometry. It supports the official-map interpretation with a bounded relative
direction, distance and street-corridor check. The OCM point is approximate in
the road-reserve site; police is not another charger, and the old KML about
258 m away is not used to corroborate it.

These roles and source-file foreign keys are retained in the 21-column
`reviewed_resolution` audit, including `supporting_address_source_file`,
`supporting_address_locator` and non-null `corroborating_role`. The role is
`same_operator_charger` for six reviews and `mapped_landmark` for Walcha, with
independent database checks against the configured evidence kind. Wagga's source
row 727 retains the literal address `8/24 Cross St`; interpreting this as the
documented site range is an individual inference across the two originals,
not a general rule equating unit-number slashes with street ranges. The 2026
property-register web extract was a research lead, not applied evidence. See
[reviewed-resolution design](reviewed_resolution_design.md) for the exact source
elements, page locators, decisions and safeguards. Public availability does not
establish a blanket reuse license for these council/operator originals; retain
their publisher information and notices. The final build applies 11 automatic
and seven reviewed resolutions; seven postal conflicts remain explicit. The
later New Italy geographic review adds an eighth point conflict, separately
from this original postcode-based queue.

## Additional originals for reviewed regional assignments

The first five of the seven remaining conflicts received separate regional evidence:
Braidwood, Walgett, Moree, Dorrigo and Inverell. Their official locality polygons
are each wholly contained in one ABS 2026 SA4. This supports regional assignment
without selecting a replacement charger point. All five source coordinates,
postcodes and conflict flags remain unchanged; all seven point conflicts remain
explicit. The five reviews add their locations to `regional_analysis_locations`,
which exposes the reviewed region and original point-derived region separately
and omits point coordinates and geometry. They do not become additional members
of `analysis_ready_locations` through this review.

The first five reviews pinned **15 complete originals**: the existing
TfNSW CSV, ABS boundaries, NRMA publishing page and KML, plus the **11 new
originals** listed below. Every original has an adjacent manifest with URL,
capture time, byte count and SHA-256. The new `reviewed_region` and
`reviewed_region_evidence` tables retain the regional decisions and their
source-file relationships. The [regional review](regional_sa4_review_20260909.md)
contains the five before/after regions, exact locators, geometry predicates and
limits. This is a separate method from the seven coordinate corrections above.

The later [regional extension](third_review_actions_20260909.md) adds Gilgandra
and Narellan. The current `config/reviewed_regions.json` pins **22 originals** for
seven reviews: the preceding 15, five new full responses below and two existing
Evie page/script originals. All seven locations now have reviewed regional
membership; all seven point conflicts remain. Gilgandra's point-derived 105 and
Narellan's point-derived 123 are independently confirmed, not replaced.

| Additional original under `data/raw/reviewed/` | Publisher and role |
| --- | --- |
| `regional_nsw_gilgandra_narellan_20260909.geojson` | [Complete official locality query](https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/MapServer/2/query?where=suburbname+IN+%28%27GILGANDRA%27%2C%27NARELLAN%27%29&outFields=%2A&returnGeometry=true&outSR=7844&f=geojson&orderByFields=suburbname), full GDA2020 polygons. |
| `regional_gilgandra_nsw_museum_20260909.html` | [NSW Government museum listing](https://www.nsw.gov.au/visiting-and-exploring-nsw/locations-and-attractions/gilgandra-museum), exact street address/locality, not surveyed charging bays. Existing NRMA publications separately identify the operator in Gilgandra. |
| `regional_evie_narellan_search_20260909.json` | [Evie public GET](https://evie.com.au/wp-admin/admin-ajax.php?action=store_search&lat=-34.04&lng=150.738&max_results=50&search_radius=5), unique site 3525, matching intersection and Narellan 2567. Existing full page/script originals establish its public GET publication chain. |
| `regional_narellan_centre_services_20260909.html` | [Centre services](https://www.narellantowncentre.com.au/customer-service/customer-service), Evie charging via Queen Street on the centre's south side. |
| `regional_narellan_centre_getting_here_20260909.html` | [Centre directions](https://www.narellantowncentre.com.au/customer-service/getting-here), Somerset Avenue/Queen Street access and Narellan 2567 venue identity. |

| Local original under `data/raw/reviewed/` | Publisher URL | Role and limit |
| --- | --- | --- |
| `regional_nsw_suburb_layer_20260909.json` | [NSW Suburb layer definition](https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/MapServer/2?f=pjson) | Complete layer metadata identifies the official polygon service. |
| `regional_nsw_five_localities_20260909.geojson` | [Complete five-locality request](https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/MapServer/2/query?where=suburbname+IN+%28%27BRAIDWOOD%27%2C%27WALGETT%27%2C%27MOREE%27%2C%27DORRIGO%27%2C%27INVERELL%27%29&outFields=%2A&returnGeometry=true&outSR=7844&f=geojson&orderByFields=suburbname) | All rings of the full five locality polygons, explicitly EPSG:7844. This is the service's 2026 observation, not a claimed December 2025 boundary snapshot or charger footprint. |
| `regional_nsw_nrma_opening_20231110.html` | [NSW Government ministerial release](https://www.nsw.gov.au/media-releases/more-ev-chargers-connecting-regional-nsw) | Published 10 November 2023; identifies the NRMA regional program and all five towns. Historical operator/locality evidence, not live status or exact bay positions. |
| `regional_braidwood_fuelcheck_20260909.json` | [Official FuelCheck EV query](https://www.fuelcheck.nsw.gov.au/fuel/api/v1/fuel/prices/bylocation?fuelType=EV&brands=SelectAll&suburb=BRAIDWOOD&postcode=2622&radius=4&bottomLeftLatitude=-35.46&bottomLeftLongitude=149.78&topRightLatitude=-35.43&topRightLongitude=149.82) | Array element 0, station 20817, identifies NRMA and the exact 15 Victory Street address. Its point is not adopted as a charger-coordinate correction. |
| `regional_fuelcheck_app_20260909.html` | [FuelCheck application](https://www.fuelcheck.nsw.gov.au/app) | Complete public HTML supplies the API base URL and linked application script. |
| `regional_fuelcheck_public_app_20260909.js` | [Published application script](https://www.fuelcheck.nsw.gov.au/assets/index-DbuG--gx.js) | Complete JavaScript defines public GET `v1/fuel/prices/bylocation` and its map-filter parameters. Builds use the archived response; they do not execute this script. |
| `regional_walgett_community_carpark.html` | [Dharriwaa Elders Group tour](https://www.dharriwaaeldersgroup.org.au/index.php?id=11&view=category) | Caravan-car-park entry describes Neilly/Pitt/Wee Waa access and EV charging. This is community context, not government/operator evidence or independent proof of number 26. |
| `regional_moree_visitor_guide.pdf` | [Moree Plains visitor guide](https://visitmoreeplains.com.au/downloads/moree-plains-visitor-guide.pdf) | PDF file page 9 / printed page 7 identifies public EV charging at the Auburn Street council carpark. It does not establish number 28 or name NRMA in that passage; separate state/operator sources support NRMA in Moree. |
| `regional_dorrigo_pamp_2016.pdf` | [Bellingen Council PAMP and Bike Plan](https://www.bellingen.nsw.gov.au/files/sharedassets/public/files/accessibility/bellingen-shire-pedestrian-access-and-mobility-plan-and-bike-plan-pamp.pdf) | PDF file page 19 / printed page 14, action 3.12, connects Coronation Park with 81 Hickory Street, Dorrigo. |
| `regional_dorrigo_council_q1_2023.pdf` | [Council quarterly progress report](https://www.bellingen.nsw.gov.au/files/sharedassets/public/v/3/files/ipr/quarterly-reports/operational-plan-progress-report-jul-sep-2023-q1.pdf) | PDF file page 38, PP3.3.1, confirms installed NRMA charging points at Coronation Park. The report supplies operator-at-venue context alongside the separate address document. |
| `regional_inverell_victoria_park.html` | [Inverell Council Victoria Park venue](https://www.inverell.com.au/venue/victoria-park-inverell/) | Names the park and Inverell NSW 2360. Its 81 Vivian Street venue entry is not substituted for source 51 Evans Street; the 51/59 Evans discrepancy remains unresolved at street/bay precision. |

The official source/operator/locality chain and complete geometry establish the
scope of these reviewed inferences. They do not prove every house number,
December 2025 equipment, present availability or an external-site association.
All new files are complete HTTP response bodies rather than search excerpts or
hand-transcribed geometry. Public access does not establish a common reuse
license across government, tourism, operator and community publications; retain
the respective attribution and notices. Hash-pinned GET restoration accepts
only the approved bytes. A changed public endpoint or changed locality boundary
requires a new observation and review rather than silently updating this audit.

## JOLT status semantics and association evidence

[JOLT status evidence](jolt_details_evidence_20260909.md) records how the archived
operator map reports `networkStatus` and `evseStatus` for each station. The new
original `data/raw/jolt_details_map_app_20260909.js`, with its manifest, is the
public script linked by that map and confirms how the station card and marker
use these fields. Builds obtain the values from the existing map JSON, without
executing the script or querying a live charging service. They remain separate
dated observations; missing values do not become `available`, and the older
`status` field does not supply a fallback. These fields do not prove present
availability, static hardware coverage or December 2025 operating conditions.

[The association evidence review](matching_evidence_improvement_20260909.md)
documents ten further complete originals under `data/raw/reviewed/matching_*`:
two Georges River Council agendas, the Evie map page/script/public site-query
response, MarketPlace Leichhardt information/map HTML and basement SVG, and
two Ampol site pages. Each has a URL, retrieval time, byte count and SHA-256
manifest. They support retaining four venue associations with stated positional
and temporal limits. The Stanley Street OCM association is individually withheld
pending location evidence while its stronger JOLT association remains. The OCM
original is retained; the uncertain relationship and its OCM-derived attributes
are withheld without moving or removing the source charger. The review does not
certify old connector specifications or equate a floor plan with latitude and
longitude evidence.

Current coverage and accepted-link counts are generated in `outputs/validation.json`
and summarized in README. Overlapping source links are not summed as unique
locations. The JOLT document's isolated before/after figures describe that
extraction change alone. Final totals are in `outputs/validation.json` and the
generated coverage files, after coordinate reviews and association exclusions.

The later semantic update also extracts two literal carpark-hours notes already
present in the same archived JOLT response. They are not synthesized opening
hours or a new capture date. OCM connection-level status/quantity fields and
`last_verified_at` come from the existing raw POIs and status reference; no
historical price is re-labelled as currently effective. The new cross-field fee
and connector review CSVs retain both sources, including conflicting values.

## Operator originals for reviewed identities

Four additional originals under `data/raw/reviewed/` support the three Exploren
identity groups RI04–RI06. These are complete HTTP response bodies, unlike the
Dan Murphy's rendered-page excerpt described below. Exact hashes, URLs and
request methods are pinned in `config/reviewed_identities.json`; each original
has an adjacent manifest recording its retrieval time and byte count.

| Local original | Published location and retrieval | Identity role |
| --- | --- | --- |
| `identity_exploren_map_20260909.html` | GET [Exploren map](https://exploren.com.au/find-a-charger/) | Published `locations` array supplies the named AC map elements used for all three groups. |
| `identity_exploren_location_845_20260909.json` | [Location 845](https://exploren.com.au/find-a-charger/?charger_location=845); POST detail response | RI04: Kempsey Shire Council, 19 Buchanan Drive, South West Rocks NSW 2431. |
| `identity_exploren_location_1437_20260909.json` | [Location 1437](https://exploren.com.au/find-a-charger/?charger_location=1437); POST detail response | RI05: Ingenia – Merry Beach, Merry Beach Caravan Park, 46 Merry Beach Road, Kioloa NSW 2539. |
| `identity_exploren_location_1380_20260909.json` | [Location 1380](https://exploren.com.au/find-a-charger/?charger_location=1380); POST detail response | RI06: Milton Ulladulla Exservos Club, 212–222 Princes Highway, Ulladulla NSW 2539. |

All three detail requests used the public
[`admin-ajax.php` endpoint](https://exploren.com.au/wp-admin/admin-ajax.php), with
action `exploren_get_location_detail` and the respective location ID. The POST
method, action, location ID and published location URL are retained in each
manifest. The JSON contains the publisher's HTML detail response; it is not a
hand-transcribed address or a screenshot. The identity stage verifies the raw
hashes and request metadata, then parses the actual map element and detail
name/address before applying the explicitly listed source-record membership.

The original source observations, charger counts, ratings and representative
coordinates remain intact. In particular, the current Exservos detail lists
two chargers, which does not replace the historical source's four-plug records.
The shared map and each separate detail response produce six rows in
`reviewed_identity_evidence`, retaining review ID, source-file foreign key, role,
operator element ID and hash. The earlier identity groups RI01–RI03 use their
guarded source observations; these Exploren documents are not claimed as their
evidence.

These POST responses are frozen snapshots. The generic GET acquisition and
dynamic candidate-staging commands do not reconstruct them. A missing snapshot
requires restoration of the reviewed original or a new documented review;
changing a stored hash or replacing POST evidence with a GET response is not a
valid refresh. The build and validation stages verify the archived identity
evidence. Public access to the operator endpoint does not imply an open reuse
license or establish present availability.

## Later DC identity and source-quality evidence

RI07 and RI08 add four complete successful GET originals. The review preserves
the complete member rows and differing power/plug observations. It establishes
one project location per group, not an identical equipment inventory across
time. Neither a failed Tesla response nor a general network statement supplies
these decisions.

| Original under `data/raw/reviewed/` | Publisher and role |
| --- | --- |
| `identity_campbelltown_installation_20260909.html` | [Council visitor publication](https://visitcampbelltown.com.au/tesla-ev-charging-station-campbelltown-catholic-club/), 12 Tesla Superchargers at the Catholic Club. |
| `identity_campbelltown_address_20260909.html` | [Venue contact page](https://cathclub.com.au/contact/), 20–22 Camden Road, Campbelltown 2560. |
| `identity_mount_annan_site_20260909.html` | [Shell station 10110865](https://find.shell.com/au/fuel/10110865-shell-reddy-express-mount-annan/en_AU), EV charging, the exact street/locality and venue point. |
| `identity_mount_annan_supplier_20260909.html` | [SwitchDin installation account](https://www.switchdin.com/resources/ultrafast-ev-chargers-live-in-an-australian-first), the supplier's own Viva/Reddy Express Mount Annan project; not a Viva-published page or independent proof of source plug counts. |
| `quality_dapto_locality_20260909.geojson` | [Complete NSW Dapto locality](https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/MapServer/2/query?where=suburbname%3D%27DAPTO%27&outFields=%2A&returnGeometry=true&outSR=7844&f=geojson), OBJECTID 26918, postcode 2530; source row 1000's point is inside this polygon while its address says 2023. Supports a warning, not an unrecorded postcode/point correction. |
| `identity_pending_balgowlah_relocation_20260909.html` | [Property-owner relocation announcement](https://www.balgowlahvillage.com/whats-on/diy-solar-windmill-7nyym), P3 removal/P2 installation and changed counts. Retained as counterevidence against automatic identity merging. |
| `identity_pending_uow_ev_parking_20260909.html` | [University EV parking page](https://www.uow.edu.au/about/locations/wollongong/getting-to-campus/parking/where-to-park/electric-vehicle-parking/), identifies the P8 DC installation. |
| `identity_pending_uow_p8_221_20260909.json` | [Official UOW P8 map node](https://maps.uow.edu.au/api/map-nodes/221/), complete polygon: source rows 969/1063 are outside it, about 309.12 m away. The P8 six-port description does not resolve those source identities. |

Every listed original has its paired URL/time/hash/byte manifest. The three
pending-identity originals are deliberately not applied as coordinate or
matching rules. `config/reviewed_source_issues.json` pins the Dapto warning.
The original postcode fields and point remain unchanged; it is an UPCOMING
record and does not enter the DC denominator. Nineteen truncated operator
labels receive `operator_label_review_required`; their full entity or network
is not guessed. Database validation reconstructs both warning classes and
rejects missing or changed audit entries.

## Temporal and retrieval limits

### Later Evie Council identity evidence (10 September 2026)

Four complete HTTP 200 originals support the two individually guarded Cowell
Street and Parraween Street identity reviews. Their manifests record URLs,
capture times, byte counts and SHA-256; the configuration pins those hashes and
the identity parser checks the actual venue, operator and charging-bay statements.

| Original under `data/raw/reviewed/` | Publisher and evidence role |
| --- | --- |
| `identity_cowell_council_proposal_20260910.html` | [Hunters Hill Council proposal and update](https://connect.huntershill.nsw.gov.au/electric-vehicle-charging-proposal): Evie at 3A Cowell Street, one charger/two bays and the kerbside funding programme. |
| `identity_cowell_council_operation_20260910.html` | [Council FAQ](https://connect.huntershill.nsw.gov.au/ev/widgets/464182/faqs): an operating Evie public charger at Cowell Street car park, Gladesville. |
| `identity_parraween_council_installation_20260910.html` | [North Sydney Council installation announcement](https://www.northsydney.nsw.gov.au/news/article/310/north-sydney-powers-up-with-60-new-ev-charging-stations): Parraween Street, Cremorne, Evie, four bays and 75 kW DC. |
| `identity_parraween_council_carpark_20260910.html` | [Council car-park directory](https://www.northsydney.nsw.gov.au/directory-record/134/parraween-street-car-park-cremorne): the car park, Evie and two dual chargers/four bays. The directory does not separately certify number 106. |

The source records and Council evidence jointly support two venue identities;
the evidence does not supply replacement coordinates or authorize summing
duplicate equipment counts. The unavailable Hunters Hill news page is not
represented as a successfully archived original. See
[the full identity review](identity_evie_council_20260910.md).

The existing `nrma_network.html` original and its manifest establish both
`/cars-and-driving/electric-vehicles/charging-network` and the resolved
`/electric-vehicles/charging` as NRMA network pages. The Yass row 731 OSM URL
therefore supplies `operator_network_map_url` at operator scope, with its OSM
provenance retained. Station subpaths, query strings and fragments are not
generalized into this rule.

The additional Dan Murphy's matching exception uses an attributed short extract
of the [official Batemans Bay store page](https://www.danmurphys.com.au/stores/NSW-Batemans-Bay-1847),
observed on 9 September 2026. Its address range supports the compatibility of
the two house numbers. `dan_murphys_batemans_bay_address_excerpt_20260909.txt`
is a transcript of rendered-page extraction, **not an original HTTP response**;
its manifest explicitly records this distinction. The downloaded HTML was an
application shell without the address and is not represented as evidence.
The excerpt is distributed as reviewed evidence and is not recreated by a cold
download. The exception is bound to the source/external records and evidence
hashes, and does not verify current prices, hardware or operating status.

The seven reviewed coordinate corrections still require their ten full archived
address originals. This separate matching exception does not weaken that rule.

The current TfNSW file is named `ev_20251216.csv`, but its official resource
metadata identifies an April 2026 effective date. The current file and several
historical-looking URLs were checked and served identical bytes; none established
an unchanged December 2025 snapshot. The [version investigation](source_version_review_20260908.md)
records this unresolved interpretation. Dataset upload/retrieval dates, OCM export
dates and per-station observation dates are not interchangeable.

The NRMA KML carries a November 2022 title. A later download date does not make
its station positions or availability current. OSM and KML may share upstream
information, so agreement is corroboration rather than demonstrated source
independence. The earlier Wollongong council-minute URLs returned HTTP 403;
their search-index excerpts were not accepted as original files. That is a
historical retrieval limit, not the current correction decision: the later
complete NRMA article and government planning PDF above now support its
individual OCM/KML review. Walcha uses official map/address originals and OSM
landmark geometry; its old KML is explicitly not used as nearby corroboration.

GET acquisition verifies cached hashes and byte counts, including the configured
expected hashes for reviewed correction originals. A missing cached GET body
can be restored only if the download still matches its saved manifest and any
review pin. Frozen POST originals and the rendered-page excerpt require their
supplied snapshots; they are not recreated by the generic downloader. Changed
publisher content requires a new source observation and, for reviewed evidence,
another explicit review.

`scripts/stage_source_candidates.py --label <unique-label>` stages dynamic
observations in an isolated version directory and reports changed bytes and
affected reviews. It preserves the active cache and verification evidence.
Its network behavior is tested with simulated providers; the delivered run does
not claim a complete new live download of every dynamic provider.

No APIs that charge per request are used. No emails or messages were sent to data
publishers. A successful automated source match is not an operator certification
of current data accuracy.

## New Italy locality evidence and matching follow-up on 10 September

The New Italy regional review adds three complete originals: the NSW Spatial
Services NEW ITALY polygon query, the New Italy Museum's own homepage and the
Richmond Valley Council 2020 statement-of-reasons table. Exact URLs, capture
times, lengths and SHA-256 values are in the adjacent manifests for
`data/raw/reviewed/regional_new_italy_*_20260910.*` and in `source_snapshot`.
The museum's Tesla charging statement is venue evidence; the city decision
DA2021/0125 connects its street address to the legal New Italy locality. The
museum's Woodburn postal town is not used to replace that locality. Neither
page supplies a surveyed bay coordinate. The original false postcode-conflict
result is preserved while an additional geographic conflict is flagged.
See [the current decision and safeguards](friend_review_actions_20260910.md).

Additional complete planning and venue originals used for the three priority
OSM matching reviews are listed in
[the targeted matching follow-up](friend_matching_followup_20260910.md).
These September captures add evidence context, not historical station attributes
or new accepted matches. A planning approval alone is not proof of operation.
