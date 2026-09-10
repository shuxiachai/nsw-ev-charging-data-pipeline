# Final review of address-missing OSM associations

Review date: 10 September 2026. This is an **AI-assisted original-evidence review**, not independently labelled human ground truth or a precision estimate. It covers the entire current SQL queue of **27 accepted OSM associations whose external address is missing and whose source-to-OSM distance is at least 50 m**. Cowra source row 709 is already one of these 27 and is not counted twice. The queue contains 27 distinct locations and OSM entities. No matching threshold, configuration, coordinate, source observation, or accepted link is changed by this report.

The companion [27-row CSV](final_matching_review_20260910.csv) contains exact current record IDs, source rows, provider IDs, distances, original 12-field JSON, OSM tags, per-case support/counter-evidence, decision, and source-file/URL/SHA-256/locator references. The source row is the stable original CSV row convention used by the pipeline. All 27 source-to-OSM distances are copied from the actual accepted-match output; additional official-point distances use the WGS84 ellipsoid (pyproj.Geod). A small numerical distance is not a claim of survey accuracy.

## What this improves, and what it does not establish

New complete operator or venue originals supply missing context for Broadway, Sovereign Place, Marulan Northbound, Lithgow, Rydalmere, Grove Square, Batemans Bay, Narellan, Villawood and Gumly Gumly. Existing first-party Ampol Werrington/Gosford Eastbound and NRMA Grafton evidence is reused rather than counted as new research. Cowra gains a Council venue/operating-context original and a complete OSM edit history. The remaining cases are explicitly retained pending stronger site evidence; failure to obtain a page is not evidence that the association is wrong. **No confirmed wrong-site association was established by this bounded review**, and no automatic withdrawal is recommended. This does not mean all 27 associations are correct.

The especially useful address bridges are Evie `7643` (`51/53A Orient St`, linking the Batemans Bay source/OCM variants), Exploren location `1847` (316 Victoria Road plus explicit left-of-entrance charging location), and the exact BP/Ampol site addresses. These support **charging venue identity**, not identical physical sockets, underground-floor geometry, power, connector totals, access rules or historical prices. Current September 2026 responses are not retrospective proof of every December 2025 attribute. A matching decision must remain separate from attribute-conflict resolution.

Twelve direct Tesla site-page requests returned HTTP 403. Their response bodies and retrieval metadata remain in the isolated research directory; they are **not promoted as successful evidence**. Some official-page text was visible through search extraction (including Goulburn and Moonee Beach); it is labelled as such and is not passed off as a complete archived original. No access restriction was bypassed.

## Case decisions

In the table, **supported** means venue support with attribute/point limits, **pending** means independent site evidence remains incomplete, and **connector conflict** means the venue is supported while connector truth remains unresolved. Precise evidence and limitations for every row follow in the CSV and case notes.

| Source row | Record ID | OSM entity | Distance (m) | Decision |
| --- | --- | --- | ---: | --- |
| 3 | `r_8ac1bf727d3903e70216` | `node/10590006365` | 65.94 | pending site evidence |
| 7 | `r_41d8e6cbe1784306a79e` | `node/5438383393` | 66.18 | supported; attributes unverified |
| 138 | `r_2aa223558e07057e448b` | `node/6656345063` | 58.59 | supported; attributes unverified |
| 172 | `r_681c43722a7f3a3851c3` | `node/11433418128` | 55.46 | supported; attributes unverified |
| 194 | `r_b7b71536d24d27dbbf44` | `node/10263943171` | 52.47 | supported; attributes unverified |
| 289 | `r_7516435bb8f765735fd6` | `node/12015928951` | 72.03 | supported; attributes unverified |
| 344 | `r_cf43c5a129de64bbcfe6` | `node/6816990777` | 84.89 | pending site evidence |
| 422 | `r_54984b72f9c24952867a` | `node/12284563526` | 54.90 | pending site evidence |
| 452 | `r_85e6119c00db7a24c9f7` | `node/12990581486` | 63.47 | supported; attributes unverified |
| 483 | `r_390030bcf0b1a43ee5af` | `way/762728901` | 87.76 | pending site evidence |
| 501 | `r_2f06d991990d90a7f810` | `node/13020827820` | 59.84 | supported; attributes unverified |
| 613 | `r_531a8cdb6b482f190a0d` | `node/7370327570` | 93.23 | supported; attributes unverified |
| 639 | `r_ca4695297ed5ae3c96a8` | `node/9467315676` | 54.31 | pending site evidence |
| 681 | `r_43dc33a48ec2827abc63` | `node/11129535113` | 94.30 | supported; attributes unverified |
| 709 | `r_05032d2862c49d60bde6` | `node/8253300980` | 95.70 | supported; connector conflict |
| 833 | `r_fb26f40a346a9f379693` | `node/11425340896` | 97.29 | supported; attributes unverified |
| 918 | `r_1b8c5edb72ec07127969` | `node/13018467011` | 71.50 | supported; attributes unverified |
| 1309 | `r_86b0088690bec6020cef` | `node/12564147445` | 99.13 | pending site evidence |
| 1327 | `r_468b05218c0c2bf17602` | `node/11155180657` | 87.25 | pending site evidence |
| 1360 | `r_f26e53dda169309ca2b1` | `node/12437997269` | 69.09 | pending site evidence |
| 1566 | `r_0eda849f14301ed0eb0a` | `node/13146732524` | 73.27 | pending site evidence |
| 1635 | `r_e8ea5f0fcfd077929751` | `node/11386697708` | 51.50 | pending site evidence |
| 1720 | `r_83adde345908446014d1` | `node/13185195202` | 61.78 | supported; attributes unverified |
| 1742 | `r_9e59feb5c2b387e92904` | `node/12221169446` | 71.20 | pending site evidence |
| 1771 | `r_da5d50a5aa67ca41070c` | `node/11842613041` | 87.71 | pending site evidence |
| 1840 | `r_16df539c3c8ea020c0aa` | `node/12884912873` | 53.80 | supported; attributes unverified |
| 1945 | `r_85ce7d2a04939146d90c` | `node/10258355351` | 76.81 | pending site evidence |

