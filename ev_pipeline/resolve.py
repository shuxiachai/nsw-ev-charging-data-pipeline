"""Resolve source conflicts only with agreeing address and spatial evidence."""
import json
import math
import re
import pandas as pd
from .acquire import ROOT, RAW
from .clean import extract_address_postcode, operator, text
from .augment import external_data, address_similarity, extended_address_conflict, _street_parts, GEOD

AUDIT_COLUMNS = [
    "record_id", "source_row", "decision", "reason", "source_address", "old_latitude",
    "old_longitude", "old_postcode", "new_latitude", "new_longitude", "new_postcode",
    "ocm_id", "osm_id", "address_similarity", "cross_source_distance_m",
    "coordinate_change_m", "ocm_source_file",
]
LOCALITY_RELATIONSHIPS = json.loads((ROOT / "config/locality_compatibility.json").read_text(encoding="utf-8"))


def normalize_locality(value):
    """Normalize a plain locality name; venue/compound/unknown fields stay unknown."""
    value = text(value).casefold().replace(".", "")
    # A word inside a place name is not an instruction: The Entrance (and The
    # Entrance North) must remain evidence in the subsequent locality check.
    # Only explicit entrance-direction phrases are discarded here.
    entrance_instruction = (
        value == "entrance"
        or re.match(r"(?:the )?(?:main|front|rear|side|north|south|east|west|northern|southern|eastern|western) "
                    r"(?:(?:vehicle|pedestrian) )?entrance\b", value)
        or re.match(r"entrance (?:via|from|off|on|at|to|near)\b", value)
    )
    if (not re.fullmatch(r"[a-z][a-z '\-]*", value)
            or value in {"unknown", "nsw", "new south wales", "australia"}
            or entrance_instruction
            or re.search(r"\b(?:car park|parking|building|level|floor|unit|shop|suite)\b", value)):
        return None
    for abbreviation, full in [("st", "saint"), ("mt", "mount"), ("nth", "north"), ("sth", "south")]:
        value = re.sub(r"\b" + abbreviation + r"\b", full, value)
    return value


def source_locality(address):
    """Extract a NSW postal locality after a street or a separate comma field.

    A town-like word inside a street/venue name is not locality evidence. The
    function deliberately declines addresses without an explicit postal suffix.
    """
    postcode = extract_address_postcode(address)
    if postcode is None:
        return None
    value = text(address).rstrip(" ,")
    value = re.sub(r"(?:,?\s+)(?:commonwealth of\s+)?australia$", "", value,
                   flags=re.I).rstrip(" ,")
    state = r"(?:NSW|New South Wales)"
    value = re.sub(rf"(?:\b{state}\s*,?\s*{postcode}|\b{postcode}\s*,?\s*{state}|,\s*{postcode})$",
                   "", value, flags=re.I).rstrip(" ,")
    if "," in value:
        candidate = value.rsplit(",", 1)[1].strip()
    else:
        street = _street_parts(value)
        if street is None:
            return None
        candidate = value[len(street[2]):].strip()
    if _street_parts(candidate) is not None:
        return None
    return normalize_locality(candidate)


def locality_relation(source, external, source_postcode, external_postcode, latitude, longitude):
    """Different known labels require a specifically bounded reviewed relationship.

    'unverified_difference' defers a correction; it does not claim two labels
    prove different physical sites. Missing or unparsed labels remain unknown.
    """
    source, external = normalize_locality(source), normalize_locality(external)
    if source is None or external is None:
        return "unknown"
    if source == external:
        return "same"
    if LOCALITY_RELATIONSHIPS.get("schema_version") != 1:
        raise ValueError("Unsupported locality-compatibility configuration")
    for relationship in LOCALITY_RELATIONSHIPS["relationships"]:
        pair = {normalize_locality(relationship["broad_locality"]), normalize_locality(relationship["specific_locality"])}
        if {source, external} != pair:
            continue
        if text(source_postcode) != text(external_postcode) or text(source_postcode) not in relationship["postcodes"]:
            continue
        box = relationship["bbox_wgs84"]
        if (math.isfinite(float(latitude)) and math.isfinite(float(longitude))
                and box["south"] <= float(latitude) <= box["north"]
                and box["west"] <= float(longitude) <= box["east"]):
            return "reviewed_hierarchy"
    return "unverified_difference"


