# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Operator display names and case-insensitive IDs share one stable identity."""
import json

import duckdb
import pandas as pd

from ev_pipeline import clean
from ev_pipeline.clean import ALIASES, identifier, load_clean, operator


def test_case_only_names_have_one_canonical_name_regardless_of_order():
    for variants, expected in [
        (["Chargefox", "CHARGEFOX", "chargefox"], "Chargefox"),
        (["New Provider", "NEW PROVIDER", "new provider"], "new provider"),
    ]:
        assert [operator(value) for value in variants] == [expected] * len(variants)
        assert [operator(value) for value in reversed(variants)] == [expected] * len(variants)
        assert len({identifier("o_", operator(value).casefold()) for value in variants}) == 1
    assert operator("BP Pulse (UK)") != operator("BP Pulse (AU)")


def test_every_registered_display_name_is_itself_canonical():
    for canonical in ALIASES.values():
        assert operator(canonical) == canonical
        assert operator(canonical.upper()) == canonical


def test_case_variants_insert_as_one_operator_without_losing_raw_labels(monkeypatch):
    base = dict.fromkeys(clean.FIELDS, "")
    base.update(Station_address="10 Test St, Sydney NSW 2000", Number_of_plugs="2", Charger_Type="DC",
                Charger_rating="50 kW", Latitude="-33.86", Longitude="151.20", PCODE="2000")
    source = pd.DataFrame([dict(base, OBJECTID="1", Operator="Chargefox"),
                           dict(base, OBJECTID="2", Operator="CHARGEFOX", Latitude="-33.87")])
    monkeypatch.setattr(clean.pd, "read_csv", lambda *args, **kwargs: source.copy())
    _, records, issues, _ = load_clean()
    operators = records[["operator_id", "operator_name"]].drop_duplicates()
    assert len(operators) == 1 and operators.iloc[0].operator_name == "Chargefox"
    assert [json.loads(value)["Operator"] for value in records.raw_json] == ["Chargefox", "CHARGEFOX"]
    assert any(i["code"] == "operator_normalized" and i["source_row"] == 3 for i in issues)
    with duckdb.connect(":memory:") as con:
        con.execute("CREATE TABLE operator(operator_id VARCHAR PRIMARY KEY,operator_name VARCHAR UNIQUE NOT NULL)")
        con.register("input_operators", operators)
        con.execute("INSERT INTO operator SELECT * FROM input_operators")
        assert con.execute("SELECT count(*) FROM operator").fetchone()[0] == 1


def test_actual_source_names_have_explicit_canonical_spellings():
    _, records, _, _ = load_clean()
    assert records.operator_id.nunique() == records.operator_name.nunique()
    assert all(name.casefold() in ALIASES and ALIASES[name.casefold()] == name
               for name in records.operator_name.unique())