Decision counts: `retained_pending_site_evidence` = 13, `site_supported_attributes_unverified` = 13, `site_supported_connector_conflict_retained` = 1. These are review categories, not validation accuracy.

### 3 — 01 Wallgrove Road, Sydney, 2766

BP's own location 6795 identifies an Eastern Creek station with actual location.products containing bppulse; its point is 50.26 m from OSM. Existing OCM 272521 calls the venue BP Truckstop.

Limit/counter-evidence: The source says 01 Wallgrove Road, whereas BP publishes Lot 558 OLD WALLGROVE ROAD. The official page supports a nearby BP charging venue but does not establish this address alias or the exact bay; do not infer equality from the shared road substring.

- [final_matching_20260910_bp_3.html](../data/raw/reviewed/final_matching_20260910_bp_3.html): script[data-page=app] JSON props.location; locationId=6795.
- [OCM-272521.json](../data/raw/ocm/OCM-272521.json): ID=272521; AddressInfo and Connections; provider context only.

### 7 — 1 Bay St, Sydney, 2037

Broadway's own parking FAQ identifies eight Tesla fast chargers on B2 near the Bay Street exit. Its centre information gives 1 Bay Street, Glebe 2037. This supports the OSM Broadway ref and source venue.

Limit/counter-evidence: The same FAQ separately describes seven universal chargers. Source 16 plugs, OSM capacity 8, and venue eight Tesla units have different counting scopes; no total is replaced. The floor-plan/bay coordinates are not independently surveyed, and the Tesla request returned 403.

- [final_matching_20260910_broadway_7_parking.html](../data/raw/reviewed/final_matching_20260910_broadway_7_parking.html): Electric Vehicle Charging Stations FAQs: location and number of stations.
- [final_matching_20260910_broadway_7_venue.html](../data/raw/reviewed/final_matching_20260910_broadway_7_venue.html): centre address: 1 Bay Street, Glebe NSW 2037.

### 138 — 132 Pound Street, Grafton, 2460

The unchanged official NRMA KML has a named Grafton fast-charger point 19.63 m from source and 39.04 m from OSM. OCM 190393 identifies Grafton Public Library on Pound Street.

Limit/counter-evidence: The KML is operator context, not a cadastral or socket survey. The old OSM capacity=1 and two cable tags are not a source plug-count contradiction by themselves. No new first-party street-number or hardware evidence was obtained.

- [OCM-190393.json](../data/raw/ocm/OCM-190393.json): ID=190393; AddressInfo and Connections; provider context only.
- [nrma_stations.kml](../data/raw/nrma_stations.kml): NRMA Fast Charger Grafton.
- [nrma_network.html](../data/raw/nrma_network.html): published official charging-network map.

### 172 — 15 Chancellors Dr, Thrumster , 2444

Sovereign Hills' own announcement identifies Tesla Superchargers at Sovereign Place Town Centre and gives 15 Chancellors Drive, postcode 2444.