def resolve_conflicts(records, issues):
    records = records.copy()
    records["original_latitude"] = records.latitude
    records["original_longitude"] = records.longitude
    records["original_postcode"] = records.postcode
    records["original_address_conflict"] = records.address_conflict
    records["resolution_method"] = "unchanged"
    if not records.address_conflict.any():
        return records, pd.DataFrame(columns=AUDIT_COLUMNS)
    ocm, _, _ = external_data()
    osm = []
    for e in json.loads((RAW / "osm_chargers.json").read_text(encoding="utf-8"))["elements"]:
        t = e["tags"]
        p = e if e["type"] == "node" else e["center"]
        osm.append({"osm_id": f"{e['type']}/{e['id']}", "operator": operator(t.get("operator") or t.get("brand") or t.get("network")),
                    "lat": p["lat"], "lon": p["lon"]})
    audit = []
    for index, r in records[records.address_conflict].iterrows():
        candidates = []
        rejected_evidence = []
        source_town = source_locality(r.address)
        for e in ocm[ocm.ocm_operator == r.operator_name].itertuples():
            postcode_matches = text(e.postcode) == r.address_postcode
            town = normalize_locality(e.town)
            town_matches = bool(source_town and town and source_town == town)
            # A malformed/missing external postcode may be supported by a town;
            # a genuinely conflicting four-digit postcode cannot be ignored.
            external_pc = text(e.postcode)
            locality_agrees = postcode_matches or (town_matches and not re.fullmatch(r"\d{4}", external_pc))
            sim = address_similarity(r.address, e.address)
            if not locality_agrees or sim < 0.85:
                continue
            relation = locality_relation(source_town, town, r.address_postcode, e.postcode, e.latitude, e.longitude)
            if relation == "unverified_difference":
                rejected_evidence.append(f"OCM {e.ocm_id}: locality_not_verified ({source_town} / {town})")
                continue
            contradiction = extended_address_conflict(r.address, e.address)
            if contradiction:
                rejected_evidence.append(f"OCM {e.ocm_id}: {contradiction}")
                continue
            corroboration = []
            for s in osm:
                if s["operator"] != r.operator_name:
                    continue
                _, _, distance = GEOD.inv(e.longitude, e.latitude, s["lon"], s["lat"])
                if distance <= 150:
                    corroboration.append((distance, s["osm_id"]))
            if corroboration:
                distance, osm_id = min(corroboration)
                candidates.append((e, sim, osm_id, distance))
        if len(candidates) != 1:
            reason = f"Expected one address/locality candidate corroborated by OSM; found {len(candidates)}"
            if rejected_evidence:
                reason += "; withheld candidate evidence: " + ", ".join(sorted(set(rejected_evidence)))
            audit.append({"record_id": r.record_id, "source_row": r.source_row, "decision": "unresolved",
                          "reason": reason,
                          "source_address": r.address, "old_latitude": r.latitude, "old_longitude": r.longitude,
                          "old_postcode": r.postcode, "new_latitude": None, "new_longitude": None, "new_postcode": None,
                          "ocm_id": None, "osm_id": None, "address_similarity": None, "cross_source_distance_m": None,
                          "coordinate_change_m": None, "ocm_source_file": None})
            continue
        e, sim, osm_id, distance = candidates[0]
        _, _, moved = GEOD.inv(r.longitude, r.latitude, e.longitude, e.latitude)
        # For a postcode-only error, retain coordinates when they already agree
        # within 100m. For a displaced record, retain the externally supported point.
        newlat, newlon = (r.latitude, r.longitude) if moved <= 100 else (e.latitude, e.longitude)
        method = "postcode_verified_ocm_osm" if moved <= 100 else "coordinates_verified_ocm_osm"
        records.loc[index, ["latitude", "longitude", "postcode", "address_conflict", "resolution_method"]] = [newlat, newlon, r.address_postcode, False, method]
        audit.append({"record_id": r.record_id, "source_row": r.source_row, "decision": "resolved", "reason": method,
                      "source_address": r.address, "old_latitude": r.latitude, "old_longitude": r.longitude,
                      "old_postcode": r.postcode, "new_latitude": newlat, "new_longitude": newlon, "new_postcode": r.address_postcode,
                      "ocm_id": e.ocm_id, "osm_id": osm_id, "address_similarity": sim, "cross_source_distance_m": distance,
                      "coordinate_change_m": moved if moved > 100 else 0, "ocm_source_file": e.source_file})
        issues.append({"record_id": r.record_id, "source_row": r.source_row, "code": method, "severity": "info",
                       "detail": f"OCM {e.ocm_id}, OSM {osm_id}; address score={sim:.3f}, source agreement={distance:.1f}m; original fields retained"})
    return records, pd.DataFrame(audit, columns=AUDIT_COLUMNS)
