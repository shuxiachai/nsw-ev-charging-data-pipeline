# Changelog

## 0.1.2 — 2026-09-30

- Isolated concurrent download temporaries and keyed verified cache entries by SHA-256.
- Added descriptor validation, bounded network operations, clear transport diagnostics and verified-cache reuse.
- Prevented public packaging of raw bodies without matching provenance manifests.
- Bound release approval to fresh full-suite collection/execution evidence, rejecting deselection, skipped tests and inconsistent artifacts.
- Added targeted adversarial tests for concurrent, interrupted, malformed and stale-evidence cases.

## 0.1.1 — 2026-09-30

- Corrected the snapshot preflight test's simulated project root, exposed by GitHub runners using temporary directories outside the repository.
- Added a relocated-project CLI regression; production preflight behavior and data observations are unchanged.
- Updated the package version and pinned release descriptor.

## 0.1.0 — 2026-09-30

- Added MIT licensing for original software, publisher notices and contribution guidance.
- Added editable Python package metadata and the `nsw-ev-pipeline` command.
- Added source preflight and checksum-verified snapshot restoration tools.
- Added Windows and Linux automated regression checks.
- Added a small synthetic DuckDB example demonstrating records, locations, site coverage and source conflicts.
- Introduced versioned, canonical augmentation IDs using named fields and verified source identity. Augmentation IDs change once from the coursework baseline; location and record identity rules remain unchanged.
- Standardized CSV record separators and generated JSON report newlines to LF and reported coastal distances to six decimal metres after full-precision eligibility checks.
- Added a versioned public code/data release and documented clean-checkout reproduction evidence.

The original coursework archive and its September 2026 results remain a separately identified historical snapshot. Data completeness metrics are not matching-accuracy measures.
