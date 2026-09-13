# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Original points retain the cleaning and whole-row representative semantics."""
import json

import pytest

from ev_pipeline.pipeline import connect, original_coordinates_match_representatives


@pytest.fixture
def provenance_db():
    # Small logical tables isolate this invariant from unrelated pinned reviews.
    with connect(":memory:") as con:
        con.execute("CREATE TABLE location(location_id VARCHAR,original_latitude DOUBLE,original_longitude DOUBLE)")
        con.execute("CREATE TABLE charger_record(record_id VARCHAR,location_id VARCHAR,source_row INTEGER,raw_json JSON)")
        con.execute("CREATE TABLE source_resolution(record_id VARCHAR,decision VARCHAR,new_postcode VARCHAR)")
        con.execute("CREATE TABLE reviewed_resolution(record_id VARCHAR,decision VARCHAR,new_postcode VARCHAR)")
        con.execute("CREATE TABLE reviewed_identity(location_id VARCHAR,representative_record_id VARCHAR)")
        yield con


def observation(con, record_id="record", source_row=2, latitude="-33.86", longitude="151.2", **fields):
    raw = dict(Latitude=latitude, Longitude=longitude, PCODE="", Station_name="", LGANAME="")
    raw.update(fields)
    con.execute("INSERT INTO charger_record VALUES (?,'location',?,?)", [record_id, source_row, json.dumps(raw)])


@pytest.mark.parametrize("latitude,longitude,expected", [
    ("-33.86", "151.2", (-33.86, 151.2)),
    (" －３３．８６ ", "１５１．２", (-33.86, 151.2)),
    ("0", "0", (0.0, 0.0)),
    ("", "151.2", (None, None)),
    ("-33.86", "", (None, None)),
    ("not a latitude", "151.2", (None, None)),
    ("-91", "151.2", (None, None)),
    ("-33.86", "181", (None, None)),
    ("NaN", "151.2", (None, None)),
    ("-33.86", "Infinity", (None, None)),
])
def test_original_pairs_follow_cleaning_including_legitimate_nulls(provenance_db, latitude, longitude, expected):
    observation(provenance_db, latitude=latitude, longitude=longitude)
    provenance_db.execute("INSERT INTO location VALUES ('location',?,?)", expected)
    assert original_coordinates_match_representatives(provenance_db)


@pytest.mark.parametrize("saved", [(None, None), (None, 151.2), (-33.86, None), (-33.85, 151.2)])
def test_valid_source_originals_cannot_be_erased_or_replaced(provenance_db, saved):
    observation(provenance_db)
    provenance_db.execute("INSERT INTO location VALUES ('location',?,?)", saved)
    assert not original_coordinates_match_representatives(provenance_db)


def test_one_invalid_source_axis_does_not_preserve_an_invented_partial_pair(provenance_db):
    observation(provenance_db, latitude="")
    provenance_db.execute("INSERT INTO location VALUES ('location',NULL,151.2)")
    assert not original_coordinates_match_representatives(provenance_db)


def test_completeness_and_source_row_choose_one_whole_observation(provenance_db):
    observation(provenance_db, "earliest", 2, "-33.861", "151.201", PCODE="NSW 2000")
    observation(provenance_db, "later", 3, "-33.862", "151.202", Station_name="A site")
    provenance_db.execute("INSERT INTO location VALUES ('location',-33.861,151.201)")
    assert original_coordinates_match_representatives(provenance_db)
    # Equal completeness uses source-row order, never insertion order.
    provenance_db.execute("CREATE TABLE reordered AS SELECT * FROM charger_record ORDER BY source_row DESC")
    provenance_db.execute("DELETE FROM charger_record")
    provenance_db.execute("INSERT INTO charger_record SELECT * FROM reordered")
    assert original_coordinates_match_representatives(provenance_db)


@pytest.mark.parametrize("resolution_table", ["source_resolution", "reviewed_resolution"])
def test_final_postcode_completeness_selects_the_correct_original_point(provenance_db, resolution_table):
    observation(provenance_db, "earliest", 2, "-33.861", "151.201", LGANAME="Council")
    observation(provenance_db, "corrected", 3, "-33.862", "151.202", Station_name="A site")
    provenance_db.execute(f"INSERT INTO {resolution_table} VALUES ('corrected','resolved','2000')")
    provenance_db.execute("INSERT INTO location VALUES ('location',-33.862,151.202)")
    assert original_coordinates_match_representatives(provenance_db)


def test_reviewed_representative_has_priority_over_more_complete_or_earlier_rows(provenance_db):
    observation(provenance_db, "ordinary", 2, "-33.861", "151.201", Station_name="Complete", PCODE="2000", LGANAME="Council")
    observation(provenance_db, "reviewed", 3, "-33.862", "151.202")
    provenance_db.execute("INSERT INTO reviewed_identity VALUES ('location','reviewed')")
    provenance_db.execute("INSERT INTO location VALUES ('location',-33.862,151.202)")
    assert original_coordinates_match_representatives(provenance_db)
    provenance_db.execute("UPDATE location SET original_latitude=-33.861,original_longitude=151.201")
    assert not original_coordinates_match_representatives(provenance_db)


def test_missing_reviewed_representative_does_not_fall_back_silently(provenance_db):
    observation(provenance_db)
    provenance_db.execute("INSERT INTO reviewed_identity VALUES ('location','missing')")
    provenance_db.execute("INSERT INTO location VALUES ('location',-33.86,151.2)")
    assert not original_coordinates_match_representatives(provenance_db)
