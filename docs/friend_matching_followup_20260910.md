# Follow-up evidence for three pending OSM associations

Current documentary status is updated in [the 13 September follow-up](matching_followup_20260913.md), including Parkes readable-page support. The dated observations below remain the earlier checkpoint.

Review date: 10 September 2026. This is an AI-assisted review of published
evidence, not independently labelled human ground truth or an accuracy estimate.
It follows the [earlier 27-case review](final_matching_review_20260910.md), whose
CSV and case decisions are retained as the historical checkpoint. No source
coordinates, source records, matching thresholds, accepted associations or
augmentation values are changed by this note.

## Goulburn: an official bridge between the two street addresses

Source row 1309 (`r_86b0088690bec6020cef`) describes Tesla, 20 plugs, at
179-183 Hume Street. Its accepted OSM object is `node/12564147445`, 99.131696 m
away, with Tesla reference 31614 and 20 CCS2 stalls. The earlier unresolved
question was whether that Hume Street source venue was compatible with the
Tesla venue described as 5 Lockyer Street.

The NSW Planning Portal's determined application PAN-473931 / DA/0078/2425
explicitly connects them: its project title names 179-183 Hume Street and a
20-space EV charging car park; the same record identifies the property as
5 Lockyer Street, Lot 1 DP1258737, and records approval on 19 December 2024.
The associated planning statement identifies Tesla, 20 charging spaces, the
southern part of that lot, co-location with the existing KFC and access from
both streets. The lot and proposed layout in its Figure 2/3 were visually
reviewed. These are complete government-hosted HTTP originals, not search
snippets.

