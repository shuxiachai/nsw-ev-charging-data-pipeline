"""Explicit identity reviews retain observations and never enable nearby clustering."""
from copy import deepcopy
from hashlib import sha256
import json
import shutil

import pandas as pd
import pytest

from ev_pipeline.acquire import ROOT
from ev_pipeline.clean import load_clean, location_representatives, flag_final_location_conflicts
from ev_pipeline.identity import (
    AUDIT_COLUMNS, EVIDENCE_COLUMNS, LEDGER_ATTRIBUTE, apply_reviewed_identities,
    identity_evidence_audit, reviewed_identity_groups,
)
from ev_pipeline.resolve import resolve_conflicts
from ev_pipeline.reviewed import apply_reviewed_resolutions


@pytest.fixture
def identity_source():
    _, records, _, _ = load_clean()
    config = json.loads((ROOT / "config/reviewed_identities.json").read_text(encoding="utf-8"))
    return records, config


def test_only_ten_reviewed_locations_merge_and_all_observations_survive(identity_source):
    original, config = identity_source
    issues = []
    result, audit = apply_reviewed_identities(original, issues, config=config)
    assert len(result) == len(original) and result.location_id.nunique() == original.location_id.nunique() - 10
    pd.testing.assert_frame_equal(original.drop(columns="location_id"), result.drop(columns="location_id"))
    changed = result.loc[result.location_id.ne(original.location_id), "source_row"].tolist()
    assert changed == [69, 223, 244, 512, 599, 906, 937, 1077, 1088, 1565]
    assert audit.shape == (21, 9) and list(audit.columns) == AUDIT_COLUMNS
    assert set(audit.source_row) == {223, 1308, 575, 1565, 599, 1590, 244, 817, 1012, 906, 1562, 937, 1398, 307, 1077, 361, 1088, 512, 1528, 69, 1861}
    assert len(issues) == 21 and all(x["code"] == "reviewed_location_identity" for x in issues)
    assert all("original Source=" in x["detail"] for x in issues)
    assert LEDGER_ATTRIBUTE not in original.attrs
    json.dumps(result.attrs)  # Plain serializable ledger, no pandas objects.
    for group in config["groups"]:
        ids = {m["record_id"] for m in group["members"]}
        rows = result.loc[result.record_id.isin(ids)]
        assert rows.location_id.nunique() == 1
        source = original.loc[original.record_id.eq(group["representative_record_id"])].iloc[0]
        assert rows.location_id.eq(source.location_id).all()
    # Missing rating text is not converted into the other observation's 22 kW.
    assert result.set_index("source_row").loc[[1308, 1590], "power_max_kw"].isna().all()
    assert result.set_index("source_row").loc[[223, 599], "power_max_kw"].eq(22).all()


def test_reviewed_representative_is_an_entire_original_row_and_order_independent(identity_source):
    original, config = identity_source
    merged, _ = apply_reviewed_identities(original, [], config=config)
    chosen = location_representatives(merged).set_index("location_id")
    shuffled = location_representatives(merged.iloc[::-1]).set_index("location_id")
    assert chosen.record_id.to_dict() == shuffled.record_id.to_dict()
    for location_id, representative in reviewed_identity_groups(merged).items():
        source = original.loc[original.record_id.eq(representative)].iloc[0]
        pd.testing.assert_series_equal(chosen.loc[location_id], source.drop(labels="location_id"), check_names=False)


@pytest.mark.parametrize("field,value", [
    ("record_id", "different-id"), ("source_row", 99999), ("operator_name", "Tesla"),
    ("latitude", -32.7640556), ("longitude", 151.2915995),
    ("postcode", "2000"), ("source_category", "Other source"),
    ("location_id", "different-location"), ("raw_json", "{}"),
])
def test_original_identity_and_complete_source_values_are_guarded(identity_source, field, value):
    records, config = identity_source
    records.loc[records.source_row.eq(1308), field] = value
    before = records.copy(deep=True)
    issues = []
    with pytest.raises(ValueError, match="source guard|Unreviewed member"):
        apply_reviewed_identities(records, issues, config=config)
    pd.testing.assert_frame_equal(records, before)
    assert not issues  # No partial review/issues after a late-group failure.


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra_location_member"])
def test_exact_membership_is_required(identity_source, change):
    records, config = identity_source
    member = records.loc[records.source_row.eq(1565)]
    if change == "missing":
        records = records.loc[records.source_row.ne(1565)]
    elif change == "duplicate":
        records = pd.concat([records, member], ignore_index=True)
    else:
        extra = member.copy()
        extra["record_id"] = "unreviewed_record"
        records = pd.concat([records, extra], ignore_index=True)
    with pytest.raises(ValueError):
        apply_reviewed_identities(records, [], config=config)