Limit/counter-evidence: The announcement states six stalls opened on 21 December 2023; source and OSM report 12. Expansion or counting/time differences are possible, not proved. The historical announcement supports venue identity only and must not overwrite the later observation.

- [final_matching_20260910_sovereign_172.html](../data/raw/reviewed/final_matching_20260910_sovereign_172.html): Sovereign Place welcomes Tesla Supercharger site; opening 21 December 2023; venue address.
- [OCM-480398.json](../data/raw/ocm/OCM-480398.json): ID=480398; AddressInfo and Connections; provider context only.

### 194 — 15666 Hume Hwy, Marulan, 2579

BP station 2330 publishes 15666 HUME HIGHWAY, Marulan North 2579, and bppulse in this station's products. The official point is 28.75 m from source and 78.91 m from OSM; northbound identity distinguishes the other-side station.

Limit/counter-evidence: BP's petrol-station point is not an exact charging-bay point. Connector model, power and number are not confirmed by the generic bppulse product marker.

- [final_matching_20260910_bp_194.html](../data/raw/reviewed/final_matching_20260910_bp_194.html): script[data-page=app] JSON props.location; locationId=2330; products bppulse.
- [OCM-238126.json](../data/raw/ocm/OCM-238126.json): ID=238126; AddressInfo and Connections; provider context only.

### 289 — 2 Stewart St, Lithgow, 2790

Evie's complete public response entry 5904 names Hungry Jacks Lithgow at 2 Stewart Street. Its operator point matches the source to 0.06 m of numeric rounding and is 71.98 m from OSM. HS013A/B each list CHAdeMO 63 kW and CCS2 150 kW.

Limit/counter-evidence: The current operator uses Bowenfels 2790 while the source uses Lithgow 2790; this individually observed venue context is not a general locality alias. The OSM pin remains displaced. Current prices/status are not evidence of December 2025 values.

- [final_matching_20260910_evie_289.json](../data/raw/reviewed/final_matching_20260910_evie_289.json): complete JSON response; id=5904; address, lat/lng, evie_chargers HS013A/HS013B.
- [matching_evie_find_a_charger.html](../data/raw/reviewed/matching_evie_find_a_charger.html): published wpslSettings.ajaxurl.
- [matching_evie_locator_script.js](../data/raw/reviewed/matching_evie_locator_script.js): public GET action=store_search.

### 344 — 2285 Pacific Hwy, Heatherbrae, 2324

OSM has the specific Tesla heatherbraesupercharger ref, and OCM 79490 names Heatherbrae Supercharger at 2285 Pacific Highway. The venue's own page places Heatherbrae's Pies at the Pacific Highway/Masonite Road corner.

Limit/counter-evidence: The archived venue page does not explicitly identify Tesla chargers, so it does not independently prove the association. Tesla's original page returned 403. Twelve source plugs and OSM six stalls with two cable tags must not be added or equated without a counting definition.

- [final_matching_20260910_heatherbrae_344.html](../data/raw/reviewed/final_matching_20260910_heatherbrae_344.html): Our location / Pacific Highway and Masonite Road; no charger-specific statement identified.
- [OCM-79490.json](../data/raw/ocm/OCM-79490.json): ID=79490; AddressInfo and Connections; provider context only.

### 422 — 3 Corkhill Pl, Bega, 2550

Old Bega Hospital's own location page identifies its reserve at 3 Corkhill Place, Bega 2550, with cadastral parcel Lot 296 DP728021. This identifies the source venue.

Limit/counter-evidence: This page does not identify Chargefox or a DC charger. OSM has no address or station-specific name and only two CCS2 tags. The 54.90 m same-operator association remains unverified at charger/site level; no contrary charger identity was established.

- [final_matching_20260910_bega_422_location.html](../data/raw/reviewed/final_matching_20260910_bega_422_location.html): Old Bega Hospital - Location; 3 Corkhill Place and Lot 296 DP728021.

### 452 — 316 Victoria Rd, Sydney, 2116

Exploren's complete published map has location_id 1847, Bunnings Rydalmere, at the source point. Its public detail response gives 316 Victoria Road, chargers 4923 and 4924, both DC 120 kW, and a location left of the store entrance by Victoria Road.

Limit/counter-evidence: This is strong venue context for the 63.47 m OSM association, not proof that the OSM coordinate is a surveyed bay. Current device IDs and ratings are retained in review evidence without rewriting source values.

- [final_matching_20260910_exploren_current_map.html](../data/raw/reviewed/final_matching_20260910_exploren_current_map.html): public locations entry location_id=1847; public detail action/nonce.
- [final_matching_20260910_exploren_452_published_detail.json](../data/raw/reviewed/final_matching_20260910_exploren_452_published_detail.json): success=true; Bunnings Rydalmere; address; chargers #4923/#4924; operational location text.

