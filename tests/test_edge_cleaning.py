"""Boundary inputs that previously produced plausible but incorrect clean values."""
import pandas as pd
import pytest

from ev_pipeline import clean
from ev_pipeline.clean import extract_address_postcode, load_clean, power


@pytest.mark.parametrize("value", [
    "1,250 kW", "1e2 kW", "50-150 kW", "50–150 kW", "2x50 kW + 22",
    "1.5 MW + 22 kW", "charger50kW", "50 kW (estimated)",
])
def test_unsupported_power_formats_never_become_partial_measurements(value):
    assert power(value) == (None, None, "unknown")


@pytest.mark.parametrize("value", ["−22 kW", "−22", "-22 kW", "0x50 kW", "0 kW", "9" * 400])
def test_nonpositive_or_nonfinite_ratings_are_invalid(value):
    assert power(value) == (None, None, "invalid")


@pytest.mark.parametrize("value,expected", [
    ("2x350kW & 6x175kW", (175.0, 350.0, "multiple")),
    ("2x350kW & 2x175kW", (175.0, 350.0, "multiple")),
    ("2 × 50 kW + 22 kW", (22.0, 50.0, "multiple")),
    ("7.4 kW", (7.4, 7.4, "single")),
    ("22", (22.0, 22.0, "single")),
    ("50kw", (50.0, 50.0, "single")),
    ("AC", (None, None, "unknown")),
])
def test_supported_power_formats_retain_individual_plug_ratings(value, expected):
    assert power(value) == expected


@pytest.mark.parametrize("address,expected", [
    ("1250 George St, Sydney", None),
    ("Unit 2000, George St, Sydney", None),
    ("10 Test St, Sydney NSW 2000, Level 2024", None),
    ("2000", None),
    ("10 Test St Sydney NSW 2000", "2000"),
    ("10 Test St, Sydney, 2000", "2000"),
    ("135 Fairfield Rd, Guildford West 2161, NSW", "2161"),
    ("89 Barwan St, Narrabri, NSW 2390, Australia,", "2390"),
    ("185 Carrington Rd Coogee NSW 2034 Commonwealth of Australia", "2034"),
    ("Hill Street, Roseville, New South Wales 2069, Australia", "2069"),
    ("1 Test St, Melbourne VIC 3000", "3000"),
    ("1 Test St, Adelaide SA 5000", "5000"),
    ("1 Test St, Brisbane Queensland 4000", "4000"),
    ("1 Test St, Canberra ACT 2600", "2600"),
    ("1 Test St, Darwin NT 0800", "0800"),
    ("1 Test St, Perth WA 6000", "6000"),
    ("1 Test St, Hobart Tasmania 7000", "7000"),
    ("3050 Great North Road, New Lynn, Auckland 060", None),
    (None, None),
])
def test_address_postcode_requires_a_postal_suffix(address, expected):
    assert extract_address_postcode(address) == expected


def test_street_number_does_not_create_a_postcode_conflict(monkeypatch):
    source = dict.fromkeys(clean.FIELDS, "")
    source.update(OBJECTID="1", Station_address="1250 George St, Sydney", Operator="Evie",
                  Number_of_plugs="2", Charger_Type="DC", Charger_rating="50 kW",
                  Latitude="-33.86", Longitude="151.20", PCODE="2000")
    monkeypatch.setattr(clean.pd, "read_csv", lambda *args, **kwargs: pd.DataFrame([source]))
    _, records, issues, _ = load_clean()
    assert records.iloc[0].postcode == "2000"
    assert records.iloc[0].address_postcode is None
    assert not records.iloc[0].address_conflict
    assert not any(i["code"] == "postcode_address_conflict" for i in issues)


def test_empty_source_is_rejected_with_a_data_error(monkeypatch):
    monkeypatch.setattr(clean.pd, "read_csv", lambda *args, **kwargs: pd.DataFrame(columns=clean.FIELDS))
    with pytest.raises(ValueError, match="no charger records"):
        load_clean()