def test_local_exception_survives_both_resolution_stages_without_coordinate_changes(identity_source):
    original, config = identity_source
    issues = []
    merged, _ = apply_reviewed_identities(original, issues, config=config)
    resolved, _ = resolve_conflicts(merged, issues)
    reviewed, _ = apply_reviewed_resolutions(resolved, issues)
    assert len(reviewed_identity_groups(reviewed)) == 10
    reviewed_ids = {m["record_id"] for group in config["groups"] for m in group["members"]}
    before = reviewed.loc[reviewed.record_id.isin(reviewed_ids)].copy()
    flag_final_location_conflicts(reviewed, issues)
    after = reviewed.loc[reviewed.record_id.isin(reviewed_ids)]
    pd.testing.assert_frame_equal(before, after)
    assert not after.address_conflict.any()
    pd.testing.assert_frame_equal(
        original.set_index("record_id").loc[sorted(reviewed_ids), ["latitude", "longitude", "raw_json"]],
        reviewed.set_index("record_id").loc[sorted(reviewed_ids), ["latitude", "longitude", "raw_json"]],
    )


@pytest.mark.parametrize("change", ["coordinate", "postcode", "raw", "extra_member", "no_ledger"])
def test_post_merge_drift_disables_only_the_reviewed_exception(identity_source, change):
    records, config = identity_source
    merged, _ = apply_reviewed_identities(records, [], config=config)
    mask = merged.source_row.eq(1565)
    location_id = merged.loc[mask, "location_id"].iloc[0]
    if change == "coordinate":
        merged.loc[mask, "latitude"] += 0.000001  # Still sub-metre; no general tolerance is allowed.
    elif change == "postcode":
        merged.loc[mask, "postcode"] = "2000"
    elif change == "raw":
        merged.loc[mask, "raw_json"] = "{}"
    elif change == "extra_member":
        extra = merged.loc[mask].copy()
        extra["record_id"] = "unreviewed_record"
        merged = pd.concat([merged, extra], ignore_index=True)
    else:
        merged.attrs.clear()
    assert location_id not in reviewed_identity_groups(merged)
    issues = []
    flag_final_location_conflicts(merged, issues)
    assert merged.loc[merged.location_id.eq(location_id), "address_conflict"].all()
    assert any(i["code"] == "post_resolution_location_conflict" for i in issues)


def test_identity_application_is_idempotent_and_rechecks_its_ledger(identity_source):
    records, config = identity_source
    issues = []
    first, audit = apply_reviewed_identities(records, issues, config=config)
    second, repeated = apply_reviewed_identities(first, issues, config=config)
    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(audit, repeated)
    assert len(issues) == 21
    changed = deepcopy(config)
    changed["groups"][0]["representative_record_id"] = changed["groups"][0]["members"][1]["record_id"]
    with pytest.raises(ValueError, match="ledger"):
        apply_reviewed_identities(first, issues, config=changed)


def test_complete_buchanan_membership_preserves_missing_source_postcode(identity_source):
    records, config = identity_source
    merged, audit = apply_reviewed_identities(records, [], config=config)
    indexed = merged.set_index("source_row")
    assert indexed.loc[[244, 817, 1012], "location_id"].nunique() == 1
    assert pd.isna(indexed.loc[1012, "postcode"])
    assert indexed.loc[1012, "address_postcode"] == "2431"
    assert pd.isna(indexed.loc[1012, "lga"]) and pd.isna(indexed.loc[1012, "source_category"])
    assert json.loads(indexed.loc[1012, "raw_json"])["PCODE"] == ""
    assert indexed.loc[[244, 1012], "power_max_kw"].eq(22).all()
    assert pd.isna(indexed.loc[817, "power_max_kw"])
    assert indexed.loc[906, "power_max_kw"] == 6 and pd.isna(indexed.loc[1562, "power_max_kw"])
    assert indexed.loc[[906, 1562, 937, 1398], "number_of_plugs"].eq(4).all()
    assert set(audit.loc[audit.review_id.eq("RI04"), "source_row"]) == {244, 817, 1012}
    incomplete = deepcopy(config)
    incomplete["groups"][3]["members"] = incomplete["groups"][3]["members"][:2]
    with pytest.raises(ValueError, match="Unreviewed member"):
        apply_reviewed_identities(records, [], config=incomplete)
    # The fourth investigated pair has insufficient venue evidence and is untouched.
    assert indexed.loc[[818, 1703], "location_id"].nunique() == 2


