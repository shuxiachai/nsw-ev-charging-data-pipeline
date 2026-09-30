# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Versioned observation identities independent of pandas layout and dtypes.

Version 1 deliberately replaces the legacy positional augmentation hashes.
Record and location identifiers retain their existing, separate scheme.
"""
from collections.abc import Mapping
from hashlib import sha256
import json
from numbers import Integral
import re

import numpy as np
import pandas as pd


IDENTITY_VERSION = "augmentation-v1"
IDENTITY_FIELDS = (
    "location_id", "attribute", "value", "scope", "ocm_id", "ocm_operator_id",
    "osm_id", "jolt_id", "ampol_id", "source_file", "method",
)


def _canonical_scalar(value):
    """Encode scalar types explicitly; equal integral numbers share an encoding."""
    if value is None or value is pd.NA or value is pd.NaT:
        return ["null"]
    if isinstance(value, (bool, np.bool_)):
        return ["boolean", bool(value)]
    if isinstance(value, str):
        return ["string", value]
    if isinstance(value, Integral):
        return ["number", f"{int(value)}/1"]
    if isinstance(value, (float, np.floating)):
        if np.isnan(value):
            return ["null"]
        if not np.isfinite(value):
            raise ValueError("Augmentation identity cannot contain an infinite number")
        # Exact ratios avoid lossy integer conversion and float-format differences.
        numerator, denominator = value.as_integer_ratio()
        return ["number", f"{numerator}/{denominator}"]
    raise TypeError(f"Unsupported augmentation identity scalar: {type(value).__name__}")


def augmentation_identifier(observation: Mapping, *, source_sha256: str) -> str:
    """Hash fixed named fields and the verified source snapshot's content hash.

    Text is preserved exactly. Null sentinels are equivalent, while strings,
    booleans and numbers remain distinct. Extra fields never affect identity.
    """
    missing = [field for field in IDENTITY_FIELDS if field not in observation]
    if missing:
        raise ValueError(f"Missing augmentation identity fields: {', '.join(missing)}")
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", source_sha256):
        raise ValueError("Augmentation identity requires a source snapshot SHA-256")
    if not isinstance(observation["source_file"], str) or not observation["source_file"]:
        raise ValueError("Augmentation identity requires a nonempty source_file")
    payload = {
        "version": IDENTITY_VERSION,
        "source_sha256": source_sha256.lower(),
        "fields": {field: _canonical_scalar(observation[field]) for field in IDENTITY_FIELDS},
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "a_v1_" + sha256(encoded).hexdigest()


def augmentation_identifiers(attributes: pd.DataFrame, source_hashes: Mapping) -> list[str]:
    """Assign all providers' IDs after concatenation, rejecting duplicate identities.

    ``source_hashes`` comes from the verified source snapshot manifest. This
    function neither changes observations nor silently drops duplicate rows.
    """
    missing = [field for field in IDENTITY_FIELDS if field not in attributes.columns]
    if missing:
        raise ValueError(f"Missing augmentation identity fields: {', '.join(missing)}")
    if not attributes.columns.is_unique:
        raise ValueError("Augmentation identity requires unique column names")
    identifiers = []
    for observation in attributes.loc[:, list(IDENTITY_FIELDS)].to_dict(orient="records"):
        source_file = observation["source_file"]
        if not isinstance(source_file, str) or not source_file or source_file not in source_hashes:
            raise ValueError(f"Augmentation source snapshot is missing: {source_file!r}")
        identifiers.append(augmentation_identifier(observation, source_sha256=source_hashes[source_file]))
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate augmentation identity after canonicalization")
    return identifiers
