"""Configuration warnings use the same complete expression as power values."""
import pandas as pd
import pytest

from ev_pipeline import clean


def clean_rating(monkeypatch, rating, plugs):
    row = dict.fromkeys(clean.FIELDS, "")
    row.update(OBJECTID="configuration-test", Station_address="10 Test St Sydney NSW 2000",
               Operator="Evie", Number_of_plugs=str(plugs), Charger_Type="DC", Charger_rating=rating,
               Latitude="-33.86", Longitude="151.20", PCODE="2000")
    monkeypatch.setattr(clean.pd, "read_csv", lambda *args, **kwargs: pd.DataFrame([row]))
    _, records, issues, _ = clean.load_clean()
    warnings = [issue for issue in issues if issue["code"] == "configuration_count_disagreement"]
    return records.iloc[0], warnings


@pytest.mark.parametrize("rating,plugs,configured", [
    ("2x50 kW + 22 kW", 2, 3),
    ("22 kW + 2x50 kW", 2, 3),
    ("2 × 50 kW", 3, 2),
    ("2 × 50 kW + 22 kW", 4, 3),
    ("2X350KW & 6x175kW", 4, 8),
    ("２ｘ５０ｋＷ ＋ ２２ｋＷ", 2, 3),
])
def test_supported_configuration_disagreements_are_counted_completely(monkeypatch, rating, plugs, configured):
    record, warnings = clean_rating(monkeypatch, rating, plugs)
    assert len(warnings) == 1
    assert f"Rating configuration count={configured}, Number_of_plugs={plugs};" in warnings[0]["detail"]
    assert record.number_of_plugs == plugs  # A warning never substitutes a count.
    assert record.power_raw == clean.text(rating)
    assert pd.notna(record.power_min_kw) and pd.notna(record.power_max_kw)


@pytest.mark.parametrize("rating,plugs", [
    ("2x50 kW + 22 kW", 3),
    ("22 kW + 2 × 50 kW", 3),
    ("2 × 50 kW", 2),
    ("2x350kW & 6x175kW", 8),
    ("2x50 kW / 22 kW", 3),
    ("2x50 kW;22 kW", 3),
    ("22 kW", 4),
    ("22", 4),
    ("50 kW + 22 kW", 4),
])
def test_matching_or_unstated_configuration_counts_do_not_create_warnings(monkeypatch, rating, plugs):
    record, warnings = clean_rating(monkeypatch, rating, plugs)
    assert not warnings
    assert pd.notna(record.power_min_kw) and record.number_of_plugs == plugs


@pytest.mark.parametrize("rating", [
    "2x50 kW + 22", "2x50 kW (estimated)", "2x50 kW + 1.5 MW",
    "2x-50 kW", "0x50 kW", "2x50-150 kW", "2x50 kW + unknown",
])
def test_unknown_or_invalid_expression_does_not_generate_a_partial_count(monkeypatch, rating):
    record, warnings = clean_rating(monkeypatch, rating, 3)
    assert not warnings
    assert record.power_kind in {"unknown", "invalid"}
    assert pd.isna(record.power_min_kw) and pd.isna(record.power_max_kw)


def test_missing_plug_count_remains_unknown_even_with_a_valid_configuration(monkeypatch):
    record, warnings = clean_rating(monkeypatch, "2x50 kW + 22 kW", "")
    assert not warnings and pd.isna(record.number_of_plugs)
    assert (record.power_min_kw, record.power_max_kw) == (22.0, 50.0)
