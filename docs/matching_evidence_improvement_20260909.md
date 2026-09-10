# Evidence review of five low-confidence site associations

Review date: 9 September 2026. This document records a targeted review of five existing associations. Four have additional first-party support for the same charging venue (`support_with_limits`); the Stanley Street OCM association remains uncertain and is withheld (`withheld_pending_location_evidence`). The review does not treat failure to find independent evidence as proof of a wrong match, change matching thresholds, or relocate the source records.

The distances and record IDs below refer to the submitted-data baseline examined during this review. New first-party pages are observations retrieved on the review date, not proof that every connector, tariff or operating status was the same in December 2025. Original bytes and retrieval metadata are retained under `data/raw/reviewed/matching_*`; derived text, rendered PDF pages and the baseline query result remain in the isolated review workspace outside the submission.

## Decisions and precise evidence locations

| Source row / record ID | Existing external association | Distance | Evidence decision |
| --- | --- | ---: | --- |
| 330 / `r_c78c8f758d2c01a9df3a` | JOLT 55, `GGR008` | 99.48 m | Retain; first-party car-park and intersecting-road evidence supports the venue, with address/pin precision limits. |
| 128 / `r_4d8fb17f73718e5d960b` | OCM 272673 | 225.02 m | Retain the venue association; operator and venue independently identify the site. The OCM pin and old connector attributes are not thereby validated. |
| 216 / `r_30c4868b9fef2b7494dd` | OCM 192687 | 236.96 m | Withhold pending location evidence; retain JOLT 52. This is not a confirmed wrong-match finding. |
| 833 / `r_fb26f40a346a9f379693` | OSM `node/11425340896` | 97.29 m | Retain; the official Ampol site supplies the missing venue/address context. |
| 681 / `r_43dc33a48ec2827abc63` | OSM `node/11129535113` | 94.30 m | Retain; the official Ampol eastbound site supplies the missing venue/address context. |

### 330 — Mortdale: Cook Lane / Cook Street

The source record identifies JOLT at `22 Cook Ln, Sydney, 2223`, while the archived JOLT map identifies `GGR008`, Mortdale, at `30-38 Cooks Street, Mortdale NSW 2223`. The source point is `(-33.9701502, 151.0801331)` and the JOLT point is `(-33.9697116, 151.081072)`.

Georges River Council's traffic agenda of 3 May 2022, item `TAC059-22`, identifies JOLT charging beside the Cook Street car park. The plan is on **PDF page 43 / printed page 39**. It draws the charger and a six-metre charging bay on Cook Street immediately beside its junction with Cook Lane. The 1 October 2025 agenda, item `LTF077-25`, **page 27 and plan on page 31**, identifies the existing JOLT installation and repeats the same road/car-park layout.

These are public authority plans identifying both roads and the charging bay; they support keeping the nearby Mortdale venue association despite different address strings. They do not prove that the two recorded coordinates locate the same physical socket. No general rule equating `Lane` and `Street` is justified by this individual case.

Primary originals:

