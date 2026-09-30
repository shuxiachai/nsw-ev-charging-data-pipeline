# Synthetic DuckDB example

This example uses project-authored fictional data. It is not an extract of NSW charging sites and does not describe live infrastructure. Only DuckDB is required; no raw snapshots, spatial extension or API access are needed.

Run from the repository root after installing dependencies:

```sh
python examples/demo.py
```

The five source records describe four locations. Two source records belong to `L1`, so they count as one location. Three locations are DC. Only `L1` and `L3` have site observations, giving `2/3 = 66.67%` site coverage; the operator website attached to `L2` does not increase site coverage. Regions `R1` and `R2` have two and one DC locations respectively.

Two sources disagree about `L3` connector type. The example retains `CCS1` and `CCS2` as a conflict rather than claiming either is authoritative. Capture dates and source names remain in `attributes.csv`.

Expected key output:

```json
{"source_records": 5, "locations": 4, "dc_locations": 3,
 "site_augmented_dc_locations": 2, "site_coverage": 0.666667}
```

For the full database's SQL examples, see [`sql/analysis_queries.sql`](../sql/analysis_queries.sql) and the [standalone SQL guide](../docs/standalone_sql.md).