def test_operator_evidence_has_complete_persistable_provenance(identity_source):
    _, config = identity_source
    audit = identity_evidence_audit(config=config)
    assert audit.shape == (14, 5) and list(audit.columns) == EVIDENCE_COLUMNS
    assert audit.groupby("review_id").size().to_dict() == {"RI04": 2, "RI05": 2, "RI06": 2, "RI07": 2, "RI08": 2, "RI09": 2, "RI10": 2}
    assert set(audit.role) == {"operator_map", "operator_location_detail", "venue_charger_installation", "venue_address", "operator_venue_map", "charging_project_supplier", "council_venue_proposal", "council_venue_operation", "council_venue_installation"}
    assert set(audit.loc[audit.review_id.isin(["RI04", "RI05", "RI06"]), "element_id"]) == {"845", "1437", "1380"}
    for row in audit.itertuples():
        assert sha256((ROOT / row.source_file).read_bytes()).hexdigest() == row.sha256
    assert len(audit.source_file.unique()) == 12


@pytest.fixture
def evidence_copy(identity_source, tmp_path):
    records, config = identity_source
    for source in config["evidence_sources"]:
        original, copied = ROOT / source["file"], tmp_path / source["file"]
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, copied)
        shutil.copyfile(original.with_name(original.name + ".meta.json"), copied.with_name(copied.name + ".meta.json"))
    return records, config, tmp_path


