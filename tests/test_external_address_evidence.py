# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Explicit external postal evidence must agree before matching/ranking."""
import pandas as pd
import pytest

from ev_pipeline.augment import match_sites
from tests.test_matching import frames


@pytest.mark.parametrize("address", [
    "1 Test Street, Sydney NSW 2001", "1 Test Street, Sydney 2001 NSW",
    "1 Test Street, Sydney, 2001, Australia",
])
def test_embedded_postcode_disqualifies_otherwise_matching_site(address):
    locations, records, sites = frames()
    sites.loc[0, "address"] = address
    matches, audit = match_sites(locations, records, sites)
    assert matches.empty
    assert audit.iloc[0].postcode_conflict
    assert audit.iloc[0].decision == "rejected_evidence"


def test_internal_postcode_conflict_blocks_when_source_postcode_is_unknown():
    locations, records, sites = frames()
    locations.loc[0, "address"] = "1 Test Street"
    locations.loc[0, ["postcode", "address_postcode"]] = None
    sites.loc[0, "address"] = "1 Test Street, Sydney NSW 2001"
    matches, audit = match_sites(locations, records, sites)
    assert matches.empty and audit.iloc[0].postcode_conflict


@pytest.mark.parametrize("address,postcode", [
    ("1 Test Street, Sydney NSW 2000", "2000"),
    ("1 Test Street, Sydney NSW 2000", ""),
    ("1 Test Street", "2000"),
    ("1250 George Street", "2000"),
])
def test_compatible_unknown_or_house_number_postal_evidence_remains_usable(address, postcode):
    locations, records, sites = frames()
    locations.loc[0, "address"] = address
    sites.loc[0, ["address", "postcode"]] = [address, postcode]
    matches, audit = match_sites(locations, records, sites)
    assert len(matches) == 1 and not audit.iloc[0].postcode_conflict


def test_postcode_conflict_is_removed_before_ranking():
    locations, records, sites = frames()
    valid = sites.assign(ocm_id=2)
    sites.loc[0, "address"] = "1 Test Street, Sydney NSW 2001"
    matches, audit = match_sites(locations, records, pd.concat([sites, valid], ignore_index=True))
    assert matches.ocm_id.tolist() == [2]
    assert audit.set_index("ocm_id").decision.to_dict() == {1: "rejected_evidence", 2: "accepted"}
