# Contributing

Use Python 3.12 and an editable checkout. Install the exact environment with `python -m pip install -r requirements.txt`, then `python -m pip install -e . --no-deps`.

## Changes and review

1. Open an issue or describe the concrete problem in a pull request.
2. Keep code changes focused and add regression tests for changed behavior.
3. Run the fast tests used by `.github/workflows/tests.yml`.
4. For processing changes, restore the pinned snapshot, build the database and run `python scripts/verify_project.py`.
5. Explain changed results, assumptions and validation evidence in the pull request.

Source bytes and their manifests form a versioned snapshot. Stage updated observations separately; review original evidence and guarded record identities before changing source configuration. Updating a checksum alone is not evidence approval. Do not loosen matching thresholds to achieve coverage targets.

Preserve source observations, publisher attribution, AI acknowledgements and the original group credits. Label synthetic examples clearly. Distinguish tests of internal consistency from independent verification of charger facts.

The submitted coursework archive is a historical baseline. New processing changes belong in a new version and release; they should not replace previously submitted files. See [coursework provenance](docs/coursework/README.md) and [third-party notices](THIRD_PARTY_NOTICES.md).
