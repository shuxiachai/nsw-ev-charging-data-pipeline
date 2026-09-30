# Snapshot preflight and restoration

The repository keeps provenance manifests (`*.meta.json`) beside every raw input. Run the preflight before a local build:

```powershell
python scripts/preflight.py
```

It reports every missing body and every size or SHA-256 mismatch. It does not require the generated DuckDB database, so a fresh checkout can pass after raw data are restored. Use `python scripts/preflight.py --require-db` only when a completed build database is also required.

To restore missing raw bodies from a local archive, provide the archive checksum yourself:

```powershell
python scripts/restore_snapshot.py --archive path/to/snapshot.zip --sha256 <sha256>
```

With no arguments, the tool reads `docs/releases/v0.1.1.json`, downloads the pinned public release into `.runtime`, verifies its checksum, and restores missing raw bodies.

The restore is deliberately narrow: it accepts no unsafe, duplicate, or symlink ZIP members; it validates every required body against the current tracked manifest before writing anything; it never replaces existing data, manifests, source code, generated CSVs, or the database. A corrupt existing raw body is an error and must be repaired deliberately rather than overwritten by this tool.
