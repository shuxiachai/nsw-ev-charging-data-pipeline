# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Conservative cleaning: preserve evidence, do not invent missing measurements."""
from hashlib import sha256
import json
import math
import re
import unicodedata

import geopandas as gpd
import pandas as pd

from .acquire import ROOT, RAW

ALIASES = json.loads((ROOT / "config/operator_aliases.json").read_text(encoding="utf-8"))
FIELDS = ["OBJECTID", "Station_name", "Station_address", "Operator", "Number_of_plugs",
          "Charger_Type", "Charger_rating", "Latitude", "Longitude", "LGANAME", "PCODE", "Source"]


def text(value):
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value))).strip()


def operator(value):
    """Use reviewed display names; unknown names have a stable casefold spelling.

    The same case-insensitive identity must never yield two operator-table names.
    Canonical spelling comes from configuration, not the first source row seen.
    """
    value = text(value)
    return ALIASES.get(value.casefold(), value.casefold())


def identifier(prefix, values):
    return prefix + sha256(json.dumps(values, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]


def address_identity(value):
    """Normalize presentation and optional postal suffixes at the same point.

    Slashes, hyphens, floor labels and other address content remain significant;
    this is not fuzzy address matching or nearby-coordinate clustering.
    """
    value = text(text(value).replace(",", " ")).casefold()
    value = re.sub(r"\s+(?:commonwealth of\s+)?australia$", "", value)
    return re.sub(r"\bnsw\s+\d{4}$", "nsw", value)


def _power_details(value):
    """Parse ratings and explicit configuration counts with one complete grammar.

    A multiplier establishes a configuration expression; unmultiplied terms in
    that expression each contribute one. Bare ratings without any multiplier do
    not establish a site's plug count.
    """
    value = text(value).lower().replace("\N{MINUS SIGN}", "-")
    number = r"-?\d+(?:\.\d+)?"
    term = rf"(?:(\d+)\s*[x×]\s*)?({number})\s*kw"
    # Validate the whole expression before extracting values. A partial match
    # would turn 1,250 kW into 250, 1e2 kW into 2, or a range into one endpoint.
    if re.fullmatch(number, value):
        terms = [("", value)]
    elif re.fullmatch(rf"{term}(?:\s*[&+/;]\s*{term})*", value):
        terms = re.findall(term, value)
        if any(quantity and int(quantity) <= 0 for quantity, _ in terms):
            return None, None, "invalid", None
    else:
        return None, None, "unknown", None
    values = [float(rating) for _, rating in terms]
    if any(not math.isfinite(n) or n <= 0 for n in values):
        return None, None, "invalid", None
    configured = (sum(int(quantity) if quantity else 1 for quantity, _ in terms)
                  if any(quantity for quantity, _ in terms) else None)
    return min(values), max(values), "multiple" if len(values) > 1 else "single", configured


def power(value):
    """Return individual-plug min/max; never sum kW into an invented site rating."""
    return _power_details(value)[:3]


def extract_address_postcode(value):
    """Read an explicit postal suffix, never a four-digit street or unit number.

    The source uses a state/postcode pair in either order, or a comma-delimited
    postcode field. Unsupported address/remark formats remain unknown.
    """
    value = text(value).rstrip(" ,")
    value = re.sub(r"(?:,?\s+)(?:commonwealth of\s+)?australia$", "", value,
                   flags=re.I).rstrip(" ,")
    state = (r"(?:NSW|New South Wales|VIC|Victoria|QLD|Queensland|SA|South Australia|"
             r"WA|Western Australia|TAS|Tasmania|ACT|Australian Capital Territory|NT|Northern Territory)")
    for pattern in [rf"\b{state}\s*,?\s*(\d{{4}})$",
                    rf"\b(\d{{4}})\s*,?\s*{state}$", r",\s*(\d{4})$"]:
        match = re.search(pattern, value, flags=re.I)
        if match:
            return match.group(1)
    return None


def load_clean():
    raw = pd.read_csv(RAW / "ev_20251216.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if set(raw.columns) != set(FIELDS):
        raise ValueError(f"TfNSW schema changed: {list(raw.columns)}")
    if raw.empty:
        raise ValueError("TfNSW source contains no charger records")
    cleaned, issues, duplicates = [], [], []
    seen = set()
    for i, row in raw.iterrows():
        original = row.to_dict()
        r = {k: text(v) for k, v in original.items()}
        rid = identifier("r_", r)
        if rid in seen:
            duplicates.append({"source_row": i + 2, "record_id": rid, "reason": "identical_normalized_row"})
            continue
        seen.add(rid)
        def flag(code, detail, severity="warning"):
            issues.append({"record_id": rid, "source_row": i + 2, "code": code, "severity": severity, "detail": detail})
        lat, lon = pd.to_numeric(r["Latitude"], errors="coerce"), pd.to_numeric(r["Longitude"], errors="coerce")
        valid = pd.notna(lat) and pd.notna(lon) and -90 <= lat <= 90 and -180 <= lon <= 180
        if not valid:
            flag("invalid_coordinates", "Coordinates are nonnumeric or outside global bounds", "error")
            lat = lon = None
        op = operator(r["Operator"])
        if op != r["Operator"]:
            flag("operator_normalized", f"{r['Operator']} -> {op}", "info")
        if r["Operator"].casefold() in {"fast cities a", "energy austra", "university of"}:
            flag("operator_label_review_required", f"Source operator label {r['Operator']!r} is incomplete or ambiguous; retained without guessing a company/network expansion. Review the individual site before interpreting this label as a distinct operator.")
        if not r["OBJECTID"]:
            flag("missing_source_id", "Stable content-based record/location identifiers generated", "info")
        if not r["Station_name"]:
            flag("missing_station_name", "Name remains null; address is the display fallback", "info")
        lo, hi, kind, configured = _power_details(r["Charger_rating"])
        if kind in ("unknown", "invalid"):
            flag("power_unavailable", f"Preserved unparseable rating: {r['Charger_rating']}")
        plugs = pd.to_numeric(r["Number_of_plugs"], errors="coerce")
        if pd.isna(plugs) or plugs <= 0 or plugs % 1:
            flag("invalid_plug_count", r["Number_of_plugs"], "error")
            plugs = None
        else:
            plugs = int(plugs)
        if configured is not None and plugs is not None and configured != plugs:
            flag("configuration_count_disagreement", f"Rating configuration count={configured}, Number_of_plugs={plugs}; units may differ, both values retained")
        ctype = r["Charger_Type"].upper()
        if ctype not in ("AC", "DC", "UPCOMING"):
            flag("unknown_charger_type", r["Charger_Type"], "error")
            ctype = "UNKNOWN"
        pc_match = re.fullmatch(r"(?:NSW\s+)?(\d{4})", r["PCODE"], flags=re.I)
        postcode = pc_match.group(1) if pc_match else None
        if postcode and postcode != r["PCODE"]:
            flag("postcode_normalized", f"{r['PCODE']} -> {postcode}", "info")
        address_postcode = extract_address_postcode(r["Station_address"])
        conflict = bool(postcode and address_postcode and postcode != address_postcode)
        if conflict:
            flag("postcode_address_conflict", f"Source PCODE={postcode}, address postcode={address_postcode}; no automatic coordinate correction")
        if not postcode:
            flag("missing_or_invalid_postcode", "Source postcode retained as null; address candidate stored separately")
        if not r["LGANAME"]:
            flag("missing_lga", "No LGA inference from SA4 (different geographical level)")
        if not r["Source"]:
            flag("missing_source_category", "Charger operational status cannot be confirmed from source category")
        locid = identifier("l_", [address_identity(r["Station_address"]), op.casefold(),
                                  round(float(lat), 6) if valid else r["Latitude"],
                                  round(float(lon), 6) if valid else r["Longitude"]])
        cleaned.append({"record_id": rid, "location_id": locid, "source_row": i + 2,
                        "source_objectid": r["OBJECTID"] or None, "station_name": r["Station_name"] or None,
                        "address": r["Station_address"], "operator_name": op, "operator_id": identifier("o_", op.casefold()),
                        "latitude": lat, "longitude": lon, "postcode": postcode,
                        "address_postcode": address_postcode, "address_conflict": conflict,
                        "lga": r["LGANAME"] or None, "charger_type": ctype, "number_of_plugs": plugs,
                        "power_min_kw": lo, "power_max_kw": hi, "power_kind": kind,
                        "power_raw": r["Charger_rating"], "source_category": r["Source"] or None,
                        "raw_json": json.dumps(original, ensure_ascii=False)})
    records = pd.DataFrame(cleaned)
    from .source_quality import source_quality_issues
    issues.extend(source_quality_issues(records, allow_absent=True))
    for lid, group in records.groupby("location_id"):
        if len(group) > 1:
            postcodes = sorted(set(group.postcode.dropna()) | set(group.address_postcode.dropna()))
            if len(postcodes) > 1:
                records.loc[group.index, "address_conflict"] = True
                for r in group.itertuples():
                    issues.append({"record_id": r.record_id, "source_row": r.source_row,
                                   "code": "cross_record_postcode_conflict", "severity": "warning",
                                   "detail": f"Location {lid} has conflicting known postcodes {postcodes}; all records flagged"})
            conflicts = [c for c in ["charger_type", "number_of_plugs", "power_raw", "source_category"] if group[c].nunique(dropna=False) > 1]
            for r in group.itertuples():
                issues.append({"record_id": r.record_id, "source_row": r.source_row, "code": "multiple_records_one_location",
                               "severity": "warning", "detail": f"{len(group)} source records share location {lid}; differences={conflicts}; do not sum plug counts across these records"})
    return raw, records, issues, pd.DataFrame(duplicates, columns=["source_row", "record_id", "reason"])


def location_representatives(records):
    """Choose the most complete source row without mixing its provenance fields.

    Retain first-location order; source row breaks completeness ties. All source
    observations remain in charger_record, including conflicting attributes.
    """
    from .identity import reviewed_identity_groups

    order = records.location_id.drop_duplicates()
    reviewed = reviewed_identity_groups(records)
    ranked = records.assign(_metadata_count=records[["station_name", "postcode", "lga"]].notna().sum(axis=1))
    ranked["_reviewed_representative"] = records.record_id.eq(records.location_id.map(reviewed))
    ranked = ranked.sort_values(["_reviewed_representative", "_metadata_count", "source_row"],
                                ascending=[False, False, True], kind="stable")
    chosen = ranked.drop_duplicates("location_id").set_index("location_id").loc[order].reset_index()
    return chosen[records.columns].copy()


def flag_final_location_conflicts(records, issues):
    """Preserve group conflicts after individual source corrections, in place.

    Resolving each row does not prove that all rows sharing an original
    location identity still agree. Compare their final observations before a
    representative hides differences. Keep all original and resolution fields.
    """
    from .identity import reviewed_identity_groups

    reviewed = reviewed_identity_groups(records)
    for lid, group in records.groupby("location_id"):
        if len(group) < 2:
            continue
        postcodes = sorted({text(value) for column in ["postcode", "address_postcode"]
                            for value in group[column] if text(value)})
        points = sorted({(round(float(row.latitude), 6), round(float(row.longitude), 6))
                         for row in group.itertuples()
                         if pd.notna(row.latitude) and pd.notna(row.longitude)})
        if len(postcodes) <= 1 and (len(points) <= 1 or lid in reviewed):
            continue
        records.loc[group.index, "address_conflict"] = True
        detail = (f"Location {lid} has inconsistent final observations: postcodes={postcodes}, "
                  f"coordinate_keys={points}; all source records remain conflicting after individual resolutions")
        for row in group.itertuples():
            issues.append({"record_id": row.record_id, "source_row": row.source_row,
                           "code": "post_resolution_location_conflict", "severity": "warning", "detail": detail})


def spatial_assign(records, issues, coastal_tolerance_m=50):
    regions = gpd.read_file(RAW / "SA4_2026_AUST_SHP_GDA2020.zip")
    required = {"SA4_CODE26", "SA4_NAME26", "STE_CODE26", "geometry"}
    if not required.issubset(regions.columns) or regions.crs is None:
        raise ValueError("ABS schema/CRS missing")
    regions = regions.loc[(regions.STE_CODE26 == "1") & regions.geometry.notna() & ~regions.geometry.is_empty].copy()
    if not regions.geometry.is_valid.all():
        raise ValueError("Invalid ABS boundary geometry; inspect source before repairing")
    regions = regions.rename(columns={"SA4_CODE26": "sa4_code", "SA4_NAME26": "sa4_name"})
    flag_final_location_conflicts(records, issues)
    loc = location_representatives(records)
    valid = loc.latitude.notna() & loc.longitude.notna()
    points = gpd.GeoDataFrame(loc.loc[valid, ["location_id", "latitude", "longitude"]].copy(),
                             geometry=gpd.points_from_xy(loc.loc[valid, "longitude"], loc.loc[valid, "latitude"]), crs=4326)
    joined = gpd.sjoin(points.to_crs(regions.crs), regions[["sa4_code", "geometry"]], how="left", predicate="intersects")
    assignment = {}
    for lid, group in joined.groupby("location_id"):
        codes = group.sa4_code.dropna().unique()
        assignment[lid] = (codes[0], "point_in_polygon", 0.0) if len(codes) == 1 else (None, "ambiguous" if len(codes) > 1 else "unmatched", None)
    # A coastal point may lie just outside the coastline polygon. Preserve its
    # coordinates and explicitly label a bounded nearest-region approximation.
    missed = points[points.location_id.map(lambda k: assignment[k][1] == "unmatched")]
    if len(missed):
        near = gpd.sjoin_nearest(missed.to_crs(3577), regions[["sa4_code", "geometry"]].to_crs(3577),
                                how="left", max_distance=coastal_tolerance_m, distance_col="distance_m")
        for lid, group in near.groupby("location_id"):
            codes = group.sa4_code.dropna().unique()
            if len(codes) == 1:
                distance_m = float(group.distance_m.min())
                if math.isfinite(distance_m) and 0 <= distance_m <= coastal_tolerance_m:
                    # Retain full precision for eligibility; report metres to six
                    # decimals so projection round-off does not change exports.
                    assignment[lid] = (codes[0], "coastal_nearest_within_50m", round(distance_m, 6))
    for r in loc.itertuples():
        a = assignment.get(r.location_id, (None, "invalid_coordinates", None))
        if a[1] != "point_in_polygon":
            issues.append({"record_id": r.record_id, "source_row": r.source_row, "code": "spatial_" + a[1],
                           "severity": "warning" if a[0] else "error", "detail": f"SA4={a[0]}, distance_m={a[2]}; original point retained"})
    loc["sa4_code"] = loc.location_id.map(lambda k: assignment.get(k, (None,))[0])
    loc["sa4_method"] = loc.location_id.map(lambda k: assignment.get(k, (None, "invalid_coordinates"))[1])
    loc["sa4_distance_m"] = loc.location_id.map(lambda k: assignment.get(k, (None, None, None))[2])
    loc["address_conflict"] = loc.location_id.map(records.groupby("location_id").address_conflict.any())
    return loc, regions.to_crs(4326)