def _repin_changed_fixture(config, root, filename, body):
    """Change all fixture hashes so tests reach parsing guards, not only hashing."""
    path = root / filename
    path.write_bytes(body)
    digest = sha256(body).hexdigest()
    next(source for source in config["evidence_sources"] if source["file"] == filename)["sha256"] = digest
    manifest_path = path.with_name(path.name + ".meta.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(sha256=digest, bytes=len(body))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


@pytest.mark.parametrize("change", ["missing", "missing_manifest", "content", "metadata_method", "metadata_element"])
def test_missing_changed_or_mislabelled_original_evidence_fails_closed(evidence_copy, change):
    records, config, root = evidence_copy
    path = root / config["groups"][3]["evidence"]["detail_file"]
    manifest_path = path.with_name(path.name + ".meta.json")
    if change == "missing":
        path.unlink()
    elif change == "missing_manifest":
        manifest_path.unlink()
    elif change == "content":
        path.write_bytes(path.read_bytes() + b" ")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["method" if change == "metadata_method" else "location_id"] = "GET" if change == "metadata_method" else 366
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before, issues = records.copy(deep=True), []
    with pytest.raises((ValueError, FileNotFoundError), match="evidence|metadata"):
        apply_reviewed_identities(records, issues, config=config, root=root)
    pd.testing.assert_frame_equal(records, before)
    assert not issues


@pytest.mark.parametrize("change", ["map_id", "map_name", "map_point", "detail_name", "detail_address", "detail_failure"])
def test_actual_operator_map_and_detail_are_parsed_even_with_matching_hashes(evidence_copy, change):
    records, config, root = evidence_copy
    evidence = config["groups"][3]["evidence"]
    filename = evidence["map_file"] if change.startswith("map_") else evidence["detail_file"]
    content = (root / filename).read_text(encoding="utf-8")
    if change == "map_id":
        content = content.replace('"id":845,', '"id":999845,')
    elif change == "map_name":
        content = content.replace('"id":845,"name":"Kempsey Shire Council"', '"id":845,"name":"Other Venue"')
    elif change == "map_point":
        content = content.replace('"lat":-30.8862295', '"lat":-31.8862295')
    else:
        detail = json.loads(content)
        if change == "detail_name":
            detail["data"] = detail["data"].replace("Kempsey Shire Council", "Other Venue")
        elif change == "detail_address":
            detail["data"] = detail["data"].replace("19 Buchanan Dr", "99 Other Road")
        else:
            detail["success"] = False
        content = json.dumps(detail)
    assert content != (root / filename).read_text(encoding="utf-8")
    _repin_changed_fixture(config, root, filename, content.encode())
    with pytest.raises(ValueError, match="operator map|operator detail|location detail"):
        apply_reviewed_identities(records, [], config=config, root=root)


def test_source_only_reviews_have_a_typed_empty_evidence_audit(identity_source):
    records, config = identity_source
    config["groups"] = config["groups"][:3]
    config["evidence_sources"] = []
    assert identity_evidence_audit(config=config).shape == (0, 5)
    merged, audit = apply_reviewed_identities(records, [], config=config)
    assert merged.location_id.nunique() == records.location_id.nunique() - 3
    assert len(audit) == 6


def test_venue_reviews_preserve_distinct_ratings_and_pending_counterexamples(identity_source):
    records, config = identity_source
    merged, _ = apply_reviewed_identities(records, [], config=config)
    before, after = records.set_index("source_row"), merged.set_index("source_row")
    for first, second in [(307, 1077), (361, 1088)]:
        assert after.loc[first, "location_id"] == after.loc[second, "location_id"]
        assert after.loc[first, "power_max_kw"] == 175
        assert after.loc[second, "power_max_kw"] == 350
        assert after.loc[first, "raw_json"] == before.loc[first, "raw_json"]
        assert after.loc[second, "raw_json"] == before.loc[second, "raw_json"]
        assert not before.loc[first, ["latitude", "longitude"]].equals(before.loc[second, ["latitude", "longitude"]])
    for pair in [(255, 1051), (969, 1063), (120, 1204), (416, 1240), (777, 1281), (702, 1071), (984, 1604)]:
        assert after.loc[list(pair), "location_id"].nunique() == 2
    assert after.loc[1063, "operator_name"] == "University of"


@pytest.mark.parametrize("change", ["installation_count", "club_address", "shell_id", "shell_point", "supplier_identity"])
def test_venue_semantics_are_checked_after_all_hashes_are_recomputed(evidence_copy, change):
    records, config, root = evidence_copy
    if change in ("installation_count", "club_address"):
        evidence = config["groups"][6]["evidence"]
        field = "installation_file" if change == "installation_count" else "address_file"
        old, new = ("installed 12 Tesla Superchargers", "installed 24 Tesla Superchargers") if change == "installation_count" else ("20-22 Camden", "40-42 Camden")
    else:
        evidence = config["groups"][7]["evidence"]
        field = "supplier_file" if change == "supplier_identity" else "site_file"
        old, new = {"shell_id": ("10110865", "99999999"), "shell_point": ("-34.049392", "-34.149392"),
                    "supplier_identity": ("Reddy Express Mt. Annan", "Reddy Express Elsewhere")}[change]
    filename = evidence[field]
    content = (root / filename).read_text(encoding="utf-8")
    changed = content.replace(old, new)
    assert changed != content
    _repin_changed_fixture(config, root, filename, changed.encode("utf-8"))
    with pytest.raises(ValueError, match="evidence|identity|point"):
        apply_reviewed_identities(records, [], config=config, root=root)


@pytest.mark.parametrize("change", ["weaker_kind", "unknown_kind", "too_large_bound", "wrong_network", "wrong_address", "wrong_source_count", "wrong_roles"])
def test_venue_configuration_cannot_relax_or_change_reviewed_evidence(identity_source, change):
    records, config = identity_source
    group = config["groups"][6]
    if change == "weaker_kind":
        group.pop("evidence")
    elif change == "unknown_kind":
        group["evidence"]["kind"] = "nearby_points"
    elif change == "too_large_bound":
        group["max_member_distance_m"] = 10000
    elif change == "wrong_network":
        group["evidence"]["network"] = "Chargefox"
    elif change == "wrong_address":
        group["evidence"]["address"] = "Elsewhere"
    elif change == "wrong_source_count":
        group["evidence"]["source_plugs"] = 24
    else:
        group["evidence"]["installation_file"] = group["evidence"]["address_file"]
    with pytest.raises(ValueError):
        apply_reviewed_identities(records, [], config=config)
