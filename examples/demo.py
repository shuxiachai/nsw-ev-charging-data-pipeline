# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to generate or revise this file.
# AI-generated or AI-revised material is included in this file.
"""Run a small synthetic DuckDB demonstration without the full source snapshot."""
import json
from pathlib import Path

import duckdb


def run_demo():
    root = Path(__file__).resolve().parent
    with duckdb.connect(":memory:") as con:
        con.execute("CREATE TABLE records AS SELECT * FROM read_csv(?, header=true)",
                    [str(root / "records.csv")])
        con.execute("CREATE TABLE attributes AS SELECT * FROM read_csv(?, header=true)",
                    [str(root / "attributes.csv")])
        con.execute("CREATE VIEW dc AS SELECT DISTINCT location_id,sa4_code FROM records WHERE charger_type='DC'")
        source_records, locations = con.execute(
            "SELECT count(*),count(DISTINCT location_id) FROM records").fetchone()
        dc_locations = con.execute("SELECT count(*) FROM dc").fetchone()[0]
        site_locations = con.execute(
            "SELECT count(DISTINCT d.location_id) FROM dc d JOIN attributes a USING(location_id) WHERE a.scope='site'").fetchone()[0]
        regional = [{"sa4_code": code, "dc_locations": count} for code, count in
                    con.execute("SELECT sa4_code,count(*) FROM dc GROUP BY sa4_code ORDER BY sa4_code").fetchall()]
        conflicts = [{"location_id": location, "attribute": attribute, "values": values} for location, attribute, values in
                     con.execute("SELECT location_id,attribute,list(DISTINCT value ORDER BY value) FROM attributes WHERE scope='site' GROUP BY location_id,attribute HAVING count(DISTINCT value)>1 ORDER BY location_id,attribute").fetchall()]
    return {"synthetic": True, "source_records": source_records, "locations": locations,
            "dc_locations": dc_locations, "site_augmented_dc_locations": site_locations,
            "site_coverage": round(site_locations / dc_locations, 6),
            "regional_dc_counts": regional, "source_conflicts": conflicts}


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
