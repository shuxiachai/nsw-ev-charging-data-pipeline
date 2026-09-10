"""Previously admissible NULL/non-finite and identity errors must fail at storage."""
import pytest
import duckdb

from ev_pipeline.acquire import ROOT
from ev_pipeline.pipeline import connect


@pytest.fixture
def schema_db():
    with connect(":memory:") as con:
        con.execute((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))
        con.execute("INSERT INTO operator VALUES ('op','Example')")
        con.execute("""INSERT INTO location(location_id,operator_id,address,address_conflict,
                    sa4_method,original_address_conflict,resolution_method)
                    VALUES ('loc','op','Example address',FALSE,'invalid_coordinates',FALSE,'unchanged')""")
        con.execute("""INSERT INTO source_snapshot VALUES ('data/raw/ev_20251216.csv',
                    'https://example.test/source','2026-09-09T00:00:00Z',repeat('a',64),1)""")
        yield con


def add_record(con, record_id, source_row, low, high):
    con.execute("""INSERT INTO charger_record(record_id,location_id,source_row,charger_type,
                power_min_kw,power_max_kw,power_kind,power_raw,raw_json)
                VALUES (?,'loc',?,'DC',?,?,'source_observation','retained rating','{}')""",
                [record_id, source_row, low, high])


@pytest.mark.parametrize("low,high", [
    (None, -1), (None, 100), (100, None), (-1, -1), (20, 10),
    (float('nan'), float('nan')), (100, float('inf')), (float('inf'), float('inf')),
])
def test_power_constraints_reject_invalid_null_and_nonfinite_combinations(schema_db, low, high):
    with pytest.raises(duckdb.ConstraintException):
        add_record(schema_db, "bad", 2, low, high)


def test_power_observations_preserve_nonrepresentative_source_ratings(schema_db):
    add_record(schema_db, "representative", 2, None, None)
    add_record(schema_db, "other-observation", 3, 50, 150)
    add_record(schema_db, "separate-observation", 4, 75, 75)
    rows = schema_db.execute("""SELECT record_id,source_row,power_min_kw,power_max_kw,source_file
                              FROM location_power_observations ORDER BY source_row""").fetchall()
    assert rows == [("other-observation", 3, 50, 150, "data/raw/ev_20251216.csv"),
                    ("separate-observation", 4, 75, 75, "data/raw/ev_20251216.csv")]
    assert schema_db.execute("SELECT count(*) FROM charger_record").fetchone()[0] == 3


def test_duplicate_logical_source_row_is_rejected(schema_db):
    add_record(schema_db, "first", 2, None, None)
    with pytest.raises(duckdb.ConstraintException):
        add_record(schema_db, "second", 2, None, None)


def test_nonhex_source_digest_is_rejected(schema_db):
    with pytest.raises(duckdb.ConstraintException):
        schema_db.execute("""INSERT INTO source_snapshot VALUES ('bad','https://example.test',
                          '2026-09-09T00:00:00Z',repeat('g',64),1)""")
