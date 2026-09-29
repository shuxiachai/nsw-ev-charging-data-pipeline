# Pipeline architecture

The command-line entry point is [`ev_pipeline/__main__.py`](../ev_pipeline/__main__.py). Acquisition verifies source snapshots; [`pipeline.py`](../ev_pipeline/pipeline.py) coordinates processing, exports and DuckDB validation.

| Stage | Main modules | Responsibility |
| --- | --- | --- |
| Acquire and freeze | `acquire.py`, `config/` | Retrieve sources and verify URLs, manifests and pinned bytes |
| Clean and identify | `clean.py`, `identity.py`, `source_quality.py` | Parse fields, preserve raw records, form location identities and flag quality issues |
| Review coordinates and regions | `resolve.py`, `reviewed.py`, `regional.py` | Apply guarded corrections and distinguish point-derived SA4 from reviewed regional membership |
| Match and enrich | `augment.py`, `osm.py`, `jolt.py`, `ampol.py`, `matching_review.py` | Evaluate candidates, reject conflicts and reuse, and retain provider-attributed observations |
| Check scope and operator evidence | `augmentation_semantics.py`, `coverage.py`, `operator_review.py` | Distinguish operator information from site enrichment and validate coverage |
| Store and validate | `pipeline.py`, `sql/schema.sql` | Create constrained tables, spatial views, audit outputs and integrity checks |
| Reproduce | `evidence.py`, `scripts/check_reproducibility.py`, `scripts/verify_project.py` | Bind evidence to source/input fingerprints and compare logical tables, CSVs and schema after an offline rebuild |

## Main entities

`charger_record` is one retained source observation. `location` is the project's operator/address/coordinate identity. Their separation preserves observations without counting overlapping records as additional places.

Provider-specific site and match tables retain their own identifiers. `augmentation` stores attributed observations rather than collapsing conflicting values into one authoritative field. Shared operator, region and snapshot entities support consistency and provenance.

Reviewed resolution, identity, match and region tables record evidence-bound exceptions. Changes to source bytes or guarded source values require a new review; replacing a manifest hash alone does not approve new data. See the [full schema](schema.md) and [design rationale](design.md).

## Geographic interpretation

TfNSW source coordinates are interpreted as WGS84 because the metadata does not declare a CRS. Spatial processing transforms points for ABS boundary matching and uses projected distances for candidate search. Stored geometries use EPSG:4326.

Eight disputed charger points remain in the coursework baseline. Official locality polygons support reviewed SA4 membership, but do not establish exact charger coordinates. `regional_analysis_locations` supports regional counts without exposing those point geometries; `analysis_ready_locations` excludes the disputed points.

## Reproduction boundary

Reproduction compares logical database contents, CSV exports, persisted schema and deterministic validation results. Physical database bytes and timestamps are not equality targets. All frozen sources, dependencies and the DuckDB spatial extension must be available for an offline run. Fresh live downloads are new source observations and are not guaranteed to reproduce the coursework snapshot.