### 483 — 3483 Jerrys Plains Rd, Jerrys Plains, 2330

OSM explicitly describes Hollydene Supercharger with singletonnswsupercharger ref; OCM 129982 calls the venue Hollydene and gives 3483 Golden Highway. The Hunter Valley tourism organisation's original listing names Tesla supercharging and 3483 Golden Highway, Jerrys Plains.

Limit/counter-evidence: The tourism listing is first-published regional tourism context, not a Tesla or venue-owner equipment statement. The source uses 3483 Jerrys Plains Road; this road-name alias has not been independently established. The Tesla original returned 403; physical bay and old six-stall/twelve-cable scope remain unverified.

- [final_matching_20260910_hollydene_483.html](../data/raw/reviewed/final_matching_20260910_hollydene_483.html): Hollydene Estate amenities Tesla supercharging station; address 3483 Golden Hwy.
- [OCM-129982.json](../data/raw/ocm/OCM-129982.json): ID=129982; AddressInfo and Connections; provider context only.

### 501 — 375-383 Windsor Rd, Sydney, 2153

Grove Square's own site gives 375-383 Windsor Road and describes four Tesla 250 kW chargers on the ground level near the Old Northern Road exit, supporting the source and OSM capacity/ref context.

Limit/counter-evidence: The notice says available from 1 September without a year and that old chargers will be removed. This is a dated retrieval of a potentially changing installation; it cannot certify the December 2025 device configuration or unchanged bay. Tesla original returned 403.

- [final_matching_20260910_grove_501.html](../data/raw/reviewed/final_matching_20260910_grove_501.html): Centre Information: NEW TESLA SUPERCHARGES Quick Guide; footer address.

### 613 — 53A Orient St, Batemans Bay, 2536

Evie entry 7643 explicitly identifies Dan Murphy's Batemans Bay at 51/53A Orient St, linking the source 53A and OCM 190706 51 address variants. It lists MS193A with two CCS2 50 kW connectors; the point is 20.48 m from source and 74.98 m from OSM.

Limit/counter-evidence: The response also includes the separate Village Centre site 6798 at 1 Perry Street; that is not substituted. Current Evie price 0.77/kWh differs from old OSM fee=no, which is a dated attribute conflict, not proof of wrong venue. Source and external pins are unchanged.

- [final_matching_20260910_evie_613.json](../data/raw/reviewed/final_matching_20260910_evie_613.json): complete JSON response; id=7643 (not 6798); address 51/53A Orient St; MS193A.
- [OCM-190706.json](../data/raw/ocm/OCM-190706.json): ID=190706; AddressInfo and Connections; provider context only.
- [matching_evie_find_a_charger.html](../data/raw/reviewed/matching_evie_find_a_charger.html): published wpslSettings.ajaxurl.
- [matching_evie_locator_script.js](../data/raw/reviewed/matching_evie_locator_script.js): public GET action=store_search.

### 639 — 580 Princes Hwy, Sydney, 2232

OSM has Tesla kirraweesupercharger ref and six stalls. Existing OCM 191280 identifies South Village on Princes Highway, providing nearby contextual support for the source's 580 Princes Highway.

Limit/counter-evidence: No complete first-party charger/venue original was obtained for this association in the bounded review; Tesla returned 403. OCM is a second provider, not independent ground truth. Its nearby location does not certify the OSM pin or device group.

- [OCM-191280.json](../data/raw/ocm/OCM-191280.json): ID=191280; AddressInfo and Connections; provider context only.

### 681 — 69-71 Central Coast Hwy, Gosford West, NSW, 2250

The previously archived Ampol Foodary Gosford West EASTBOUND page identifies 69-71 Central Coast Highway, postcode 2250, AmpCharge and a point 17.75 m from OSM. This supplies the missing OSM address context.

Limit/counter-evidence: This reuses the completed 9 September review; no duplicated research or new resolution is claimed. Eastbound and opposite-side westbound sites are not interchangeable. Point and historical attributes remain independently qualified.

- [matching_ampol_gosford_eastbound.html](../data/raw/reviewed/matching_ampol_gosford_eastbound.html): LocalBusiness JSON-LD; exact source street/corner; AmpCharge EV charging.

### 709 — 77 Darling St, Cowra, 2794

NRMA KML names Cowra and is 6.60 m from OSM; OCM 156010 names Cowra Regional Art Gallery, 77 Darling Street. The Council's full PDF page 58, E2.3.a, explicitly places the NRMA fast charger in the Art Gallery carpark, separately from Council-owned Tesla units opposite the Visitor Centre.

