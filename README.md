# COMP5339 2026 S2 - Assignment 1 code and database

Reproducible NSW EV charger acquisition, cleaning, SA4 integration, web-data
augmentation and DuckDB storage. This package contains the **code deliverable**;
the six-page project report, title-page identities/team contributions, and genAI
usage report are separate submission items and are not supplied here.
This code/database ZIP runs and can be marked from its own contents; no
repository access is needed.

All Python and SQL source files carry a `USYD CODE CITATION ACKNOWLEDGEMENT`.
For 53 files, dated implementation/review records or later Git revisions
document file-specific Codex-assisted changes, including work before the
first collaboration commit. Three initial-draft files (__init__.py,
__main__.py and evidence.py) instead disclose the group's confirmation
that the initial draft used AI generation or substantive revision; their
file-specific tool attribution was not retained. They are not separately
declared AI-free. The separate AI usage report records the tools, purposes,
extent of use and representative prompts, including other members' actual
tool use. File-level notices do not replace that submission item.

For the current result, start with the validated snapshot below and
[the latest review fixes](docs/friend_review_actions_20260910.md). The main
technical references are [design](docs/design.md), [schema](docs/schema.md) and
[sources](docs/sources.md). Earlier dated reviews document historical checkpoints;
their old counts do not describe the current database.

## Group collaboration on GitHub (not needed to run or mark this ZIP)

The currently retained ZIP is a working snapshot. Rebuild it from the final
validated `main` revision at final submission. This section only describes how
the group worked.

