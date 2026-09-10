"""Apply individually reviewed source corrections from pinned public evidence.

This is a separate stage from generic OCM/OSM matching. A reviewed source file
is immutable: changing its bytes requires a new review, not an automatic refresh.
"""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import transform

from .acquire import ROOT, fetch
from .augment import GEOD
from .clean import FIELDS, operator, text

METHOD = "coordinates_reviewed_primary_evidence"
AUDIT_COLUMNS = [
    "record_id", "source_row", "decision", "old_latitude", "old_longitude",
    "old_postcode", "new_latitude", "new_longitude", "new_postcode",
    "coordinate_source_file", "coordinate_element_id", "corroborating_source_file",
    "corroborating_element_id", "address_source_file", "evidence_distance_m",
    "coordinate_change_m", "reason", "review_date",
    "supporting_address_source_file", "supporting_address_locator",
    "corroborating_role",
]


def _source_path(root, filename):
    if not isinstance(filename, str) or not re.fullmatch(r"data/raw/[A-Za-z0-9_./-]+", filename):
        raise ValueError(f"Invalid reviewed evidence path: {filename!r}")
    path = (root / filename).resolve()
    if not path.is_relative_to((root / "data/raw").resolve()):
        raise ValueError(f"Reviewed evidence escapes raw directory: {filename}")
    return path