- `matching_georges_river_20220503_agenda.pdf`: [Council agenda, 3 May 2022](https://georgesriver.infocouncil.biz/Open/2022/05/TAC_03052022_AGN_AT.PDF).
- `matching_georges_river_20251001_agenda.pdf`: [Council agenda, 1 October 2025](https://georgesriver.infocouncil.biz/RedirectToDoc.aspx?URL=Open%2F2025%2F10%2FLTF_01102025_AGN_AT.PDF). The manifest records the resolved direct PDF URL.
- Existing immutable operator original: `data/raw/jolt_map.html`, record `GGR008` / JOLT ID 55.

### 128 — MarketPlace Leichhardt

Both the source record and OCM 272673 name `128 Flood Street, Leichhardt, 2040`; the external title is MarketPlace Leichhardt. The source point is `(-33.88518, 151.148629)` and the OCM point is `(-33.883514, 151.150017)`.

The current official Evie map provides a direct site record: **JSON array entry with `id="4505"`**, `store="MarketPlace Leichhardt"`, address `128 Flood Street`, and coordinates `(-33.8851799059, 151.148629067)`. This agrees with the source coordinate to centimetres of numeric rounding; it is an operator-published point, not a surveyed accuracy claim. The independently published shopping-centre information page identifies the encompassing address **122–138 Flood Street**, the corner of Marion and Flood Streets, and **four EV chargers in the basement car park** under `Amenities → EV Chargers`.

The Evie response was retrieved using the publicly exposed map interface: `find-a-charger` publishes `wpslSettings.ajaxurl`, and its archived map script uses HTTP GET with `action=store_search`, `lat`, `lng`, `max_results`, and `search_radius`. The archived request uses the source coordinate and a five-kilometre search radius. The complete response, including all five returned sites, is preserved; it is not an edited extraction containing only the desired result. No account, private API token or form submission was used.

This provides strong same-venue support. The 225 m OCM displacement remains a precision limitation: the review does not silently replace the OCM coordinate or claim to have independently georeferenced it to a basement bay. The current operator JSON reports four 75 kW CCS2 connectors (`MS019A` and `MS019B`, two connectors each), whereas the older OCM snapshot reports different hardware. The reviewed identity decision does **not** certify the old connector mix or update tariffs/status automatically; those are separate attribute and temporal-provenance decisions.

Primary originals:

- `matching_evie_find_a_charger.html`: [Evie map page](https://evie.com.au/find-a-charger/).
- `matching_evie_locator_script.js`: [Public map script](https://evie.com.au/wp-content/plugins/wp-store-locator/js/wpsl-gmap.min.js?ver=2.3.23), locator `action: "store_search"` and `e.get(wpslSettings.ajaxurl, ...)`.
- `matching_evie_leichhardt_station_search.json`: [Archived public station query](https://evie.com.au/wp-admin/admin-ajax.php?action=store_search&lat=-33.88518&lng=151.148629&max_results=50&search_radius=5), entry `id="4505"`.
- `matching_leichhardt_centre_info.html`: [Centre information](https://www.marketplaceleichhardt.com.au/centre-info/), `Location / Getting Here` and `Amenities / EV Chargers`.
- `matching_leichhardt_centre_map.html`: [Centre map](https://www.marketplaceleichhardt.com.au/centre-map/), embedded `mapplic-map` JSON, layer `stores-basement`.
- `matching_leichhardt_basement_map.svg`: [Original basement SVG](https://www.marketplaceleichhardt.com.au/wp-content/uploads/2025/10/map_basement_202507.svg).

The original SVG is retained intact. Its drawing has no external `href`, `xlink:href` or CSS `url(...)` dependencies. The containing interactive HTML also refers to live scripts, styles and other floors that are not a complete offline website archive. The SVG is a floor plan, not a latitude/longitude reference; the explicit four-charger/basement assertion above comes from the centre's text, not from interpreting a rendered image as geographic proof.

### 216 — Stanley Street, Peakhurst: uncertainty remains

The source record identifies JOLT at `17 Stanley St, Sydney, 2210`, point `(-33.96212217, 151.0635736)`. The independent operator association already present in the project is JOLT 52 / `GGR005`, address `17 Stanley St, Peakhurst NSW 2210`, point `(-33.9621222, 151.0635726)`, about 0.1 m away. OCM 192687 identifies `Stanley St Peakhurst NSW`, address `17-25 Stanley St`, but places its point `236.96 m` away at `(-33.961219, 151.065897)`.

The 2022 Council agenda, **PDF page 39 / printed page 35**, specifies the JOLT site adjacent to property 26. Its plan on **PDF page 42 / printed page 38** draws the bay immediately in front of the parcel marked **26–28**. The 2025 agenda, **pages 27 and 30**, confirms an existing JOLT bay in the same position. These documents strengthen the evidence for a JOLT station on this street. They do not supply numeric coordinates or an OCM identifier, and this review has not independently placed the displaced OCM point onto that bay or demonstrated that it refers to another charger.

Therefore the OCM link is **not independently verified**, and a wrong match is **not established**. The final decision is **`withheld_pending_location_evidence`**: withhold this individual OCM association while retaining the much stronger JOLT association separately. The baseline impact is removal of three OCM-derived values: `dc_connector_types`, `usage_cost_text` (`0.40`), and `usage_type`. The JOLT `GGR005` station code and operator website remain; newly integrated operator details can be assessed separately. The OCM raw object remains archived, and no source coordinate, SA4 assignment, or charger record is removed because this external association is uncertain. Integration applies an explicit single-association exclusion bound to the original record values and source snapshot hashes, retaining the rejected candidate for audit rather than widening a generic matching threshold.

Relevant originals are the same two Council PDFs above, existing `data/raw/jolt_map.html` entry `GGR005`, and existing `data/raw/ocm/OCM-192687.json`. The review does not equate the Council's adjacent property number with the charging operator's postal address through a new generic address rule.

### 833 — Ampol Foodary Werrington

The source address is `Cnr Dunheved Rd & Henry Lawson Dr, Werrington, NSW, 2747`. The OSM node has AmpCharge operator tags and CCS2/CHAdeMO sockets but lacks a street address or site name, so the original association depended heavily on proximity and operator identity.

The official Ampol Foodary Werrington page gives the same corner address, explicitly offers AmpCharge, and lists charging bays for CHAdeMO and CCS2. Its embedded JSON-LD `GeoCoordinates` is **`(-33.745872, 150.741075)`**, approximately **44.05 m** from OSM `node/11425340896` and **53.47 m** from the source point. The exact address, matching network and independently published site point fill the missing venue context.

Retain the association. Distances indicate agreement at service-station site scale; the JSON-LD point is not assumed to be the exact charger position. The page's current connector powers are not used to overwrite the frozen source's original power.

Original `matching_ampol_werrington.html`: [Ampol Foodary Werrington](https://locations.ampol.com.au/en/ampol-foodary-werrington), address block, `EV charging`, and JSON-LD `geo`.

### 681 — Ampol Foodary Gosford West, eastbound

The source address is `69-71 Central Coast Hwy, Gosford West, NSW, 2250`. The official **eastbound** page identifies that exact numbered site, offers AmpCharge, and lists CHAdeMO and CCS2 charging bays. Its JSON-LD point is **`(-33.427473, 151.321276)`**, approximately **17.75 m** from OSM `node/11129535113` and **101.67 m** from the source point. This is the numbered eastbound site; the opposite westbound site and other Gosford West Ampol sites are not interchangeable.

Retain the association. The official point and address supply strong site evidence despite the OSM node's missing address/name. The old OSM access and fee tags remain dated observations; the identity review does not certify a live tariff, operating status or precise socket position.

Original `matching_ampol_gosford_eastbound.html`: [Ampol Foodary Gosford West Eastbound](https://locations.ampol.com.au/en/ampol-foodary-gosford-west-eastbound), address block, `EV charging`, and JSON-LD `geo`.

## Archive and reproducibility boundary

Every new original is paired with its standard `.meta.json`, preserving the actual request URL, resolved URL, retrieval time, SHA-256 and byte count from the research download. Promotion into `data/raw/reviewed/` was a byte-for-byte copy; none of the existing raw inputs or their hashes was replaced. The archive/research step made no matcher or output changes; the separate integration step implements the single withheld association and synchronises its derived attributes.

The HTML, SVG, JavaScript, PDF and JSON originals are complete HTTP response bodies. PDF text extracts and page PNGs used during review are derived aids and are not substitutes for those originals. A later live request can return changed website markup, station status or prices. Exact restoration of the frozen bytes therefore depends on the supplied cache when the publisher no longer serves those bytes; no manifest hash should be removed to disguise a changed observation.

This review supports four venue associations with stated limits and withholds one unresolved external-point association. It does not claim five fully verified matches, measured physical bay coordinates, or universally current augmentation attributes.
