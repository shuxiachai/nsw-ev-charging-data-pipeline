# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Observation IDs follow evidence and meaning, independently of pandas layout."""
from datetime import datetime
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from ev_pipeline.augmentation_identity import (
    IDENTITY_FIELDS, augmentation_identifier, augmentation_identifiers,
)


SOURCE_HASH = "1234567890abcdef" * 4


def observation(**changes):
    row = dict(location_id="l_original", attribute="dc_connector_types", value="CCS (Type 2)",
               scope="site", ocm_id=7, ocm_operator_id=None, osm_id=None, jolt_id=None,
               ampol_id=None, source_file="data/raw/ocm/site.json",
               method="coordinate_operator_address_match")
    row.update(changes)
    return row


def identify(row, snapshot=SOURCE_HASH):
    return augmentation_identifier(row, source_sha256=snapshot)


@pytest.mark.parametrize("missing", [None, float("nan"), np.float32("nan"), np.float64("nan"), pd.NA, pd.NaT])
def test_null_representations_have_one_identity(missing):
    row = observation(ocm_operator_id=missing, osm_id=missing, jolt_id=missing, ampol_id=missing)
    assert identify(row) == identify(observation())


@pytest.mark.parametrize("number", [7, 7.0, np.int32(7), np.int64(7), np.uint64(7),
                                    np.float32(7), np.float64(7)])
@pytest.mark.parametrize("field", ["ocm_id", "ocm_operator_id", "jolt_id"])
def test_integral_numeric_scalars_have_one_identity(field, number):
    assert identify(observation(**{field: number})) == identify(observation(**{field: 7}))


def test_exact_numbers_preserve_precision_and_normalize_signed_zero():
    assert identify(observation(value=1.5)) == identify(observation(value=np.float32(1.5)))
    assert identify(observation(value=-0.0)) == identify(observation(value=0))
    assert identify(observation(ocm_id=2**53 + 1)) != identify(observation(ocm_id=float(2**53)))


def test_text_booleans_null_and_numbers_have_unambiguous_types():
    values = [None, "", "None", "null", "7", 7, True, False, 0, 1, 1.5, "a|b", "a,b", "a\x00b"]
    ids = [identify(observation(value=value)) for value in values]
    assert len(set(ids)) == len(values)
    assert identify(observation(value=True)) == identify(observation(value=np.bool_(True)))


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), np.float32("inf"), np.float64("-inf")])
def test_infinite_identity_values_fail_closed(value):
    with pytest.raises(ValueError, match="infinite"):
        identify(observation(ocm_id=value))


@pytest.mark.parametrize("value", [[7], {"id": 7}, b"7", Decimal("7"), datetime(2026, 9, 30)])
def test_unsupported_types_are_not_coerced_to_ambiguous_text(value):
    with pytest.raises(TypeError, match="Unsupported augmentation identity scalar"):
        identify(observation(value=value))


def test_field_order_and_unrelated_columns_do_not_change_identity_or_input():
    row = observation()
    reordered = dict(reversed(list(row.items())))
    reordered.update(augmentation_id="legacy-id", extra_metadata={"unrelated": True})
    assert identify(reordered) == identify(row)
    frame = pd.DataFrame([reordered])
    before = frame.copy(deep=True)
    assert augmentation_identifiers(frame, {row["source_file"]: SOURCE_HASH}) == [identify(row)]
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("field,changed", [
    ("location_id", "l_other"), ("attribute", "usage_type"), ("value", "CHAdeMO"),
    ("scope", "operator"), ("ocm_id", 8), ("ocm_operator_id", 8),
    ("osm_id", "node/8"), ("jolt_id", 8), ("ampol_id", "amp-8"),
    ("source_file", "data/raw/ocm/other.json"), ("method", "operator_reference"),
])
def test_every_named_identity_field_changes_the_id(field, changed):
    assert identify(observation(**{field: changed})) != identify(observation())