def _configuration(root, config):
    if config is None:
        config = json.loads((root / "config/reviewed_resolutions.json").read_text(encoding="utf-8"))
    config = deepcopy(config)
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported reviewed-resolution configuration")
    date.fromisoformat(config["review_date"])
    sources = {}
    for source in config["sources"]:
        filename = source["file"]
        _source_path(root, filename)
        if filename in sources or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
            raise ValueError("Duplicate reviewed source or invalid SHA-256")
        if urlparse(source["url"]).scheme != "https":
            raise ValueError("Reviewed sources require HTTPS URLs")
        sources[filename] = source
    ids = [entry["record_id"] for entry in config["resolutions"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate reviewed record identifier")
    publication = config["map_publication"]
    for filename in [publication["source_file"], publication["map_file"]]:
        if filename not in sources:
            raise ValueError("Unpinned map-publication evidence")
    for entry in config["resolutions"]:
        if entry["expected_source"]["operator_name"] != "NRMA":
            raise ValueError("This reviewed batch only establishes NRMA sites")
        for filename in [entry["coordinate"]["file"], entry["corroborating"]["file"], entry["address_source_file"]]:
            if filename not in sources:
                raise ValueError(f"Unpinned evidence reference: {filename}")
        support = entry.get("supporting_address_source_file")
        locator = entry.get("supporting_address_locator")
        if support is not None or locator is not None:
            if (not isinstance(support, str) or not support.strip()
                    or not isinstance(locator, str) or not locator.strip()):
                raise ValueError("Supporting address evidence requires a source and locator together")
            if support not in sources or support == entry["address_source_file"]:
                raise ValueError("Supporting address evidence must reference a distinct pinned source")
        if entry["coordinate"]["kind"] not in {"osm", "ocm"} or entry["corroborating"]["kind"] not in {"kml", "osm_landmark"}:
            raise ValueError("Unsupported reviewed coordinate/corroborating evidence kind")
        if entry["coordinate"]["kind"] == "ocm":
            reference = entry["coordinate"]
            if reference.get("operator_reference_file") not in sources:
                raise ValueError("Reviewed OCM coordinate requires pinned operator reference data")
            required_address = {"Title", "AddressLine1", "Town", "Postcode", "CountryID"}
            if set(reference.get("expected_address", {})) != required_address:
                raise ValueError("Reviewed OCM coordinate requires its complete site/address guards")
            if set(entry["expected_source"].get("raw_values", {})) != set(FIELDS):
                raise ValueError("Reviewed OCM correction requires complete original source guards")
        corroborating = entry["corroborating"]
        if corroborating["kind"] == "kml" and corroborating["file"] != publication["map_file"]:
            raise ValueError("Reviewed KML is not the published map")
        if corroborating["kind"] == "osm_landmark":
            if (entry["coordinate"]["kind"] != "ocm" or not support
                    or not entry.get("address_evidence", {}).get("pdf_page_1_based")):
                raise ValueError("Reviewed mapped landmark requires OCM and two pinned official map/address originals")
            for field, low, high in [("distance_range_m", 0, 150), ("bearing_range_deg", 0, 360)]:
                values = corroborating.get(field)
                if (not isinstance(values, list) or len(values) != 2
                        or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values)
                        or not low <= values[0] < values[1] <= high):
                    raise ValueError(f"Invalid reviewed landmark {field}")
            street = corroborating.get("street", {})
            if (not isinstance(street.get("max_distance_m"), (int, float))
                    or not 0 < street["max_distance_m"] <= 5):
                raise ValueError("Reviewed landmark requires a narrow pinned street-distance guard")
    return config, sources


def _verify_sources(root, sources):
    for filename, source in sources.items():
        path = _source_path(root, filename)
        if not path.is_file():
            raise FileNotFoundError(f"Reviewed evidence missing: {filename}; run acquire online")
        meta_path = path.with_name(path.name + ".meta.json")
        if not meta_path.is_file():
            raise ValueError(f"Reviewed evidence has no acquisition manifest: {filename}")
        manifest = json.loads(meta_path.read_text(encoding="utf-8"))
        actual = sha256(path.read_bytes()).hexdigest()
        if (manifest.get("url") != source["url"] or actual != source["sha256"]
                or manifest.get("sha256") != actual or manifest.get("bytes") != path.stat().st_size
                or not manifest.get("retrieved_at_utc")):
            raise ValueError(f"Reviewed evidence source/hash/metadata mismatch: {filename}")


def acquire_reviewed(offline=False, *, root=ROOT, config=None):
    """Retrieve or verify every review-pinned original; never revise its review hash."""
    root = Path(root)
    _, sources = _configuration(root, config)
    for filename, source in sources.items():
        fetch(source["url"], _source_path(root, filename), offline,
              expected_sha256=source["sha256"])
    _verify_sources(root, sources)


def _published_map(root, config, sources):
    publication = config["map_publication"]
    map_url = sources[publication["map_file"]]["url"]
    parsed = urlparse(map_url)
    ids = parse_qs(parsed.query).get("mid", [])
    page = _source_path(root, publication["source_file"]).read_text(encoding="utf-8")
    if (parsed.hostname != "www.google.com" or len(ids) != 1
            or not re.search(r"google\.com/maps/d/[^\"<>]*mid=" + re.escape(ids[0]) + r"(?:[&\"<>]|$)", page)):
        raise ValueError("Pinned NRMA page does not publish the reviewed KML map")


def _osm_way(data, reference, *, closed):
    """Parse the complete, individually pinned OSM way; never use a guessed centre."""
    candidates = [way for way in data.findall("way")
                  if f"way/{way.get('id')}" == reference.get("element_id")]
    if len(candidates) != 1:
        raise ValueError("Reviewed landmark/street way missing or ambiguous")
    way = candidates[0]
    tags = {tag.get("k"): tag.get("v") for tag in way.findall("tag")}
    refs = [nd.get("ref") for nd in way.findall("nd")]
    if (tags != reference.get("expected_tags") or refs != reference.get("node_refs")
            or len(refs) < (4 if closed else 2) or (closed and refs[0] != refs[-1])):
        raise ValueError("Reviewed landmark/street tags or complete geometry differ")
    nodes = {}
    for node in data.findall("node"):
        if node.get("id") in nodes:
            raise ValueError("Reviewed landmark snapshot has duplicate nodes")
        nodes[node.get("id")] = node
    coordinates = []
    for node_id in refs:
        if node_id not in nodes:
            raise ValueError("Reviewed landmark/street geometry has missing nodes")
        node = nodes[node_id]
        lon, lat = float(node.get("lon", "nan")), float(node.get("lat", "nan"))
        if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("Reviewed landmark/street contains invalid coordinates")
        coordinates.append([lon, lat])
    if coordinates != reference.get("coordinates_lon_lat"):
        raise ValueError("Reviewed landmark/street complete geometry differs")
    geometry = Polygon(coordinates) if closed else LineString(coordinates)
    if not geometry.is_valid or geometry.is_empty or (closed and geometry.area <= 0):
        raise ValueError("Reviewed landmark/street geometry is invalid")
    return geometry


def _point(root, reference, expected_operator, town, parsed):
    key = (reference["file"], reference["kind"])
    if key not in parsed:
        path = _source_path(root, reference["file"])
        parsed[key] = (json.loads(path.read_text(encoding="utf-8")) if reference["kind"] in {"osm", "ocm"}
                       else ET.parse(path).getroot())
    data = parsed[key]
    if reference["kind"] == "osm":
        if data.get("remark") or not isinstance(data.get("elements"), list):
            raise ValueError("Reviewed OSM snapshot is incomplete")
        candidates = [item for item in data["elements"]
                      if f"{item['type']}/{item['id']}" == reference["element_id"]]
        if len(candidates) != 1:
            raise ValueError("Reviewed OSM element is missing or ambiguous")
        item = candidates[0]
        tags = item.get("tags", {})
        name = operator(tags.get("operator") or tags.get("brand") or tags.get("network"))
        if tags.get("amenity") != "charging_station" or name != expected_operator:
            raise ValueError("Reviewed OSM point is not the expected operator's charging station")
        position = item if item["type"] == "node" else item.get("center", {})
        latitude, longitude = position.get("lat"), position.get("lon")
    elif reference["kind"] == "osm_landmark":
        tags = reference.get("expected_tags", {})
        if tags.get("amenity") != "police" or tags.get("building") != "yes" or not tags.get("name"):
            raise ValueError("Reviewed landmark is not the mapped named police building")
        landmark = _osm_way(data, reference, closed=True)
        latitude, longitude = landmark.centroid.y, landmark.centroid.x
    elif reference["kind"] == "ocm":
        if (reference["element_id"] != f"OCM-{data.get('ID')}"
                or data.get("OperatorID") != reference.get("operator_id")):
            raise ValueError("Reviewed OCM point ID/operator differs from its reviewed evidence")
        operator_file = reference["operator_reference_file"]
        reference_key = (operator_file, "ocm_reference")
        if reference_key not in parsed:
            parsed[reference_key] = json.loads(_source_path(root, operator_file).read_text(encoding="utf-8"))
        operators = [item for item in parsed[reference_key].get("Operators", []) if item.get("ID") == data.get("OperatorID")]
        if len(operators) != 1 or operator(operators[0].get("Title")) != expected_operator:
            raise ValueError("Reviewed OCM operator reference is missing, ambiguous or incompatible")
        address = data.get("AddressInfo", {})
        if (any(address.get(field) != value for field, value in reference["expected_address"].items())
                or text(address.get("Town")).casefold() != town.casefold()
                or address.get("CountryID") != 18):
            raise ValueError("Reviewed OCM site/address evidence disagrees")
        latitude, longitude = address.get("Latitude"), address.get("Longitude")
    else:
        ns = {"k": "http://www.opengis.net/kml/2.2"}
        candidates = [item for item in data.findall(".//k:Placemark", ns)
                      if item.findtext("k:name", default="", namespaces=ns) == reference["element_id"]]
        label = reference["element_id"]
        if len(candidates) != 1 or not label.startswith("NRMA ") or town.casefold() not in label.casefold():
            raise ValueError("Reviewed KML placemark is missing, ambiguous, or not the reviewed town")
        positions = candidates[0].findall("k:Point/k:coordinates", ns)
        if len(positions) != 1 or len(positions[0].text.split()) != 1:
            raise ValueError("Reviewed KML placemark does not contain one point")
        longitude, latitude = map(float, positions[0].text.strip().split(",")[:2])
    if (latitude is None or longitude is None or not math.isfinite(float(latitude))
            or not math.isfinite(float(longitude)) or not -90 <= float(latitude) <= 90
            or not -180 <= float(longitude) <= 180):
        raise ValueError("Invalid reviewed point coordinates")
    return float(latitude), float(longitude)


def _landmark_context(reference, coordinate, landmark, parsed):
    """Check this reviewed map relation, without treating a landmark as a charger.

    The resulting OCM point is approximate within a documented road-reserve site;
    the map and these checks do not establish a surveyed bay or side of the road.
    """
    bearing, _, distance = GEOD.inv(landmark[1], landmark[0], coordinate[1], coordinate[0])
    bearing %= 360
    low, high = reference["distance_range_m"]
    first, last = reference["bearing_range_deg"]
    if not low <= distance <= high or not first <= bearing <= last:
        raise ValueError("Reviewed mapped-landmark distance/direction disagrees")
    street_reference = reference["street"]
    if not street_reference.get("expected_tags", {}).get("highway") or not street_reference["expected_tags"].get("name"):
        raise ValueError("Reviewed landmark street is not a named road")
    street = _osm_way(parsed[(reference["file"], reference["kind"])], street_reference, closed=False)
    project = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True).transform
    distance_to_street = transform(project, Point(coordinate[1], coordinate[0])).distance(transform(project, street))
    if not math.isfinite(distance_to_street) or distance_to_street > street_reference["max_distance_m"]:
        raise ValueError("Reviewed mapped-landmark point is outside the reviewed street corridor")


