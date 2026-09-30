# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Canonical coastal distances preserve raw eligibility and source coordinates."""
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from ev_pipeline import clean


@pytest.fixture
def coastal_point(monkeypatch):
    regions = gpd.GeoDataFrame({"SA4_CODE26": ["122"], "SA4_NAME26": ["Synthetic region"],
                               "STE_CODE26": ["1"]}, geometry=[box(145, -35, 146, -34)], crs=4326)
    monkeypatch.setattr(clean.gpd, "read_file", lambda path: regions.copy())
    return pd.DataFrame([dict(record_id="r_original", location_id="l_original", source_row=2,
                              station_name="Coastal fixture", postcode="2093", address_postcode="2093",
                              lga="Synthetic council", latitude=-33.80467, longitude=151.2528397,
                              address_conflict=False)])


def nearest_distances(monkeypatch, *candidates):
    """Inject measured distances after the real point-in-polygon stage misses."""
    def nearest(points, regions, *, how, max_distance, distance_col):
        assert max_distance == 50 and how == "left" and distance_col == "distance_m"
        assert points.crs.to_epsg() == regions.crs.to_epsg() == 3577
        return pd.DataFrame([dict(location_id="l_original", sa4_code=code, distance_m=distance)
                             for code, distance in candidates])
    monkeypatch.setattr(clean.gpd, "sjoin_nearest", nearest)


@pytest.mark.parametrize("distance", [1.311081041223775, 1.3110810417422223])
def test_environment_roundoff_has_one_reported_distance_and_issue(coastal_point, monkeypatch, distance):
    nearest_distances(monkeypatch, ("122", distance))
    before = coastal_point.copy(deep=True)
    issues = []
    locations, _ = clean.spatial_assign(coastal_point, issues)
    assert locations.sa4_distance_m.tolist() == [1.311081]
    assert locations.sa4_code.tolist() == ["122"]
    assert locations.sa4_method.tolist() == ["coastal_nearest_within_50m"]
    assert issues == [dict(record_id="r_original", source_row=2,
                          code="spatial_coastal_nearest_within_50m", severity="warning",
                          detail="SA4=122, distance_m=1.311081; original point retained")]
    pd.testing.assert_frame_equal(coastal_point, before)
    pd.testing.assert_frame_equal(locations[before.columns], before)


@pytest.mark.parametrize("distance,accepted", [
    (49.9999996, True), (50.0, True), (50.0000004, False),
    (-0.0000001, False), (float("nan"), False), (float("inf"), False),
])
def test_raw_distance_controls_eligibility_before_rounding(coastal_point, monkeypatch, distance, accepted):
    nearest_distances(monkeypatch, ("122", distance))
    issues = []
    locations, _ = clean.spatial_assign(coastal_point, issues)
    row = locations.iloc[0]
    if accepted:
        assert row.sa4_code == "122" and row.sa4_method == "coastal_nearest_within_50m"
        assert row.sa4_distance_m == 50.0
    else:
        assert pd.isna(row.sa4_code) and pd.isna(row.sa4_distance_m)
        assert row.sa4_method == "unmatched" and issues[0]["severity"] == "error"


def test_equal_nearest_regions_are_not_resolved_by_reported_precision(coastal_point, monkeypatch):
    nearest_distances(monkeypatch, ("122", 1.311081041223775), ("123", 1.311081041223775))
    locations, _ = clean.spatial_assign(coastal_point, [])
    assert locations.sa4_code.isna().all() and locations.sa4_distance_m.isna().all()
    assert locations.sa4_method.tolist() == ["unmatched"]


def test_point_in_polygon_stays_exact_and_skips_coastal_distance(coastal_point, monkeypatch):
    coastal_point.loc[0, ["latitude", "longitude"]] = [-34.5, 145.5]
    def unexpected_nearest(*args, **kwargs):
        pytest.fail("A contained point must not use nearest-region approximation")
    monkeypatch.setattr(clean.gpd, "sjoin_nearest", unexpected_nearest)
    issues = []
    locations, _ = clean.spatial_assign(coastal_point, issues)
    assert locations.sa4_method.tolist() == ["point_in_polygon"]
    assert locations.sa4_distance_m.tolist() == [0.0]
    assert not issues
