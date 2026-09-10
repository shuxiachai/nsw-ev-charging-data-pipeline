# Fresh-environment installation verification — 10 September 2026

The baseline code submission was extracted into a new review directory. A new
virtual environment was created from Python 3.12.9 with system site packages
disabled. All 22 exact dependencies in `requirements.txt` were installed from
public PyPI using pip's isolated mode with its download cache disabled. Their
installed versions matched the requirements, all distribution paths were inside
the new environment, and `pip check` reported no broken requirements.

Before the first documented `python -m ev_pipeline all` run, the extracted
project had no `.runtime` spatial extension. DuckDB's native `INSTALL spatial`
downloaded the official core extension for DuckDB 1.5.5 / Windows amd64. No old
packages or extension binaries were copied. The extension install metadata
identified core as its repository and extension version `eb1e57c`.

The first build passed all 42 integrity checks present in that baseline. An
independent comparison against the database and exports originally stored in
the ZIP found identical contents for all 21 base tables, persisted schema, 36
generated CSVs and the complete validation report. A subsequent offline rebuild
also passed all four reproducibility comparisons. This verifies the README's
Windows installation procedure using a new environment. It does not claim a
new live download of every historical source or verification on other platforms.

The baseline ZIP SHA-256 was
`4164b8ffafc60f375089e1aa897ffae1b433035bd0f4c6ca717693c02a8e6953`.
The later Ampol integration adds two database tables and associated exports;
its current test and rebuild evidence is recorded with the current project
fingerprint in `outputs/test_evidence.json` and `outputs/reproducibility.json`.
The final delivered ZIP's independent extraction verification is recorded
outside the archive in `submission/package_verification.json`.