Limit/counter-evidence: The OSM history added CCS1 on 29 March 2022 in version 3 and keeps it in latest version 4 (15 December 2022); OCM instead reports CCS2. Council confirms venue and paid operation, not connector shape. Preserve physical_connector_conflict and old fee=no disagreement; do not rewrite CCS1 as CCS2 or withdraw a supported site link merely to erase a hardware conflict.

- [final_matching_20260910_cowra_osm_history.xml](../data/raw/reviewed/final_matching_20260910_cowra_osm_history.xml): node 8253300980 versions 1-4; v3 socket:type1_combo; changeset 119049261.
- [final_matching_20260910_cowra_council_2025.pdf](../data/raw/reviewed/final_matching_20260910_cowra_council_2025.pdf): PDF page 58; E2.3.a; Dec 2024 column Art Gallery/fee for service; Jun 2025 column NRMA maintenance.
- [OCM-156010.json](../data/raw/ocm/OCM-156010.json): ID=156010; AddressInfo and Connections; provider context only.
- [nrma_stations.kml](../data/raw/nrma_stations.kml): NRMA Fast Charger Cowra.
- [nrma_network.html](../data/raw/nrma_network.html): published official charging-network map.

### 833 — Cnr Dunheved Rd & Henry Lawson Dr, Werrington, NSW, 2747

The previously archived Ampol Foodary Werrington page gives the exact Dunheved Road/Henry Lawson Drive corner, AmpCharge and the two connector types; its point is 44.05 m from OSM.

Limit/counter-evidence: This reuses the completed 9 September review. The petrol-station point and contemporaneous availability are not socket-level or December 2025 truth; coordinates and provider observations are retained.

- [matching_ampol_werrington.html](../data/raw/reviewed/matching_ampol_werrington.html): LocalBusiness JSON-LD; exact source street/corner; AmpCharge EV charging.

### 918 — NARELLAN RD CNR MAXWELL PL, Sydney, 2567

Ampol's Narellan page gives Narellan Road/Cnr Maxwell Place, postcode 2567, AmpCharge, and a JSON-LD point 21.84 m from OSM and 49.68 m from source.

Limit/counter-evidence: The page currently lists Bay01 CHAdeMO 125 kW and Bay02 CCS2 150 kW, whereas OSM/source counting differs. This supports the venue while leaving old connector/count/power observations separate.

- [final_matching_20260910_ampol_918.html](../data/raw/reviewed/final_matching_20260910_ampol_918.html): LocalBusiness JSON-LD geo/address; EV charging Bay01/Bay02.

### 1309 — 179-183 Hume St, Goulburn NSW 2580

OSM has specific Tesla ref 31614 and 20 CCS2 stalls, matching source count. Earlier official-page search extraction identified Tesla at 5 Lockyer Street, nearby but not the source's 179-183 Hume Street.

Limit/counter-evidence: The newly archived Council tourism brochure, PDF page 2, labels 179-183 Hume Street as Chargefox KFC South and puts Tesla at the Visitor Centre. Its printed update is 24 July 2024, before the source snapshot, so it cannot rule out a later Tesla installation; it also cannot establish the Hume/Lockyer site boundary. The Tesla full response was 403. This is a priority unverified alternative-address case, not a confirmed wrong association.

- [final_matching_20260910_goulburn_1309_brochure.pdf](../data/raw/reviewed/final_matching_20260910_goulburn_1309_brochure.pdf): PDF page 2; Chargefox KFC South 179-183 Hume Street; footer Updated 24/07/2024.

### 1327 — 188 Fernleigh Rd Glenfield Park NSW 2650 Australia

OSM Tesla ref 30889 has six CCS2 stalls; OCM 300153 identifies Wagga Wagga on Fernleigh Road, supporting the source road and six-plug context.

Limit/counter-evidence: No new complete first-party charger/venue evidence archived; Tesla returned 403. Provider agreement and 87.25 m distance do not certify the exact site or hardware.

- [OCM-300153.json](../data/raw/ocm/OCM-300153.json): ID=300153; AddressInfo and Connections; provider context only.

### 1360 — 2 Moonee Beach Rd Moonee Beach NSW 2450 Australia

OSM Tesla ref 32996 has 15 CCS2 stalls, and OCM 311704 explicitly gives 2 Moonee Beach Road, matching source address and count.