| Packaged original | Publisher, locator and SHA-256 |
| --- | --- |
| [Determination record](../data/raw/reviewed/friend_matching_goulburn_determination_20260910.html) | [NSW Planning Portal](https://www.planningportal.nsw.gov.au/daex/determined/179-183-hume-street-goulburn-construction-and-operation-20-space-ev-charging-car-park): project title, Property Address, Lot/DP, reference and determination fields. SHA-256 `6bdbc80971d50d3325c5ff0dbeb70fdfdc17fdf24c051b50093d33ac0e070b4c`. |
| [Planning statement](../data/raw/reviewed/friend_matching_goulburn_planning_20240927.pdf) | [Government-hosted original](https://apps.planningportal.nsw.gov.au/prweb/PRRestService/DocMgmt/v1/PublicDocuments/DATA-WORKATTACH-FILE%20PEC-DPE-EP-WORK%20PAN-473931%2120240927T010446.532%20GMT): file page 6 Figures 2/3 (site and proposed layout); page 7 (lot and dual access); page 9 section 3.1 (Tesla, 20 spaces, KFC co-location); page 11 section 3.2.2 (access). SHA-256 `3e8ddf00631e7b65593ae5df94d1c15bbe374573c65f7657e68d9d924a25dcd4`. |

Each original has an adjacent manifest recording its requested/resolved URL,
GET method, successful HTTP status, UTC retrieval time, byte count and SHA-256.

**Updated review decision: venue supported; exact point and attributes remain
unverified.** The independently published address bridge removes the specific
Hume/Lockyer venue ambiguity. It does not survey the OSM point or establish that
the source's representative point is a particular bay. Development approval
does not itself prove construction completion or operation on a particular
date. Neither the original 175 kW rating nor the OSM connector/access values
are replaced or retrospectively verified by the planning records.

The later [Council tourism brochure, updated 29 August 2025](https://www.goulburnaustralia.com.au/wp-content/uploads/2025/08/EV-Brochure_DL-20250829.pdf),
also read as a complete PDF during this follow-up, lists Chargefox KFC South at
179-183 Hume Street and Tesla at 5 Lockyer Street separately. This distinguishes
operator installations; it does not negate the official common-lot address
bridge. It must not be used to transfer Chargefox's equipment or prices to
Tesla. The brochure remains supplementary investigation material rather than
an applied dataset input. The earlier 2024 brochure is retained unchanged.

## Parkes: stronger venue context, pending direct charger evidence

Source row 1742 (`r_9e59feb5c2b387e92904`) describes four Tesla plugs at
9-17 Short Street. OSM `node/12221169446` is 71.204642 m away and identifies
Tesla reference 34173 with four CCS2 stalls.

The [club's own homepage](../data/raw/reviewed/friend_matching_parkes_club_20260910.html) identifies Parkes
Services Club at 9-17 Short Street. Its [2025 audited financial report](../data/raw/reviewed/friend_matching_parkes_club_2025_financial.pdf),
file page 5, identifies 18-20 Caledonia Street as the club car park. Both were
retrieved as complete originals and are supplied with adjacent manifests; they
connect the source address to the club's parking property, but do not themselves
identify Tesla equipment. A [30 October 2024 ClubTIC article](https://clubtic.com.au/parkes-services-stepping-up-and-cashing-in/)
reports four Tesla chargers being installed in the rear car park. This is
independent trade-press reporting, not a first-party operator or club publication.

| Packaged original | Publisher, locator and SHA-256 |
| --- | --- |
| `friend_matching_parkes_club_20260910.html` | [Club homepage](https://parkesservicesclub.com.au/): club name and footer address. SHA-256 `ebf83d918e1999bf8bd2920b70a99c0a1eeea8ac315ce4be602839cecb307806`. |
| `friend_matching_parkes_club_2025_financial.pdf` | [Club's audited report](https://parkesservicesclub.com.au/wp-content/uploads/2026/05/Signed-2025-Audited-Financial-Report-Parkes-Services-and-Citizens-Club-Co-Operative-Limited.pdf): file page 5 / printed page 3, Disclosure of Core and Non-Core Property table, club-carpark row; visually reviewed. SHA-256 `9d44f17f5653569d3fa8e9e555396b630af88905bd3ee2c5e4f891ddbc0af285`. |

Search-extracted Tesla site text names Parkes Services Club and 20 Caledonia
Street for reference 34173. Its full original was not available in the earlier
review, which returned HTTP 403; this follow-up did not bypass that restriction
or treat extracted search text as an archived operator response. The club's
public website search for Tesla returned an empty result. The 2024 financial
report was an image-only PDF; no claim of complete searchable-text review of
that report is made.

**Decision: retain pending site evidence**, with improved context. A complete
operator response or direct club publication identifying the Tesla installation
would complete the stronger source standard used for this review. The new
material does not establish a wrong association or justify automatic removal.
It is not used to overwrite connector counts, prices, power or access conditions.

## Bega: adjacent-address question remains open

Source row 422 (`r_54984b72f9c24952867a`) describes Chargefox, two plugs and
42 kW at 3 Corkhill Place. Its OSM object `node/12284563526`, 54.895419 m away,
has no address or specific venue name. The [previously archived Old Bega
Hospital location page](../data/raw/reviewed/final_matching_20260910_bega_422_location.html)
identifies number 3 but does not identify a charger.

The [Tarra Motors homepage](https://www.tarramotors.com.au/) independently
identifies the dealership at **1 Corkhill Place**. It was retrieved as a complete
HTTP original, but supplies no site-specific Chargefox assertion in the reviewed
content. A Parliament search result refers to a 42 kW charger at the dealership;
the quoted witness explicitly attributes that information to PlugShare and says
they had not visited. The PDF request returned HTTP 403. Neither a search extract
nor second-hand testimony is treated as verified charging-site evidence.

**Decision: retain pending site evidence.** Number 1 and number 3 are not assumed
equivalent. A provider station record or direct venue confirmation is needed to
establish which property hosts the charger and whether the source address is an
imprecise label. Missing confirmation is not proof that the OSM association is
wrong; the original values and accepted link remain unchanged.

## Effect on the review ledger and sensitivity calculation

Only the Goulburn evidence decision changes. Of the same 27 previously reviewed
links, 15 now have venue support (14 with attributes still unverified and one
with its previously documented connector conflict); 12 remain pending. These
are evidence-review categories, not a measured match-accuracy result.

Actual coverage is unchanged: site augmentation is 245/426 = 57.51%, and site
information excluding identifiers and status is 214/426 = 50.23%. Among the
three OSM-only non-status contributors considered in this targeted follow-up,
two remain pending under the stronger direct-source standard. Conditionally
removing their two contributions would give `(214 - 2) / 426 = 49.77%`. This is
a sensitivity scenario, not an applied exclusion and not a new coverage result.
The historical three-case scenario remains mathematically valid for its stated
assumption but no longer describes the updated evidence-review count.
