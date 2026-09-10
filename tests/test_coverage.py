import duckdb
import pytest

from ev_pipeline.coverage import attribute_coverage, augmentation_composition


def test_coverage_deduplicates_locations_and_separates_scope_and_station_codes():
    with duckdb.connect() as con:
        con.execute("CREATE TABLE charger_record(location_id VARCHAR, charger_type VARCHAR)")
        con.execute("INSERT INTO charger_record VALUES ('a','DC'),('a','DC'),('b','DC'),('c','DC'),('d','AC')")
        con.execute("CREATE TABLE augmentation(location_id VARCHAR, scope VARCHAR, attribute VARCHAR)")
        con.execute("""INSERT INTO augmentation VALUES
            ('a','site','fee'),('a','site','fee'),('a','site','operator_station_code'),
            ('b','site','operator_station_code'),('b','operator','website'),
            ('c','operator','website'),('d','site','fee')""")
        composition = augmentation_composition(con).set_index('category')
        assert composition.dc_locations.to_dict() == {
            'non_identifier_site_attribute': 1, 'station_code_only': 1, 'no_site_augmentation': 1}
        assert composition.fraction_all_dc.tolist() == pytest.approx([1 / 3] * 3)
        attributes = attribute_coverage(con).set_index(['scope', 'attribute'])
        fee = attributes.loc[('site', 'fee')]
        assert fee.covered_dc_locations == 1
        assert fee.source_observations == 2
        assert fee.fraction_all_dc == pytest.approx(1 / 3)
        assert attributes.loc[('operator', 'website')].covered_dc_locations == 2


def test_empty_dc_composition_retains_explicit_zero_categories():
    with duckdb.connect() as con:
        con.execute("CREATE TABLE charger_record(location_id VARCHAR, charger_type VARCHAR)")
        con.execute("CREATE TABLE augmentation(location_id VARCHAR, scope VARCHAR, attribute VARCHAR)")
        result = augmentation_composition(con)
        assert len(result) == 3 and result.dc_locations.sum() == 0
        assert result.fraction_all_dc.isna().all()
        assert attribute_coverage(con).empty