Limit/counter-evidence: The current official Tesla search extraction supports Moonee Beach Hotel and 15 chargers, but downloading its original returned 403. Search extraction is not a complete archived original or independent ground truth; retained pending stronger reproducible venue evidence.

- [OCM-311704.json](../data/raw/ocm/OCM-311704.json): ID=311704; AddressInfo and Connections; provider context only.

### 1566 — 477 Coolac Rd Coolac NSW 2727 Australia

OSM Tesla ref 33621 has 12 CCS2 stalls. OCM 461335 gives 477 Coolac Road, matching source address/count and the nearby OSM context.

Limit/counter-evidence: The full Tesla source returned 403; no new first-party original independently places this OSM point at the charging venue. Agreement of provider records can reflect shared information.

- [OCM-461335.json](../data/raw/ocm/OCM-461335.json): ID=461335; AddressInfo and Connections; provider context only.

### 1635 — 618 Dean St Albury NSW 2640 Australia

OSM Tesla ref 31612 has 16 CCS2 stalls; OCM 300154 names Albury and Stanley Street, consistent with a nearby Tesla venue.

Limit/counter-evidence: The source says 618 Dean Street, whereas OCM says Stanley Street. The alternative entrance/site-boundary explanation was not independently verified; Tesla full source returned 403. Retain this case as a priority address-context gap rather than claim exact-site confirmation.

- [OCM-300154.json](../data/raw/ocm/OCM-300154.json): ID=300154; AddressInfo and Connections; provider context only.

### 1720 — 850 Woodville Rd, Villawood 2163, NSW

Evie entry 7185 names Timezone Villawood at 824-850 Woodville Road, postcode 2163, encompassing source number 850. It lists four CCS2 DC 300 kW on MS190A and one separate AC Type2 on MS190B. The official point lies 51.04 m from OSM.

Limit/counter-evidence: The five connectors cover mixed DC/AC equipment; do not turn them into five DC plugs or overwrite source power 175 kW. Its 89.70 m offset from the source remains venue-level precision, not a corrected source point. The response's separate Guildford site is not selected.

- [final_matching_20260910_evie_1720.json](../data/raw/reviewed/final_matching_20260910_evie_1720.json): complete JSON response; id=7185 (not 6352); address; MS190A DC versus MS190B AC.
- [matching_evie_find_a_charger.html](../data/raw/reviewed/matching_evie_find_a_charger.html): published wpslSettings.ajaxurl.
- [matching_evie_locator_script.js](../data/raw/reviewed/matching_evie_locator_script.js): public GET action=store_search.

### 1742 — 9-17 Short St, Parkes NSW 2870

OSM Tesla ref 34173 and four CCS2 stalls agree with the source operator and four plugs near 9-17 Short Street.

Limit/counter-evidence: There is no accepted OCM cross-reference and no new complete first-party venue source; Tesla returned 403. This remains a proximity/operator association awaiting independent venue context, not a proved wrong match.


### 1771 — Corner Sturgeon St & Glenelg St Raymond Terrace NSW 2324 Australia

OSM has 12 Tesla stalls; existing OCM 297859 calls the venue Terrace Central on Glenelg Street, consistent with the source's Sturgeon/Glenelg corner.

Limit/counter-evidence: OSM has no station-specific ref or address. No new first-party original was archived locating these chargers; provider context is not independent confirmation. Exact venue boundary and historic device scope remain uncertain.

- [OCM-297859.json](../data/raw/ocm/OCM-297859.json): ID=297859; AddressInfo and Connections; provider context only.

### 1840 — 1 Tasman Rd, Gumly Gumly NSW 2652, Australia

BP station 4091 gives exactly 1 Tasman Road, Gumly Gumly 2652, and bppulse in the actual station's products. Its point is 27.31 m from OSM and 31.53 m from source.

Limit/counter-evidence: The operator's fuel-station point confirms charging at the venue, not each bay. Source six plugs versus OSM three CCS2 tags remains a separate counting/equipment observation, with no automatic replacement.

- [final_matching_20260910_bp_1840.html](../data/raw/reviewed/final_matching_20260910_bp_1840.html): script[data-page=app] JSON props.location; locationId=4091; products bppulse.

### 1945 — 162 Rouse St, Tenterfield NSW 2372, Australia

OSM has Tesla tenterfieldsupercharger ref and four CCS2 stalls; OCM 312274 names Coles Tenterfield with 1 Crown Street and four connectors.

Limit/counter-evidence: The source gives 162 Rouse Street. A shared Coles parcel or alternative entry is plausible but not established by a complete first-party original here. Tesla returned 403. Keep this alternative-address association explicitly unverified.

