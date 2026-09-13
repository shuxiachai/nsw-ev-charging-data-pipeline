# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Validate source counts before DuckDB can silently round numeric values."""
import json

import duckdb
import pandas as pd
import pytest

from ev_pipeline import augment


@pytest.mark.parametrize("value", [0, 1, 2.0, 2_147_483_647, None])
def test_count_preserves_nonnegative_whole_observations_and_missing(value):
    result = augment.nonnegative_count(value, context="fixture")
    assert result == value
    assert result is None or type(result) is int


@pytest.mark.parametrize("value", [1.5, -0.1, -1, True, False, "2", "", float("nan"),
                                    float("inf"), float("-inf"), 2_147_483_648, 10 ** 400])
def test_invalid_counts_are_rejected_before_integer_conversion(value):
    with pytest.raises(ValueError, match="Invalid nonnegative integer count.*fixture"):
        augment.nonnegative_count(value, context="fixture")


def raw_fixture(tmp_path, monkeypatch, quantity, points):
    monkeypatch.setattr(augment, "RAW", tmp_path)
    reference = {name: [] for name in ["Operators", "ConnectionTypes", "DataProviders", "UsageTypes", "StatusTypes"]}
    (tmp_path / "ocm_reference.json").write_text(json.dumps(reference), encoding="utf-8")
    (tmp_path / "ocm_au_tree.json").write_text(json.dumps({"tree": [{"type": "blob", "path": "OCM-1.json"}]}), encoding="utf-8")
    poi = {"ID": 1, "AddressInfo": {"CountryID": 18, "Latitude": -33.86, "Longitude": 151.2},
           "Connections": [{"ID": 2, "CurrentTypeID": 30, "Quantity": quantity}], "NumberOfPoints": points}
    (tmp_path / "ocm").mkdir()
    (tmp_path / "ocm/OCM-1.json").write_text(json.dumps(poi), encoding="utf-8")


@pytest.mark.parametrize("field", ["Quantity", "NumberOfPoints"])
def test_external_loader_rejects_fraction_with_source_identity(tmp_path, monkeypatch, field):
    raw_fixture(tmp_path, monkeypatch, 1.5 if field == "Quantity" else 1,
                1.5 if field == "NumberOfPoints" else 1)
    with pytest.raises(ValueError, match=rf"OCM-1.json, OCM 1.*{field}"):
        augment.external_data()


@pytest.mark.parametrize("quantity,points", [(0, None), (None, 0), (2.0, 3)])
def test_external_loader_preserves_zero_null_and_integral_counts(tmp_path, monkeypatch, quantity, points):
    raw_fixture(tmp_path, monkeypatch, quantity, points)
    sites, connectors, _ = augment.external_data()
    assert connectors.iloc[0].quantity == quantity if quantity is not None else pd.isna(connectors.iloc[0].quantity)
    assert sites.iloc[0].number_of_points == points if points is not None else pd.isna(sites.iloc[0].number_of_points)


def test_sql_check_is_insufficient_to_detect_fractional_count():
    with duckdb.connect(":memory:") as con:
        con.execute("CREATE TABLE counts(quantity INTEGER CHECK(quantity >= 0))")
        con.register("source_counts", pd.DataFrame({"quantity": [1.5]}))
        con.execute("INSERT INTO counts SELECT * FROM source_counts")
        assert con.execute("SELECT quantity FROM counts").fetchone()[0] == 2
    # Therefore the source loader must reject the value, not rely on SQL CHECK.
    with pytest.raises(ValueError):
        augment.nonnegative_count(1.5, context="Quantity before INSERT")