The private repository is [shuxiachai/comp5339-assignment1-2026s2](https://github.com/shuxiachai/comp5339-assignment1-2026s2).
Start with the [pipeline](ev_pipeline/pipeline.py), [cleaning](ev_pipeline/clean.py),
[matching](ev_pipeline/augment.py), [database DDL](sql/schema.sql), and the validated
snapshot below. The repository includes source code, tests, technical notes,
small frozen originals with all manifests, processed CSVs and result summaries.

The [10 September data snapshot Release](https://github.com/shuxiachai/comp5339-assignment1-2026s2/releases/tag/review-fixes-2026-09-10)
contains `COMP5339_A1_Code_and_Database.zip` and `SHA256.txt`. The ZIP includes the
complete frozen inputs and DuckDB database. Large PDF/ZIP originals, the database,
local environments and review scratch files are excluded from Git history.
Repository collaborators can access this private Release after accepting an
invitation. The release is a reviewed working baseline, not a final submission
declaration; the report and group details remain separate deliverables.

The Release preserves the 10 September code and data snapshot; `main` includes
later boundary-case fixes. No new submission ZIP is generated for each code edit.
Download that ZIP and `SHA256.txt`, check the checksum, and extract it to recover
the frozen data. On Windows, `Get-FileHash -Algorithm SHA256 <zip-path>` computes
the checksum.
Links to PDF originals refer to files included in the snapshot.

To work in a Git clone, use `git clone https://github.com/shuxiachai/comp5339-assignment1-2026s2.git`.
Copy the extracted snapshot's `data/` directory into
the clone, then run Quick start from the clone. This restores the large frozen
originals and database without replacing the checked-out code. A clone alone
does not include all evidence required for an offline build. Match the data
package to the code revision; later changes to pinned inputs need their matching
reviewed data snapshot.

Use a short feature branch for changes and open a pull request for another group
member to review. Describe the change, its reason and relevant validation.
Check `git status` before committing. Keep credentials, environments, generated
database files and full submission ZIPs in their designated local/release locations.

## Quick start

Tested on Windows with Python 3.12. A clean virtual environment is required.
Run commands from the extracted project root (the folder containing this README).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ev_pipeline all
.\.venv\Scripts\python.exe scripts/verify_project.py
```

If `py` is unavailable, use the full path to a Python 3.12 executable for the
first command. Activation is optional; using the explicit interpreter avoids
PowerShell execution-policy changes. No API keys are required. Initial setup
needs internet access for Python packages and the official DuckDB spatial
extension. `all` verifies the supplied raw cache and only downloads missing files.

The reviewed identity evidence in `data/raw/reviewed/identity_*` consists of frozen
snapshots. The Exploren location details came from the public map's read-only
POST endpoint; the original request method, action and location ID remain in
each manifest. These responses are not recreated by the generic GET downloader.
Identity processing verifies the pinned hashes and parses the archived map
points, venue names and addresses. A missing or altered evidence file stops the
build; restore the supplied snapshot or conduct and document a new review.
The later operator equipment descriptions support venue identity only and do
not replace the original source coordinates, plug counts or ratings.
The Campbelltown and Mount Annan reviews additionally use four complete GET
originals from council, venue, Shell and supplier publications. They are also
checked against their pinned bytes; they are not silently refreshed by the
identity stage. Archived Balgowlah/UOW counterevidence explains decisions to
leave those identities unresolved.
The later Cowell Street and Parraween Street identity reviews use four complete
council originals, each pinned and semantically checked. They merge duplicate
site observations across source programmes while preserving every source row,
its coordinates and equipment values; see [the council evidence](docs/identity_evie_council_20260910.md).

Linux/macOS equivalent:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ev_pipeline all
.venv/bin/python scripts/verify_project.py
```

Only Windows execution has been verified. Other platforms install their own
DuckDB extension binary on the initial online run.

For a standalone DuckDB connection, follow [the SQL setup and spatial-query guide](docs/standalone_sql.md).
`sql/schema.sql` creates the empty schema and installs/loads spatial when needed;
the first installation needs internet access. Python's project extension cache
and a default DuckDB CLI cache are separate unless explicitly configured alike.
The guide also opens the delivered database read-only without rebuilding it.

## Commands

| Command, after the Python interpreter | Purpose |
| --- | --- |
| `-m ev_pipeline acquire` | Download missing raw inputs and verify every cached file's SHA-256 and URL |
| `-m ev_pipeline all` | Acquire/verify, clean, integrate, augment, build and validate; installs spatial if necessary |
| `-m ev_pipeline all --offline` | Full processing using existing cache and installed spatial extension, no downloads |
| `-m ev_pipeline build` | Same cached rebuild, always offline |
| `-m ev_pipeline validate` | Independently query database integrity and augmentation coverage |
| `-m pytest -q` | Unit, adversarial matching, cache and actual database integration tests; run `-m ev_pipeline all` once first, which populates the project extension directory `.runtime/duckdb_extensions` that the submission package excludes |
| `scripts/check_reproducibility.py` | Rebuild offline and compare table contents, persisted schema, CSVs and the complete validation report |
| `scripts/verify_project.py` | Run tests, offline reproducibility and database checks; bind evidence to current code and input manifests |
| `scripts/package_submission.py` | Build the code/database ZIP after validation and reproducibility gates pass |
| `scripts/stage_source_candidates.py --label 2026-09-09-a` | Download dynamic source candidates into a new review directory; leave the active project inputs and outputs unchanged |

The final database is replaced only after transaction, integrity checks and all
required CSV/JSON exports succeed.
A failed build retains the previously completed database; read the traceback and
`outputs/failed_validation.json` if generated. Do not run concurrent builds into
the same output directory. Export files can be partly written if a build fails;
rerun the build and verification before using or packaging those outputs.

## Project structure

```text
ev_pipeline/       acquisition, cleaning, spatial join, augmentation, storage, CLI
config/            operator aliases and evidence-bound reviewed corrections
sql/schema.sql     executable DuckDB DDL (tables, constraints, indexes, views)
sql/analysis_queries.sql   example verification and coverage queries
scripts/           reproducibility and ZIP packaging tools
tests/             meaningful correctness and integration tests
docs/              design decisions, source attribution and schema diagram
data/raw/          original inputs and per-file provenance/hash manifests
data/processed/    final DuckDB plus derived CSV exports
outputs/           quality issues, all match decisions, review samples, validation
submission/        generated ZIP and SHA256.txt (repository only, not in the ZIP)
requirements.txt   exact versions from the tested isolated environment
```

`.venv`, `.runtime`, scratch files and bytecode are excluded from the ZIP. Spatial
extension binaries are installed under `.runtime/duckdb_extensions` so they do
not change another project's DuckDB configuration. The input PDF/rubric are not
duplicated in the code submission.

## Data sources and automated retrieval

1. **Transport for NSW:** CKAN catalogue queried in Python; the resource matching
   the December 2025 CSV filename is selected and downloaded. The actual supplied
   resource is `ev_20251216.csv`. Its catalogue description says **Effective 20
   April 2026**, and the accompanying documentation is April 2026 v2.1. These
   conflicting version signals are retained; the filename is not proof that all
   contents describe December 2025. The v2.1 changelog says "Revised data format"
   but does not establish the records' observation period. Acceptance as the
   assignment's December 2025 input still requires course confirmation. No newer
   file is silently substituted.
2. **ABS:** parse the official Edition 4 download page for the 2026 SA4 shapefile
   ZIP, download it in Python, and read the ZIP directly with GeoPandas. Select
   NSW by `STE_CODE26='1'`. The two nonspatial special categories have no polygons
   and are not used for point assignment.
3. **Open Charge Map:** use the publisher's public GitHub export, pinned to commit
   `8e3bedca48ca94807d96b2f5e7ee02cffe63ae54` (2026-04-22). The Git Tree API avoids
   the 1,000-file limit of the Contents API. All 1,298 Australian POI files and the
   matching lookup table are cached. Only station/operator/connector fields are
   used; user comments and contributor profiles are not analysis fields.
4. **OpenStreetMap:** one Overpass request for `amenity=charging_station` in a
   bounding box enclosing NSW; the box also includes neighbouring territory.
   Only matches to the NSW source locations contribute to results. Query,
   retrieval timestamp, raw JSON and OSM object links are retained. The cached
   snapshot includes 686 objects; absence of a tag is not treated as a default.
5. **JOLT:** parse the JSON object embedded in the operator's public Australian
   charger-map HTML using Python's JSON decoder. No JavaScript execution, private
   API, authentication or embedded third-party key is used. Matched operator
   station codes, network status and EVSE status are separate site attributes.
   Status values come from the map captured on 6 September 2026; they are not
   live availability or an observation of December 2025. The archived operator
   map script supports the field meanings. See [JOLT evidence](docs/jolt_details_evidence_20260909.md).
6. **Reviewed source corrections:** retain the NRMA website and its embedded public
   KML map examined when investigating source conflicts. The KML title contains
   'Nov 2022' and some pins are town-level or inconsistent with street evidence.
   Seven reviewed corrections require archived council/operator address or venue
   evidence and original source guards. Five use OSM points corroborated by NRMA
   KML; Wollongong uses an OCM point and NRMA KML. Walcha uses an OCM site point
   with an official street map and a separately labelled police/road landmark
   check. It is an approximate street site, not a surveyed bay or two charging
   points in agreement. All coordinates are parsed from pinned originals. See
   [reviewed resolution evidence](docs/reviewed_resolution_design.md).
7. **Regional membership review:** query NSW Spatial Services for the complete
   official locality polygons for Braidwood, Walgett, Moree, Dorrigo, Inverell,
   Gilgandra, Narellan and New Italy.
   Parse every polygon ring in the stated GDA2020 CRS and require the entire
   locality to lie in exactly one ABS 2026 SA4. Separate government/operator/venue
   originals support the eight source-to-locality identities. This establishes
   regional membership without replacing uncertain charger coordinates. See
   [initial regional evidence](docs/regional_sa4_review_20260909.md) and
   [the two additional confirmations](docs/third_review_actions_20260909.md), plus
   [the New Italy geographic conflict](docs/friend_review_actions_20260910.md).
8. **Ampol individual station pages:** programmatically download and decode the
   per-location `currentLocation.services.EVCharging` data from official pages.
   Explicit CCS/CHAdeMO labels become dated connector observations. The 15
   archived pages include one without an EVCharging category; absence does not
   prove no charger exists. The same matching thresholds and reuse rejection
   apply. No website bay labels, powers, general business hours or status are
   converted to physical charger counts, ratings or availability. Source pins
   are in `config/ampol_sources.json`; cached acquisition verifies them and can
   restore missing bodies only against their original manifests and hashes.

Every download has a `.meta.json` file containing its URL, UTC retrieval time,
SHA-256, byte count and HTTP metadata. Existing raw inputs are immutable by
default. A URL/hash mismatch fails explicitly. If only a manifest remains,
downloading the missing file must restore the same recorded bytes. Reviewed
evidence is also pinned to the hashes in its configuration. Downloads use timeouts, retry and
backoff for transient HTTP errors; OCM uses at most six download workers. An
optional `GITHUB_TOKEN` environment variable is supported only for authenticated
GitHub rate limits; it is never stored in URLs or manifests.

**Reproducibility:** distribute the included raw snapshots with the code. A
cached rebuild is deterministic. Official CSV/ABS/OSM/JOLT URLs can change their
contents on later fresh retrievals; a future fresh download is a new observation,
not a promise of historical reproduction. To inspect newer observations without
changing the frozen inputs, run:

```powershell
.\.venv\Scripts\python.exe scripts/stage_source_candidates.py --label 2026-09-09-a
```

Choose a new label for each attempt (1-64 letters, digits, underscores or hyphens,
starting with a letter or digit; reserved filesystem names are rejected). The
script refuses to overwrite an existing candidate directory. It downloads the
TfNSW catalogue, a selected CSV and metadata PDF; the ABS page and boundary ZIP;
OSM, JOLT, and the NRMA page and published KML. By default, CSV selection excludes
resources explicitly labelled historical or no longer updated by the publisher
in their names/descriptions, then prefers an explicitly current resource over an
unmarked one. It never ranks filenames, modification dates or CKAN `active`
status to infer currency. The supplied catalogue has one unmarked CSV and a
second explicitly historical CSV, so the former is selected. Zero or multiple
resources at the preferred priority fail explicitly. OCM remains at the fixed
commit above. The candidate metadata PDF follows the same label priority and
also rejects a missing or ambiguous selection. Candidate CSVs use the
neutral filename `tfnsw_chargers.csv`; the selected publisher URL and resource
details are retained in the report.

To select an exact catalogue CSV resource, add its published ID:

```powershell
.\.venv\Scripts\python.exe scripts/stage_source_candidates.py --label 2026-09-09-explicit --tfnsw-resource-id 7bbb6461-e52d-4fe7-ace4-a15c30198de0
```

An absent, duplicated or non-CSV ID fails without falling back to another
resource. Explicit selection can retain a historical CSV for comparison; its
official description, historical label and selection reason remain in the
report. That selection is not a current or assignment-approved replacement, and
the separately downloaded catalogue PDF is contextual rather than proof of the
historical CSV's documentation version. This option affects candidate staging
only; the normal pipeline's December 2025 resource selection remains unchanged.

Read `.runtime/source_candidates/<label>/candidate_report.json`. It records
byte-level changes against current raw files and identifies reviewed corrections
that depend on changed evidence. It also lists matching-exception snapshot
dependencies and the reviewed identity groups to check when the source CSV
changes. Regional-review dependencies are also listed for the staged
CSV, ABS and NRMA sources; changed bytes or source URLs require re-review before
adoption. The locality and venue originals remain separately pinned snapshots.
Even a changed timestamp inside an OSM response
changes its bytes; this does not rewrite the existing review hash. Downloads
retain their own `.meta.json` files. A failed attempt leaves `complete=false`,
the failing stage and any completed downloads for inspection; retry with a new
label. `complete=true` means the candidate downloads finished, not that their
contents satisfy the assignment or are approved for use. This directory is
excluded from the submission ZIP, and staging does not run the pipeline.

To adopt a candidate version:

1. Compare the downloaded originals, catalogue version information and report.
   Recheck any affected reviewed source evidence and original-record guards.
   Unrelated CSV row changes do not alone invalidate an unchanged reviewed row.
2. Use a separate project copy and preserve the old project and all its raw
   files/manifests. In that copy, adopt only the reviewed source/manifest pairs
   together. Confirm that the TfNSW resource still satisfies the assignment's
   version requirement; a different filename is not silently substituted.
3. Update affected review configuration entries only after reviewing the actual
   original evidence and record identity. Record the new review decision and
   date; changing a hash or editing a download manifest alone is not a review.
4. Run `-m ev_pipeline all`, `scripts/verify_project.py`, then
   `scripts/package_submission.py` in that independent version. Existing
   per-record guards and verification gates remain active. There is no automatic
   promotion or option to bypass reviewed evidence checks.

## Cleaning, identity and spatial assumptions

- Keep the complete original row as `charger_record.raw_json`, plus original
  source row and source ID. Missing names/IDs are not invented. Stable content
  hashes supply project identifiers.
- Strip whitespace and normalize documented operator aliases, preserving raw
  spellings. Australian BP Pulse is distinct from UK/US providers. Unrecognized
  names use a deterministic case-folded spelling, consistent with their identity;
  unrelated brands are not merged through fuzzy similarity.
- Normalize `NSW 2500` to `2500`; preserve nulls and flag source/address postcode
  conflicts. Corrections require one OCM candidate with street similarity at
  least 0.85, agreement on postcode (or town when external postcode is missing),
  and a same-operator OSM charging location within 150 m of that candidate.
  Both source and OCM addresses must contain parsed streets; equal generic venue
  labels cannot authorize correction. The OCM address's explicit postal suffix
  must agree with its independent postcode and the source. Full and structured
  OSM fields are also checked against each other before providing corroboration.
  Explicit street-number/type contradictions disqualify correction even when
  the string similarity is high. Different clearly parsed localities require
  verified compatibility; postcode agreement alone cannot authorize a move.
  An OSM corroborator with an explicit contradictory street number/type or
  postcode is also withheld; its absence of address fields remains unknown.
  Automatic correction also requires a known operator: empty, non-networked,
  unknown-operator and business-owner labels cannot establish shared identity.
  Rejected corrections retain their original values and an explicit audit reason.
  Eleven original conflicts meet this rule: ten coordinate corrections and one
  postcode-only correction. Original fields and source IDs are retained in
  `source_resolution`. A second, explicitly reviewed stage corrects seven further
  records using archived venue and coordinate evidence;
  `reviewed_resolution` stores these decisions and evidence roles separately. Seven postal conflicts remain
  flagged. The automatic stage's 14 unsuccessful decisions remain as history;
  they are not the final unresolved count.
- Regional and point certainty are separate. The seven remaining postal conflicts have
  a `reviewed_region` audit: Braidwood 101, Walgett 105, Moree 110, Dorrigo 104 and
  Inverell 110, Gilgandra 105 and Narellan 123. Their entire official localities lie within the respective SA4,
  with zero tolerance and no other intersecting SA4. Their point coordinates,
  postcodes and conflict flags remain unchanged. `regional_analysis_locations`
  combines regional decisions with the ordinary analysis-ready set;
  it exposes no point geometry or coordinates. Use that view for SA4 statistics.
  Gilgandra and Narellan retain their original point-derived SA4 numbers, now
  independently supported at regional precision; their points are not corrected.
- A further geographic conflict concerns Tesla New Italy (source row 1711): both
  source/address postcodes are 2472, but the point lies about 186 km outside the
  official New Italy locality. A guarded venue/council/locality review flags it
  and retains its original coordinate. Its regional answer is SA4 112, while
  the stored point remains in 108. There are now eight disputed points and eight
  regional reviews; the postcode comparison alone is not a geographic check.
  This evidence-bound review does not claim an exhaustive locality audit of all
  other source rows. See [the current review](docs/friend_review_actions_20260910.md).
- Parse individual-plug kW values. `2x350kW & 6x175kW` becomes minimum 175 and
  maximum 350, not a made-up total station power. Bare `AC` is unknown power.
  Count disagreements are flagged because configured units and plugs can differ.
  Power and configuration counts share a whole-expression parser: `x` and `×`
  are equivalent, and `2x50 kW + 22 kW` describes three configuration units.
  Bare ratings without any multiplier do not establish a plug count; unsupported
  expressions do not generate a misleading count from only part of the text.
  `location_power_observations` exposes every available source-record rating,
  including nonrepresentative rows, with source-row and snapshot provenance.
  A rating is parsed only when its whole expression is supported; ambiguous
  thousands separators, ranges or scientific notation remain unknown. Explicit
  nonpositive ratings are invalid. Postal suffix parsing never treats a four-digit
  street number alone as a postcode. Empty mandatory CSVs fail explicitly; empty
  optional OSM results retain their table schema.
- A location is an operator/address/coordinate identity (coordinates rounded to
  six decimals for the identity only). Address case, commas and whitespace are
  normalized for identity, as are optional trailing postcode/country suffixes;
  unit-number slashes, number ranges, floor labels and
  other address content remain significant. Distinct nearby points are not
  merged automatically. Ten individually reviewed same-site groups have explicit
  full-value and membership guards in `config/reviewed_identities.json` and a
  persisted `reviewed_identity` audit. Eleven address-format duplicate pairs
  also share locations, while all original records remain visible. Together
  with Figtree, twenty-one locations have
  multiple source records; do not sum their plug counts without resolving
  record-level conflicts.
- The location representative is the source row with the most populated name,
  postcode and LGA fields, with source row as a stable tie-breaker. It retains
  that row's original fields together, rather than mixing provenance. This
  preserves Balmain's known postcode and LGA after merging its two records.
  Address-conflict flags still aggregate across all records at the location.
  Conflicting known postcodes across records flag the whole location, so removing
  a postal suffix from the identity cannot hide contradictory source evidence.
  The ten reviewed identity groups instead use fixed complete source rows
  575, 1308, 1590, 817, 1562, 1398, 307, 361, 1528 and 1861. Their original coordinates and separate equipment
  observations remain unchanged; a location-level count is not the sum of rows.
- Keep AC, DC and UPCOMING records. The augmentation denominator is the distinct
  locations with an explicit source `DC` record. Upcoming is not silently
  classified as currently operating DC.
- Source coordinate CRS is not explicitly stated in the TfNSW metadata; WGS84
  longitude/latitude is an assumption. Reproject points to ABS GDA2020 for the
  join. Final DuckDB geometries are consistently EPSG:4326.
- Use point/polygon intersection with a uniqueness check. A unique nearest
  polygon within 50 metres is allowed only for an otherwise unmatched point and
  receives a separate method and distance. The actual Clontarf case is about
  1.31 metres outside the mapped coast. Its original coordinate is retained.
  Larger misses and ambiguous boundaries do not receive forced assignments.

## Augmentation methodology and evidence

Candidates are found using a spatial index in Australian Albers (EPSG:3577), then
measured with WGS84 ellipsoidal distance. A match requires the same canonical
operator and no postcode/source-address conflict, plus either:

- distance at most 100 m; or
- distance at most 250 m and address similarity at least 0.65.

Both routes reject explicit conflicts between house-number intervals or street
types on the same named street. One exact Dan Murphy's address-range exception
is supported by an attributed extraction of the official store page, guarded by
reviewed input/evidence hashes and linked in the database and candidate audits.
It bypasses no other match requirement. External connector/station counts are
validated as nullable, finite, non-Boolean, nonnegative integers before SQL
insertion, so fractional quantities cannot be silently rounded.

The score is `0.65 * max(0, 1-distance_m/300) + 0.35 * address_similarity`.
Ordinary matching compares normalized street components, or the first
comma-delimited label when a street cannot be parsed; missing text scores zero.
This label fallback is weaker evidence and is not allowed to justify automatic
coordinate correction.
Two eligible candidates less than 0.10 apart in score are left ambiguous. Reuse
of one external site for different source locations is sent to review, not
automatically accepted. OCM and OSM candidates must have explicit DC evidence.
JOLT candidates come from the DC operator map. Operator, distance, addresses,
score and rejection decisions are exported for inspection. The same thresholds
are used across sources; they were not widened to force the 50% target.

One evidence-bound exclusion withholds source row 216 / OCM192687 because the
Stanley Street bay relationship remains unproven. Its three OCM observations
are removed; the JOLT52 match and operator information remain. The original OCM
record, exclusion audit and source documents are retained. Four other weak
associations gained archived venue evidence; matching thresholds were unchanged.
See [the five matching reviews](docs/matching_evidence_improvement_20260909.md).

Site attributes include DC connector types, access/usage information, opening
hours, JOLT station codes and separately attributed network/EVSE status snapshots.
Prices are retained as source text, not converted
into a universal AUD/kWh value. Different sources are retained as separate
observations, including disagreements. Operator website/phone enrichment uses
exact canonical operator names and is explicitly `scope='operator'`; it does not
verify a location's connectors or eligibility for non-Tesla vehicles.
The unverified Counties Energy assignment at Richmond (one AC location) is
withheld using guarded source evidence, with its candidate value and reason in
`quality_issue`. No operator label or DC coverage is changed by that decision.
See [the operator identity review](docs/operator_identity_review_20260910.md).
OSM matching checks `addr:full` alongside house-number/street fields and explicit
postcodes before ranking candidates. A contradiction in either representation,
including between the two OSM representations, cannot be hidden by the other.
Missing fields remain unknown; all original tags are retained.
OCM embedded postal suffixes and Ampol full/structured address fields receive
the same explicit-conflict checks. Ampol's native `street,postcode,locality,Au`
layout and reversed street-number layout are recognized without treating a
four-digit house number as a postcode. Conflicting candidates stay in the audit
and cannot contribute site attributes.
Recognized generic network-map URLs are also operator-scoped. In particular,
the two exact NRMA network-page paths are not treated as individual site pages;
site-detail URLs, query strings and fragments are not generalized by that rule.

Current validated snapshot:

| Measure | Result |
| --- | ---: |
| Original source rows / retained charger records | 1,958 / 1,958 |
| Distinct project locations | 1,936 |
| Explicit DC source records / distinct DC locations | 433 / 426 |
| Locations assigned by point-in-polygon | 1,935 |
| Separately labelled coastal approximation | 1 |
| Regional-only reviews / still disputed points | 8 / 8 |
| Eligible regional-analysis locations / DC locations | 1,936 / 426 |
| Unresolved point/address conflicts, including the eight reviewed regions | 8 |
| Site-specific augmentation (unique DC locations) | **245 / 426 = 57.51%** |
| At least one non-identifier site attribute, including dated status | 245 / 426 = 57.51% |
| Site information excluding station codes and network/EVSE states | 214 / 426 = 50.23% |
| Station-code-only site enrichment | 0 / 426 = 0% |
| Any augmentation, including operator-level details | 419 / 426 = 98.36% |

Use `outputs/validation.json` as the generated source of truth. This is automated
matching, not ground-truth verification of every station. Of 25 original source
postcode/address conflicts, 11 have automatic corroborated corrections, seven
have archived reviewed corrections, and seven remain
excluded from automatic site matching and `analysis_ready_locations`.
The separately detected New Italy geographic conflict also remains excluded.
`regional_analysis_locations` additionally includes all eight disputed locations
with independently reviewed SA4 membership; it does not imply coordinate repair.
`location.sa4_code` continues to describe its stored point. In `locations.csv`,
use `regional_sa4_code` for reviewed regional analysis, with its method/review
columns; a missing regional value means the record is not yet eligible. The full
426-location DC denominator is retained; regional/point exclusions do not inflate
coverage. In the preceding follow-up the denominator changed from 428 to 426 through the
two evidence-bound Cowell Street and Parraween Street identity merges, preserving
all 433 DC source records. The preceding Campbelltown and Mount Annan review had
changed the earlier 430-location checkpoint to 428. These are successive
location-identity decisions, not removal of unaugmented source records.
Some corrected coordinates come from OCM or OSM: their same-source zero-distance matches are
not independent accuracy measurements. Inspect the resolution evidence and
review CSVs before drawing location-specific conclusions.

Coordinate verification uses null-safe comparisons and checks retained originals
against each location's representative source record. Invalid original coordinate
pairs may legitimately be null; a null cannot hide an unsupported change or the
erasure of valid original coordinates.

The integrated Windows/Python 3.12 verification for this follow-up passed
**1,006 tests and 47 integrity checks**. Results are recorded in
`outputs/test_evidence.json` and `outputs/validation.json`. An offline rebuild
reproduced all 23 base tables, 40 generated CSVs, persisted schema definitions
and the complete deterministic validation report.
Accepted source matches are OCM 131, OSM 149, JOLT 41 and Ampol 13; their overlapping location
sets must not be added together to compute coverage. See the generated evidence
files for the exact project fingerprint.

Station codes are legitimate new site data and are retained. The rubric does not
explicitly exclude identifiers; the non-identifier percentage is shown so the
report can explain the enrichment's content rather than presenting one opaque
coverage number. The non-identifier and station-code-only categories are disjoint. Status snapshots
have short-lived meaning: 57.51% is not a claim that this many locations gained
stable connector, price or access information. Excluding both status and station
codes leaves 214/426 locations (50.23%) with other site information, including two
literal JOLT carpark-hours notes. This narrower measure is only slightly above
50% and remains a coverage measure, not a matching-accuracy estimate.
Of the two priority OSM-only contributors, Bega (source row 422) remains pending;
Parkes (1742) now has venue support from the club property originals and a
clearly identified Tesla official-page text extraction. This is not an archived
HTTP-original or proof of historical equipment values. Withholding only Bega
hypothetically gives 213/426 = 50.00% excluding identifiers/status and
244/426 = 57.28% site scope; no exclusion is applied. Goulburn's planning evidence
also supports its venue without surveying the point or equipment. The same
27-case review cohort now comprises 16 with venue support and 11 pending.
See the [current evidence and extraction limits](docs/matching_followup_20260913.md).
Per-attribute coverage is 211 DC locations for connector types, 103 for cost text,
44 for opening hours and 31 for site websites. The two generic network-map URL
observations are operator-scoped. Rows in `augmentation_attribute_coverage.csv`
overlap and must not be summed.

## Important output files

The archive-specific `submission/package_verification.json`, supplied beside
the Release ZIP, records checks for that dated snapshot. Current code verification
is recorded in `outputs/test_evidence.json` and `outputs/reproducibility.json`.
The earlier [fresh-environment check](docs/fresh_environment_20260910.md)
documents the initial baseline and retains its historical counts and hash.
Fresh environment setup is distinct from a fresh retrieval of historical sources.

- `data/processed/ev_chargers.duckdb`: primary deliverable, with spatial geometry,
  relational constraints, raw-row provenance and all accepted augmentations.
- `data/processed/cleaned_records.csv`: one row per retained source record.
- `data/processed/locations.csv`: one row per project location; point-derived
  `sa4_code` and reviewed `regional_sa4_code` have different stated meanings.
- `data/processed/regional_analysis_locations.csv`: eligible regional assignments
  without point coordinates, including the eight region-only reviews.
- `outputs/regional_sa4_counts.csv`: distinct-location and distinct-DC counts by
  the regional view; excluded records are not removed from the enrichment denominator.
- `outputs/reviewed_region.csv`, `outputs/reviewed_region_evidence.csv`: original
  point SA4, reviewed SA4, entire locality geometry, evidence roles/locators and hashes.
- `data/processed/augmentation.csv`: one source-attributed attribute observation
  per row; not a location count.
- `data/processed/location_power_observations.csv`: every available source-record
  power rating, including other rows at a location whose representative has no rating.
- `outputs/connector_quality_issues.csv`: explicit zero quantities and differing
  OCM site/connector status labels, with the original connector and source IDs.
- `outputs/quality_issues.csv`: missing values, normalization and source conflicts.
- `outputs/source_resolution.csv`: original and corrected values, source IDs,
  address similarity, cross-source distance, and automatic-stage decisions.
- `outputs/reviewed_resolution.csv`: seven further evidence-bound corrections,
  with original/new values, source-file links and recomputed map distances;
  Wagga, Wollongong and Walcha include additional address-support sources and
  locators; `corroborating_role` distinguishes the Walcha mapped landmark.
- `outputs/reviewed_match_exclusion.csv`: the guarded Stanley Street OCM
  exclusion, with source/record IDs, original evidence, decision and review date.
- `outputs/reviewed_identity.csv`: all twenty-one members of ten reviewed groups,
  old/new location IDs and fixed source representatives.
- `outputs/reviewed_identity_evidence.csv`: reviewed group-to-source relationships
  for the three Exploren groups and four later DC venue groups, with element IDs and hashes.
- `outputs/augmentation_composition.csv`: nonoverlapping DC categories showing
  non-identifier site attributes, station-code-only coverage and uncovered sites.
- `outputs/augmentation_attribute_coverage.csv`: distinct DC coverage and source
  observations per attribute and scope; attribute rows overlap.
- `outputs/*matching_candidates.csv`: accepted and rejected candidate evidence.
- `outputs/*matching_review_sample.csv`: weakest accepted matches for review
  (the JOLT file includes all its accepted matches).
- `outputs/unmatched_dc_locations.csv`: source locations without site enrichment.
- `outputs/spatial_exceptions.csv`: separately labelled spatial approximations.
- `outputs/coverage_by_operator.csv`: uneven coverage and operator bias.
- `outputs/cross_source_attribute_differences.csv`: differing source values,
  preserved for review without forcing one value to win.
- `outputs/tests.xml`, `outputs/reproducibility.json`: test and rebuild evidence.

See [database and engineering design](docs/design.md),
[schema diagram](docs/schema.md), and [source attribution](docs/sources.md).

The latest [regional SA4 review](docs/regional_sa4_review_20260909.md),
the preceding [improvement and self-check](docs/improvement_self_check_20260909.md),
the preceding [continuation review decisions](docs/continuation_review_actions_20260909.md),
the preceding [external review decisions](docs/external_review_actions_20260909.md),
the preceding [boundary-case review](docs/edge_case_review_20260909.md) and
[earlier code review](docs/code_review_20260909.md),
[matching changes](docs/matching_changes_20260909.md),
[reviewed corrections](docs/reviewed_resolution_design.md) and
[official source-version investigation](docs/source_version_review_20260908.md)
explain the implemented decisions and their limits. Internal handoff notes,
self-assessed marks and superseded review snapshots are excluded from the ZIP.