- [OCM-312274.json](../data/raw/ocm/OCM-312274.json): ID=312274; AddressInfo and Connections; provider context only.

## Cowra: preserve the physical connector conflict

The Council PDF was visually checked on **PDF page 58**, row **E2.3.a**. Its December 2024 column identifies the Art Gallery carpark NRMA fast charger as paid service; its June 2025 column confirms continued NRMA maintenance contact. The separate Council-owned Tesla chargers opposite the Visitor Centre are described as free. These statements must not be mixed across columns or sites.

The complete OSM history for node `8253300980` has four versions. Version 1 (23 December 2020) identifies NRMA; version 2 adds operator identifiers; version 3 (29 March 2022, changeset `119049261`) introduces `socket:type1_combo=1` and `socket:chademo=1`, both 50 kW; version 4 (15 December 2022) retains those connectors while changing the name to a description. OCM `156010` has CCS2 and CHAdeMO. The official KML point is 6.60 m from OSM and 90.18 m from the source; this supports venue identity but says nothing about CCS1 versus CCS2. The Council text likewise does not identify the physical connector. The current `physical_connector_conflict` therefore remains a useful unresolved warning, not an error to hide by guessing a connector type.

## Reproducibility and archive

The current queue was reconstructed from `osm_site_matches.csv` joined to `locations.csv` and `osm_sites.csv`, filtering blank external address and `distance_m >= 50`. The review freezes the exact 27 keys rather than sampling only easy confirmations. All newly promoted bodies below returned HTTP 200, have byte-for-byte SHA-256 and size checks against a paired `.meta.json`, and use new names. Existing raw data and manifests were not overwritten. Each manifest keeps the original URL, resolved URL, retrieval time, HTTP status and method. Exploren's successful detail retrieval used its public page's published read-only POST parameters; the manifest preserves those parameters, and the complete response is retained. It is a frozen evidence original, not a new generic POST acquisition feature.

The Evie responses are complete public search arrays, including alternative nearby sites. The existing archived Evie map and script publish the query interface. BP's `bppulse` evidence comes from the specific `props.location.products` array, not from a generic page-wide translation/configuration string. Exploren's map and detail response are retained together, with the station-specific `location_id=1847` and address verified. The tourism listing for Hollydene is explicitly treated as regional tourism context, not as Tesla's or the venue owner's own equipment record.

The isolated research folder also retains unsuccessful responses, parsed point calculations and the two visually checked PDF page renderings. These helper files are not substituted for original sources or required to run the existing pipeline. The formal CSV is the per-case ledger. This review adds evidence and makes unresolved cases visible; it does not create a new ground-truth dataset or certify a 100% match rate.