def _guard(row, expected):
    if "raw_values" in expected and ("raw_json" not in row.index or json.loads(row.raw_json) != expected["raw_values"]):
        raise ValueError(f"Reviewed source guard failed for {row.record_id}: complete original fields")
    for field in ["source_row", "operator_name", "address", "address_postcode", "charger_type"]:
        if row[field] != expected[field]:
            raise ValueError(f"Reviewed source guard failed for {row.record_id}: {field}")
    for field in ["latitude", "longitude"]:
        actual = row["original_" + field]
        if pd.isna(actual) or not math.isclose(float(actual), expected[field], rel_tol=0, abs_tol=1e-10):
            raise ValueError(f"Reviewed source guard failed for {row.record_id}: original_{field}")
    if (text(row.original_postcode) != expected["postcode"] or pd.isna(row.original_address_conflict)
            or row.original_address_conflict != True):
        raise ValueError(f"Reviewed source guard failed for {row.record_id}: original postcode/conflict")


def apply_reviewed_resolutions(records, issues, *, root=ROOT, config=None):
    """Return an updated copy and audit rows after generic conflict resolution.

    All evidence and source guards are checked before applying any changes.
    Already resolved records are never overwritten, including a repeated call.
    """
    root = Path(root)
    config, sources = _configuration(root, config)
    _verify_sources(root, sources)
    _published_map(root, config, sources)
    required = {"record_id", "source_row", "operator_name", "address", "address_postcode", "charger_type",
                "latitude", "longitude", "postcode", "address_conflict", "original_latitude",
                "original_longitude", "original_postcode", "original_address_conflict", "resolution_method"}
    if not required.issubset(records.columns):
        raise ValueError("Reviewed corrections must run after generic conflict resolution")
    parsed, audit, pending_issues = {}, [], []
    result = records.copy(deep=True)
    for entry in config["resolutions"]:
        matches = result.index[result.record_id.eq(entry["record_id"])]
        if len(matches) != 1:
            raise ValueError(f"Reviewed source record missing or duplicated: {entry['record_id']}")
        index = matches[0]
        row = result.loc[index]
        expected = entry["expected_source"]
        _guard(row, expected)
        if pd.isna(row.address_conflict) or row.address_conflict not in (True, False):
            raise ValueError(f"Invalid current conflict flag: {entry['record_id']}")
        if not bool(row.address_conflict):
            continue
        # An unresolved row must still have its original values; do not conceal
        # an unrecorded intermediate correction by applying another one.
        for field in ["latitude", "longitude"]:
            if pd.isna(row[field]) or not math.isclose(float(row[field]), expected[field], rel_tol=0, abs_tol=1e-10):
                raise ValueError(f"Untracked intermediate coordinate change: {entry['record_id']}")
        if text(row.postcode) != expected["postcode"] or row.resolution_method != "unchanged":
            raise ValueError(f"Untracked intermediate resolution: {entry['record_id']}")
        coordinate = _point(root, entry["coordinate"], expected["operator_name"], entry["town"], parsed)
        corroborating = _point(root, entry["corroborating"], expected["operator_name"], entry["town"], parsed)
        distance = GEOD.inv(coordinate[1], coordinate[0], corroborating[1], corroborating[0])[2]
        if not math.isfinite(distance) or distance > 150:
            raise ValueError(f"Reviewed coordinate corroboration exceeds 150 m: {entry['record_id']}")
        role = "same_operator_charger"
        if entry["corroborating"]["kind"] == "osm_landmark":
            _landmark_context(entry["corroborating"], coordinate, corroborating, parsed)
            role = "mapped_landmark"
        moved = GEOD.inv(float(row.longitude), float(row.latitude), coordinate[1], coordinate[0])[2]
        result.loc[index, ["latitude", "longitude", "postcode", "address_conflict", "resolution_method"]] = [
            coordinate[0], coordinate[1], expected["address_postcode"], False, METHOD]
        audit.append(dict(zip(AUDIT_COLUMNS, [
            row.record_id, int(row.source_row), "resolved", float(row.latitude), float(row.longitude), text(row.postcode),
            coordinate[0], coordinate[1], expected["address_postcode"], entry["coordinate"]["file"],
            entry["coordinate"]["element_id"], entry["corroborating"]["file"], entry["corroborating"]["element_id"],
            entry["address_source_file"], distance, moved, entry["reason"], config["review_date"],
            entry.get("supporting_address_source_file"), entry.get("supporting_address_locator"),
            role,
        ])))
        pending_issues.append({"record_id": row.record_id, "source_row": int(row.source_row), "code": METHOD,
                               "severity": "info", "detail": f"Reviewed {entry['coordinate']['element_id']}; corroborating_role={role}; "
                               f"evidence_distance={distance:.2f} m; address evidence={entry['address_source_file']}; "
                               + ("OCM approximate road-reserve site position supported by official map/address and mapped landmark; "
                                  "not a second charger or surveyed bay; " if role == "mapped_landmark" else "")
                               + "original values retained"})
    issues.extend(pending_issues)
    return result, pd.DataFrame(audit, columns=AUDIT_COLUMNS)
