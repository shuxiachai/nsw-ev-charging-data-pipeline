# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to generate or revise this file.
# AI-generated or AI-revised material is included in this file.
"""Published output files have platform-independent record separators."""
from pathlib import Path

import pytest


@pytest.mark.parametrize("directory", ["data/processed", "outputs"])
def test_exported_csv_headers_have_lf_record_separator(directory):
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / directory).glob("*.csv"))
    assert paths, "Build the database before checking exported CSVs"
    for path in paths:
        with path.open("rb") as handle:
            header = handle.readline()
        assert header.endswith(b"\n")
        assert not header.endswith(b"\r\n"), path.name