def test_new_snapshot_content_at_the_same_path_changes_identity():
    assert identify(observation(), "f" * 64) != identify(observation())
    assert identify(observation(), SOURCE_HASH.upper()) == identify(observation())


def test_provider_namespace_distinguishes_equal_source_record_numbers():
    rows = [observation(ocm_id=None, **{provider: 7}) for provider in ("jolt_id", "ocm_operator_id")]
    rows.append(observation(ocm_id=7))
    assert len({identify(row) for row in rows}) == 3


def test_all_provider_frames_share_the_same_post_merge_identity_path():
    rows = [
        observation(),
        observation(ocm_id=None, ocm_operator_id=7, scope="operator", source_file="data/raw/ocm_reference.json"),
        observation(ocm_id=None, osm_id="node/7", source_file="data/raw/osm_chargers.json"),
        observation(ocm_id=None, jolt_id=7, source_file="data/raw/jolt_map.html"),
        observation(ocm_id=None, ampol_id="amp-7", source_file="data/raw/ampol/site.html"),
    ]
    # Providers do not all return the same set of nullable ID columns. Concatenating
    # disjoint numeric IDs may coerce them to floats or pandas nullable scalars.
    frames = [pd.DataFrame([{key: value for key, value in row.items() if value is not None}]) for row in rows]
    combined = pd.concat(frames, ignore_index=True)
    hashes = {row["source_file"]: SOURCE_HASH for row in rows}
    result = augmentation_identifiers(combined, hashes)
    assert result == [identify(row) for row in rows]
    assert len(set(result)) == len(rows)
    assert all(value.startswith("a_v1_") and len(value) == 69 for value in result)
    reordered = combined.iloc[::-1].loc[:, list(reversed(combined.columns))]
    assert augmentation_identifiers(reordered, hashes) == list(reversed(result))
    assert combined.location_id.tolist() == ["l_original"] * len(rows)


def test_nullable_integer_dtype_does_not_change_identity():
    frame = pd.DataFrame([observation(), observation(ocm_id=None, jolt_id=8)])
    nullable = frame.copy()
    for column in ("ocm_id", "ocm_operator_id", "jolt_id"):
        nullable[column] = nullable[column].astype("Int64")
    hashes = {observation()["source_file"]: SOURCE_HASH}
    assert augmentation_identifiers(nullable, hashes) == augmentation_identifiers(frame, hashes)


def test_duplicate_observations_are_rejected_after_null_and_numeric_normalization():
    frame = pd.DataFrame([observation(), observation(ocm_id=7.0, jolt_id=pd.NA)])
    with pytest.raises(ValueError, match="Duplicate augmentation identity"):
        augmentation_identifiers(frame, {observation()["source_file"]: SOURCE_HASH})


@pytest.mark.parametrize("source_file", [None, pd.NA, float("nan"), "", "missing.json"])
def test_every_observation_requires_a_bound_source_snapshot(source_file):
    with pytest.raises(ValueError, match="source snapshot is missing"):
        augmentation_identifiers(pd.DataFrame([observation(source_file=source_file)]), {})


@pytest.mark.parametrize("snapshot", [None, pd.NA, "", "f" * 63, "x" * 64])
def test_missing_or_invalid_snapshot_hashes_are_rejected(snapshot):
    with pytest.raises(ValueError, match="source snapshot SHA-256"):
        identify(observation(), snapshot)


def test_missing_identity_columns_and_duplicate_column_names_are_rejected():
    row = observation()
    del row["scope"]
    with pytest.raises(ValueError, match="Missing augmentation identity fields: scope"):
        identify(row)
    with pytest.raises(ValueError, match="Missing augmentation identity fields: scope"):
        augmentation_identifiers(pd.DataFrame([row]), {})
    frame = pd.DataFrame([observation()])
    with pytest.raises(ValueError, match="unique column names"):
        augmentation_identifiers(pd.concat([frame, frame[["scope"]]], axis=1), {})


def test_empty_observation_frame_needs_no_snapshots():
    assert augmentation_identifiers(pd.DataFrame(columns=IDENTITY_FIELDS), {}) == []
