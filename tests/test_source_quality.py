"""Source warning evidence is checked without changing coordinates or analysis eligibility."""
from copy import deepcopy
from hashlib import sha256
import json
import shutil

import pandas as pd
import pytest

from ev_pipeline import clean
from ev_pipeline.acquire import ROOT
from ev_pipeline.source_quality import source_quality_issues


@pytest.fixture
def quality_source():
    _, records, issues, _ = clean.load_clean()
    config = json.loads((ROOT / "config/reviewed_source_issues.json").read_text(encoding="utf-8"))
    return records, issues, config


def test_dapto_postcode_warning_leaves_point_and_conflict_status_unchanged(quality_source):
    records, issues, config = quality_source
    before = records.copy(deep=True)
    warning = source_quality_issues(records, config=config)
    pd.testing.assert_frame_equal(before, records)
    assert len(warning) == 1 and warning[0]["source_row"] == 1000
    assert warning[0]["code"] == "address_postcode_locality_mismatch"
    assert "reviewed_postcode=2530" in warning[0]["detail"]
    assert "OBJECTID=26918" in warning[0]["detail"] and "sha256=" in warning[0]["detail"]
    assert warning[0] in issues
    row = records.set_index("source_row").loc[1000]
    assert row.address_postcode == "2023" and pd.isna(row.postcode)
    assert not row.address_conflict and row.charger_type == "UPCOMING"
    assert [row.latitude, row.longitude] == [-34.4940356, 150.7915413]
    assert json.loads(row.raw_json) == config["reviews"][0]["raw_values"]


def test_known_truncated_labels_are_reviewable_without_global_alias_guesses(quality_source):
    records, issues, _ = quality_source
    flags = [i for i in issues if i["code"] == "operator_label_review_required"]
    assert len(flags) == 19
    selected = records[records.record_id.isin([i["record_id"] for i in flags])]
    assert selected.operator_name.value_counts().to_dict() == {"Fast Cities A": 17, "Energy Austra": 1, "University of": 1}
    assert clean.operator("University of") != clean.operator("Chargefox")
    assert selected.set_index("source_row").loc[1063, "operator_name"] == "University of"


@pytest.mark.parametrize("field,value", [("source_row", 99999), ("raw_json", "{}"), ("address", "Elsewhere"),
                                         ("latitude", -33.8), ("address_postcode", "2530"), ("record_id", "other")])
def test_changed_original_source_is_rejected(quality_source, field, value):
    records, _, config = quality_source
    records.loc[records.source_row.eq(1000), field] = value
    with pytest.raises(ValueError, match="guard|missing"):
        source_quality_issues(records, config=config)


def test_missing_reviewed_source_requires_explicit_short_input_mode(quality_source):
    records, _, config = quality_source
    with pytest.raises(ValueError, match="missing"):
        source_quality_issues(records.loc[records.source_row.ne(1000)], config=config)
    assert source_quality_issues(records.head(1), config=config, allow_absent=True) == []
    with pytest.raises(ValueError, match="missing"):
        source_quality_issues(records.loc[records.source_row.ne(1000)], config=config, allow_absent=True)


@pytest.mark.parametrize("change", ["missing", "metadata", "hash", "postcode", "locality", "objectid", "crs", "empty", "truncated", "geometry"])
def test_official_locality_original_and_semantics_are_checked(quality_source, tmp_path, change):
    records, _, config = quality_source
    source = config["sources"][0]
    path = tmp_path / source["file"]
    path.parent.mkdir(parents=True)
    original = ROOT / source["file"]
    shutil.copyfile(original, path)
    meta_path = path.with_name(path.name + ".meta.json")
    shutil.copyfile(original.with_name(original.name + ".meta.json"), meta_path)
    meta = json.loads(meta_path.read_text())
    if change == "missing":
        path.unlink()
    elif change == "metadata":
        meta["url"] = "https://example.com/not-official"
        meta_path.write_text(json.dumps(meta))
    elif change == "hash":
        path.write_bytes(path.read_bytes() + b" ")
    else:
        data = json.loads(path.read_text())
        properties = data["features"][0]["properties"]
        if change in ("postcode", "locality", "objectid"):
            properties[{"postcode": "postcode", "locality": "suburbname", "objectid": "OBJECTID"}[change]] = {"postcode": 2023, "locality": "ELSEWHERE", "objectid": 99999}[change]
        elif change == "crs":
            data.pop("crs")
        elif change == "empty":
            data["features"] = []
        elif change == "truncated":
            data["exceededTransferLimit"] = True
        else:
            data["features"][0]["geometry"] = {"type": "Polygon", "coordinates": [[[150, -33], [150.01, -33], [150.01, -33.01], [150, -33]]]} 
        body = json.dumps(data).encode()
        path.write_bytes(body)
        digest = sha256(body).hexdigest()
        source.update(sha256=digest, bytes=len(body))
        meta.update(sha256=digest, bytes=len(body))
        meta_path.write_text(json.dumps(meta))
    with pytest.raises((ValueError, FileNotFoundError)):
        source_quality_issues(records, config=config, root=tmp_path)


@pytest.mark.parametrize("key,value", [("locality_name", "ELSEWHERE"), ("reviewed_postcode", "2023"), ("locality_object_id", 1)])
def test_config_claims_are_checked_against_source_properties(quality_source, key, value):
    records, _, config = quality_source
    changed = deepcopy(config)
    changed["reviews"][0][key] = value
    with pytest.raises(ValueError):
        source_quality_issues(records, config=changed)
