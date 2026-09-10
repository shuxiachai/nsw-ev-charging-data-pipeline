# Run the SQL independently

Use DuckDB **1.5.5**, matching `requirements.txt`. The Python package contains the
DuckDB engine; a separate DuckDB CLI is optional. Run the examples from the
project root. The DDL creates the empty relational schema, constraints, indexes
and views; the Python pipeline populates it with the supplied data.

`sql/schema.sql` and `sql/analysis_queries.sql` start with `INSTALL spatial;`
and `LOAD spatial;`. The first installation downloads the official DuckDB core
extension and therefore requires internet access. Ordinary `INSTALL` reuses an
existing extension for the current DuckDB version/platform and extension
directory; it does not refresh it. `LOAD` is required in each new connection.
No `FORCE INSTALL` is used.

## Create a new, empty database

After installing the Python dependencies, the following PowerShell example
executes the DDL directly, without running the pipeline. Choose a new output
filename; do not execute schema creation against the populated deliverable.

```powershell
@'
from pathlib import Path
import duckdb

database = Path(".runtime/schema_example.duckdb")
extensions = Path(".runtime/duckdb_extensions").resolve()
extensions.mkdir(parents=True, exist_ok=True)
if database.exists():
    raise FileExistsError("Choose a new database filename; this example creates an empty schema.")
with duckdb.connect(str(database), config={"extension_directory": str(extensions)}) as con:
    con.execute(Path("sql/schema.sql").read_text(encoding="utf-8"))
    print(con.execute("SHOW TABLES").fetchall())
'@ | .\.venv\Scripts\python.exe -
```

Alternatively, start a DuckDB **1.5.5** CLI with a new database filename:

```text
duckdb schema_example.duckdb
```

Then execute:

```sql
SET extension_directory = './.runtime/duckdb_extensions';
.read sql/schema.sql
SHOW TABLES;
```

`.read` is a DuckDB CLI command, not a SQL statement for `con.execute()`.
The CLI creates `schema_example.duckdb` in the current project root; use a
different new filename if it already exists. The Python example places its
example database under `.runtime` instead.

## Read the supplied spatial database

The following opens the completed deliverable **read-only** and prints stored
point geometries. It does not rebuild or change the database. The extension
directory can still receive an installation if this is the first online use.

```powershell
@'
from pathlib import Path
import duckdb

extensions = Path(".runtime/duckdb_extensions").resolve()
extensions.mkdir(parents=True, exist_ok=True)
with duckdb.connect("data/processed/ev_chargers.duckdb", read_only=True,
                    config={"extension_directory": str(extensions)}) as con:
    con.execute("INSTALL spatial; LOAD spatial;")
    print(con.execute("""
        SELECT location_id, address, sa4_code, ST_AsText(geometry) AS point_wkt
        FROM location ORDER BY location_id LIMIT 5
    """).fetchall())
'@ | .\.venv\Scripts\python.exe -
```

CLI equivalent:

```text
duckdb -readonly data/processed/ev_chargers.duckdb
```

```sql
SET extension_directory = './.runtime/duckdb_extensions';
INSTALL spatial;
LOAD spatial;
SELECT location_id, address, sa4_code, ST_AsText(geometry) AS point_wkt
FROM location ORDER BY location_id LIMIT 5;
.read sql/analysis_queries.sql
```

These examples display `location.sa4_code`, which describes the stored point.
Use `regional_analysis_locations` for SA4 statistics that incorporate the eight
regional reviews; the example analysis SQL demonstrates that distinct view.

## Extension directories and offline execution

The pipeline stores its spatial binary under `.runtime/duckdb_extensions` and
sets `extension_directory` explicitly. An ordinary DuckDB connection instead
uses its own default extension directory unless instructed otherwise. Installing
through the pipeline therefore does not automatically prepare an unrelated
default CLI connection. The examples above deliberately use the same project
directory.

The extension must match DuckDB's version and operating-system architecture.
The submission omits binary caches; another platform needs its own first online
installation. After installation, the same SQL and extension directory work
offline. The pipeline's `all --offline` / `build` checks `LOAD spatial` before
executing the DDL and fails with an installation instruction if the cache is
missing. Its cached path does not download an extension. A standalone SQL first
run with no installed spatial extension cannot run offline.

The historical installation baseline is described, with its original version
and scope, in [fresh_environment_20260910.md](fresh_environment_20260910.md).
Current code and input fingerprints are recorded in
`outputs/test_evidence.json` and `outputs/reproducibility.json`; the final ZIP's
independent extraction verification is supplied beside it as
`submission/package_verification.json`.
