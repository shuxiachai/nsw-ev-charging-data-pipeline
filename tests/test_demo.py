# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to generate or revise this file.
# AI-generated or AI-revised material is included in this file.
import importlib.util
from pathlib import Path


def test_synthetic_demo_deduplicates_locations_and_separates_site_scope():
    path = Path(__file__).resolve().parents[1] / "examples/demo.py"
    spec = importlib.util.spec_from_file_location("synthetic_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_demo()
    assert result == {
        "synthetic": True,
        "source_records": 5,
        "locations": 4,
        "dc_locations": 3,
        "site_augmented_dc_locations": 2,
        "site_coverage": 0.666667,
        "regional_dc_counts": [{"sa4_code": "R1", "dc_locations": 2},
                               {"sa4_code": "R2", "dc_locations": 1}],
        "source_conflicts": [{"location_id": "L3", "attribute": "dc_connector_types",
                             "values": ["CCS1", "CCS2"]}],
    }
