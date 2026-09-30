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

With no arguments, the tool reads `docs/releases/v0.1.2.json`, validates the descriptor and local inputs, then reuses a valid cache or downloads the pinned public release into `.runtime/snapshots/<sha256>/`. Complete valid inputs skip downloading. Every downloaded archive is checksum-verified before use, and only missing raw bodies are restored.

The restore is deliberately narrow: it accepts no unsafe, duplicate, or symlink ZIP members; it validates every required body against the current tracked manifest before writing anything; it never replaces existing data, manifests, source code, generated CSVs, or the database. A corrupt existing raw body is an error and must be repaired deliberately rather than overwritten by this tool.

Each download owns its exclusive temporary file. Different checksums have separate cache directories, even if their archive filenames are identical. Network operations have a 60-second timeout per blocking operation, not a total-transfer deadline. Failed or interrupted downloads preserve existing cache entries. Invalid descriptor fields are rejected before network access.
