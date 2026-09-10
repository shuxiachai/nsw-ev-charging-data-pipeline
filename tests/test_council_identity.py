"""Council venue evidence supports exactly two source-bound Evie identity reviews."""
from hashlib import sha256
import json
import shutil

import pandas as pd
import pytest

from ev_pipeline.acquire import ROOT
from ev_pipeline.clean import load_clean, location_representatives, flag_final_location_conflicts
from ev_pipeline.identity import acquire_identities, apply_reviewed_identities, identity_evidence_audit


@pytest.fixture
def council_source():
    _, records, _, _ = load_clean()
    config = json.loads((ROOT / "config/reviewed_identities.json").read_text(encoding="utf8"))
    config["groups"] = [group for group in config["groups"] if group["review_id"] in {"RI09", "RI10"}]
    files = {value for group in config["groups"] for key, value in group["evidence"].items() if key.endswith("_file")}
    config["evidence_sources"] = [source for source in config["evidence_sources"] if source["file"] in files]
    return records, config


def test_council_identity_keeps_complete_observations_and_original_representatives(council_source):
    original, config = council_source
    result, audit = apply_reviewed_identities(original, [], config=config)
    assert result.location_id.nunique() == original.location_id.nunique() - 2
    assert result.loc[result.location_id.ne(original.location_id), "source_row"].tolist() == [69, 512]
    pd.testing.assert_frame_equal(original.drop(columns="location_id"), result.drop(columns="location_id"))
    representatives = location_representatives(result).set_index("source_row")
    for removed, representative in [(512, 1528), (69, 1861)]:
        assert removed not in representatives.index
        pd.testing.assert_series_equal(
            representatives.loc[representative], original.set_index("source_row").loc[representative], check_names=False,
        )
    assert audit.review_date.eq("2026-09-10").all()
    assert identity_evidence_audit(config=config).shape == (4, 5)
    flag_final_location_conflicts(result, [])
    assert not result.loc[result.source_row.isin([69, 512, 1528, 1861]), "address_conflict"].any()


def test_new_review_dates_do_not_rewrite_previous_identity_history():
    _, records, _, _ = load_clean()
    _, audit = apply_reviewed_identities(records, [])
    assert audit.loc[audit.review_id.isin(["RI09", "RI10"]), "review_date"].eq("2026-09-10").all()
    assert audit.loc[~audit.review_id.isin(["RI09", "RI10"]), "review_date"].eq("2026-09-09").all()


@pytest.fixture
def council_evidence(council_source, tmp_path):
    records, config = council_source
    for source in config["evidence_sources"]:
        original, copied = ROOT / source["file"], tmp_path / source["file"]
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, copied)
        shutil.copyfile(original.with_name(original.name + ".meta.json"), copied.with_name(copied.name + ".meta.json"))
    return records, config, tmp_path


@pytest.mark.parametrize("provider,old,new", [
    ("cowell_council_proposal", "3A Cowell St", "99 Cowell St"),
    ("cowell_council_proposal", "1 x charger with 2 x charging bays", "2 x chargers with 4 x charging bays"),
    ("cowell_council_operation", "owned and operated by Evie", "owned and operated by Tesla"),
    ("parraween_council_installation", "<td>Parraween Street, Cremorne (Evie)</td>\n\t\t\t<td>4</td>", "<td>Parraween Street, Cremorne (Evie)</td>\n\t\t\t<td>8</td>"),
    ("parraween_council_carpark", "four charging bays", "eight charging bays"),
    ("parraween_council_carpark", "Parraween Street, Cremorne, 2090", "Other Street, Cremorne, 2090"),
])
def test_complete_council_evidence_semantics_are_checked_after_repinning(council_evidence, provider, old, new):
    records, config, root = council_evidence
    source = next(item for item in config["evidence_sources"] if item["provider"] == provider)
    path = root / source["file"]
    body = path.read_text(encoding="utf8")
    changed = body.replace(old, new)
    assert changed != body
    path.write_bytes(changed.encode("utf8"))
    source["sha256"] = sha256(path.read_bytes()).hexdigest()
    meta_path = path.with_name(path.name + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf8"))
    meta.update(sha256=source["sha256"], bytes=path.stat().st_size)
    meta_path.write_text(json.dumps(meta), encoding="utf8")
    before, issues = records.copy(deep=True), []
    with pytest.raises(ValueError, match="Council.*evidence"):
        apply_reviewed_identities(records, issues, root=root, config=config)
    pd.testing.assert_frame_equal(records, before)
    assert not issues


@pytest.mark.parametrize("change", ["missing_body", "missing_manifest", "wrong_url", "wrong_status"])
def test_council_originals_are_required_and_fail_closed(council_evidence, change):
    _, config, root = council_evidence
    path = root / config["evidence_sources"][0]["file"]
    meta_path = path.with_name(path.name + ".meta.json")
    if change == "missing_body":
        path.unlink()
    elif change == "missing_manifest":
        meta_path.unlink()
    else:
        meta = json.loads(meta_path.read_text(encoding="utf8"))
        meta["url" if change == "wrong_url" else "status_code"] = "https://example.com/" if change == "wrong_url" else 403
        meta_path.write_text(json.dumps(meta), encoding="utf8")
    with pytest.raises((ValueError, FileNotFoundError), match="evidence"):
        identity_evidence_audit(root=root, config=config)


@pytest.mark.parametrize("offline", [True, False])
def test_acquisition_verifies_frozen_council_originals_in_both_modes(council_evidence, offline):
    _, config, root = council_evidence
    audit = acquire_identities(offline=offline, root=root, config=config)
    assert audit.shape == (4, 5)
    (root / config["evidence_sources"][0]["file"]).unlink()
    with pytest.raises(FileNotFoundError, match="restore the reviewed snapshot"):
        acquire_identities(offline=offline, root=root, config=config)


@pytest.mark.parametrize("change", ["postcode", "source_category", "coordinate", "extra_member", "larger_bound", "missing_evidence", "swapped_kind"])
def test_council_reviews_cannot_become_a_generic_nearby_or_sydney_alias_rule(council_source, change):
    records, config = council_source
    group = config["groups"][0]
    mask = records.source_row.eq(512)
    if change == "postcode":
        records.loc[mask, "postcode"] = "2000"
    elif change == "source_category":
        records.loc[mask, "source_category"] = "Unreviewed source"
    elif change == "coordinate":
        records.loc[mask, "latitude"] += 0.000001
    elif change == "extra_member":
        extra = records.loc[mask].copy()
        extra["record_id"] = "unreviewed_nearby"
        records = pd.concat([records, extra], ignore_index=True)
    elif change == "larger_bound":
        group["max_member_distance_m"] = 21
    elif change == "missing_evidence":
        group.pop("evidence")
    else:
        group["evidence"]["kind"] = "parraween_evie_council_venue"
        group["evidence"]["installation_file"] = config["groups"][1]["evidence"]["installation_file"]
        group["evidence"]["carpark_file"] = config["groups"][1]["evidence"]["carpark_file"]
    before, issues = records.copy(deep=True), []
    with pytest.raises(ValueError):
        apply_reviewed_identities(records, issues, config=config)
    pd.testing.assert_frame_equal(records, before)
    assert not issues