| New archived original | Public source | SHA-256 |
| --- | --- | --- |
| [evie_289.json](../data/raw/reviewed/final_matching_20260910_evie_289.json) | [original](https://evie.com.au/wp-admin/admin-ajax.php?action=store_search&lat=-33.48184889&lng=150.1361812&max_results=50&search_radius=5) | `fcedcf6877ad837e7021d2b573eafcd2c136a701308567c73208862fdf4ba97d` |
| [evie_613.json](../data/raw/reviewed/final_matching_20260910_evie_613.json) | [original](https://evie.com.au/wp-admin/admin-ajax.php?action=store_search&lat=-35.71073278&lng=150.1776366&max_results=50&search_radius=5) | `8ce431a5f05f7ff8d0db0dc2d120c4844372eee6f60e81b429fecd2bfb5a719a` |
| [evie_1720.json](../data/raw/reviewed/final_matching_20260910_evie_1720.json) | [original](https://evie.com.au/wp-admin/admin-ajax.php?action=store_search&lat=-33.8791212&lng=150.9776442&max_results=50&search_radius=5) | `160521f446ceb17faa685e32c12ca678aa10359e8053377045468aa9b9ec11fe` |
| [ampol_918.html](../data/raw/reviewed/final_matching_20260910_ampol_918.html) | [original](https://locations.ampol.com.au/en/ampol-foodary-narellan) | `f37f0a0e3b0f0da81bbfa7cae31ce48c42a024b3c330430b6f9b5beac767cc99` |
| [bp_3.html](../data/raw/reviewed/final_matching_20260910_bp_3.html) | [original](https://map.bp.com/en-AU/AU/gas-station/eastern-creek/bp-eastern-creek/6795) | `43dd86de1e438dcc7e9d9e8788dfb4a2f899e4bb417b02dfa1025fe3756606e5` |
| [bp_194.html](../data/raw/reviewed/final_matching_20260910_bp_194.html) | [original](https://map.bp.com/en-AU/AU/gas-station/marulan-north/bp-express-marulan-northbound/2330) | `287ae8e0799b4f1a0bf2762c5113665c6ba8be57a403d24372ce306b211c351f` |
| [bp_1840.html](../data/raw/reviewed/final_matching_20260910_bp_1840.html) | [original](https://map.bp.com/en-AU/AU/gas-station/gumly-gumly/bp-gumly-gumly/4091) | `207e344391c9c9220d70bd5d05e45aeed9aac6bf728eac3f3deb5ba01f702766` |
| [exploren_current_map.html](../data/raw/reviewed/final_matching_20260910_exploren_current_map.html) | [original](https://exploren.com.au/find-a-charger/) | `fca3d1a3c50a0e904d0439bf7e60e3db07fc4ffe07fce54217c418f2fb9780cd` |
| [exploren_452_published_detail.json](../data/raw/reviewed/final_matching_20260910_exploren_452_published_detail.json) | [original](https://exploren.com.au/wp-admin/admin-ajax.php) | `2931638fd8012a6930c53103396633d62886ad3b238c359ed847c2f16d7e616e` |
| [cowra_osm_history.xml](../data/raw/reviewed/final_matching_20260910_cowra_osm_history.xml) | [original](https://api.openstreetmap.org/api/0.6/node/8253300980/history) | `1b5853149a117aeefb2f39bde77879e6f251cb7ed017951671c04b97f9253974` |
| [cowra_council_2025.pdf](../data/raw/reviewed/final_matching_20260910_cowra_council_2025.pdf) | [original](https://www.cowracouncil.com.au/files/assets/public/v/1/council/governance-and-transparency/council-plans-and-reports/delivery-program-2022-2023-to-2025-2026-2025-six-month-review-to-30-june-2025.pdf) | `99029ef90b9b6a96b3f165caed5ad7660570efb2ad2a3f0db8e28f6e5bcc83c9` |
| [sovereign_172.html](../data/raw/reviewed/final_matching_20260910_sovereign_172.html) | [original](https://www.sovereignhills.com.au/news/sovereign-place-welcomes-tesla-supercharger-site) | `0ed1c1ae1699002ec0bbbf679f41cee9ed9e54ff33119980724bf8779ce9b388` |
| [broadway_7_venue.html](../data/raw/reviewed/final_matching_20260910_broadway_7_venue.html) | [original](https://www.broadwaysydney.com.au/visit/centre-info-and-services) | `d2f172332e35952d39f73ca782d8a71afe94e4c436b20f55e0b35f3b8ecb4224` |
| [broadway_7_parking.html](../data/raw/reviewed/final_matching_20260910_broadway_7_parking.html) | [original](https://www.broadwaysydney.com.au/visit/parking) | `2c50c7ed2e37a39e1b0ed50982d331fcc9b2f14fc414a6f8e1c800647628b6d7` |
| [hollydene_483.html](../data/raw/reviewed/final_matching_20260910_hollydene_483.html) | [original](https://www.winecountry.com.au/hollydene-estate) | `8d898173821d7b92d534bc75bc66c497e6d08f4012edaae8bff23463623283fe` |
| [heatherbrae_344.html](../data/raw/reviewed/final_matching_20260910_heatherbrae_344.html) | [original](https://www.heatherbraespies.com.au/heatherbrae/) | `264d5688d10a87bdf2a88f1b038e6c7353ee2acc733484addfcf2461bbed160f` |
| [bega_422_location.html](../data/raw/reviewed/final_matching_20260910_bega_422_location.html) | [original](https://obh.org.au/Hospital/location.htm) | `84d57011e8723f1864b397fecdab298e5fba81ba63c5acb6136733bc8e372a7f` |
| [grove_501.html](../data/raw/reviewed/final_matching_20260910_grove_501.html) | [original](https://grovesquare.com.au/) | `75ad3c65309f589d2216b7c5513d393ed7e830c9a1a3c120540ed3062173b636` |
| [goulburn_1309_brochure.pdf](../data/raw/reviewed/final_matching_20260910_goulburn_1309_brochure.pdf) | [original](https://www.goulburnaustralia.com.au/wp-content/uploads/2025/03/EV-Brochure_DL-20250327.pdf) | `9a706757c50a6ec0553d9b2ff5f1bcbadab295fbfe21cb07986236a3d6e81175` |

Related packaged evidence: [five-case evidence improvement](matching_evidence_improvement_20260909.md) and [third-review actions](third_review_actions_20260909.md). The 8 September internal matching review is a historical working note; the current 27-case ledger above is supplied with this submission.
