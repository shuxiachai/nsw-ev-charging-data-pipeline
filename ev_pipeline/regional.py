"""Confirm a source site's SA4 without pretending its disputed point is resolved.

The whole pinned official locality is the conservative regional extent. Neither
source geometry nor address-conflict flags are changed by this separate audit.
"""
from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
from html import unescape
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

import geopandas as gpd
import pandas as pd
from pyproj import CRS
from shapely import to_wkb, to_wkt
from shapely.geometry import Point, shape

from .acquire import ROOT, fetch
from .clean import FIELDS, extract_address_postcode, identifier, operator, text

AUDIT_COLUMNS = [
    "review_id", "record_id", "location_id", "source_row", "source_point_sa4_code",
    "reviewed_sa4_code", "method", "locality_name", "locality_object_id",
    "locality_postcode", "locality_source_file", "operator_source_file",
    "operator_element_id", "coordinate_status", "reason", "review_date", "locality_wkt",
]
EVIDENCE_COLUMNS = ["review_id", "source_file", "role", "locator", "sha256"]
SOURCE_CSV = "data/raw/ev_20251216.csv"
LOCATION_GUARDS = {
    "location_id", "address", "operator_name", "latitude", "longitude", "postcode",
    "address_postcode", "address_conflict", "original_latitude", "original_longitude",
    "original_postcode", "original_address_conflict", "sa4_code",
}
EVIE_SITE_FIELDS = {"id", "store", "address", "city", "state", "zip", "country", "lat", "lng"}


def _review_files(config, review):
    """Each source kind keeps its own mandatory publication/evidence chain."""
    locality = review.get("locality_source_file", config["locality_source_file"])
    required = {SOURCE_CSV, locality, config["layer_source_file"], config["abs_source_file"]}
    kind = review.get("operator_kind", "nrma_kml")
    if kind == "nrma_kml":
        required.update({config["operator_page_file"], config["operator_map_file"]})
    elif kind == "evie_public_map":
        required.update({review["operator_page_file"], review["operator_script_file"], review["operator_source_file"]})
    else:
        raise ValueError("Unsupported regional operator evidence kind")
    return locality, required


def _street_tokens(value):
    # Formatting-only support for the separately reviewed intersection address.
    aliases = {"ave": "avenue", "st": "street", "rd": "road"}
    return {aliases.get(token, token) for token in re.findall(r"[a-z0-9]+", value.casefold())}


def _path(root, filename):
    if not isinstance(filename, str) or not re.fullmatch(r"data/raw/[A-Za-z0-9_./-]+", filename):
        raise ValueError("Invalid regional evidence path")
    path = (root / filename).resolve()
    if not path.is_relative_to((root / "data/raw").resolve()):
        raise ValueError("Regional evidence path escapes raw directory")
    return path


def _timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Regional source capture time must include a timezone")
    return parsed


def _configuration(root, config):
    if config is None:
        config = json.loads((root / "config/reviewed_regions.json").read_text(encoding="utf-8"))
    config = deepcopy(config)
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported regional-review configuration")
    date.fromisoformat(config["review_date"])
    if config.get("source_csv_file", SOURCE_CSV) != SOURCE_CSV:
        raise ValueError("Regional review source CSV differs from the guarded base source")
    sources = {}
    for source in config["sources"]:
        filename = source["file"]
        _path(root, filename)
        if (filename in sources or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
                or urlparse(source["url"]).scheme != "https"
                or type(source["bytes"]) is not int or source["bytes"] <= 0):
            raise ValueError("Invalid or duplicate pinned regional source")
        _timestamp(source["retrieved_at_utc"])
        sources[filename] = source
    required = {SOURCE_CSV} | {config[key] for key in ["locality_source_file", "layer_source_file", "abs_source_file",
                                                       "operator_page_file", "operator_map_file"]}
    if not required.issubset(sources):
        raise ValueError("Unpinned required regional evidence")
    for field in ["review_id", "record_id"]:
        values = [review[field] for review in config["reviews"]]
        if any(not isinstance(v, str) or not v.strip() for v in values) or len(values) != len(set(values)):
            raise ValueError("Missing or duplicate regional review/record ID")
    locations = []
    for review in config["reviews"]:
        _, review_required = _review_files(config, review)
        if not review_required.issubset(sources):
            raise ValueError("Unpinned required regional review evidence")
        operator_name = "NRMA" if review.get("operator_kind", "nrma_kml") == "nrma_kml" else "Evie"
        expected = review["expected_source"]
        if (type(expected["source_row"]) is not int or expected["source_row"] < 2
                or set(expected["raw_values"]) != set(FIELDS)
                or any(not isinstance(value, str) for value in expected["raw_values"].values())):
            raise ValueError("Regional review requires all original CSV fields")
        if not LOCATION_GUARDS.issubset(review["expected_location"]):
            raise ValueError("Regional review requires complete current/original location guards")
        locations.append(review["expected_location"]["location_id"])
        if (review["expected_location"]["address_conflict"] is not True
                or review["expected_location"]["original_address_conflict"] is not True):
            raise ValueError("Regional review must retain the unresolved coordinate conflict")
        if (not isinstance(review["locality_name"], str) or not review["locality_name"].strip()
                or type(review["locality_object_id"]) is not int
                or not re.fullmatch(r"\d{4}", str(review["locality_postcode"]))
                or not re.fullmatch(r"\d{3}", review["expected_sa4_code"])
                or not isinstance(review["reason"], str) or not review["reason"].strip()):
            raise ValueError("Invalid regional locality/code/reason guard")
        raw_address = text(expected["raw_values"]["Station_address"])
        locality_pattern = r"\b" + re.escape(review["locality_name"]).replace(r"\ ", r"\s+") + r"\b"
        if (not re.search(locality_pattern, raw_address, flags=re.I)
                or str(review["locality_postcode"]) != review["expected_location"]["address_postcode"]
                or extract_address_postcode(raw_address) != str(review["locality_postcode"])
                or raw_address != review["expected_location"]["address"]
                or operator(expected["raw_values"]["Operator"]) != operator_name
                or review["expected_location"]["operator_name"] != operator_name):
            raise ValueError("Regional locality/address/postcode/operator semantic guards disagree")
        if operator_name == "Evie":
            site = review.get("operator_expected_values", {})
            if (set(site) != EVIE_SITE_FIELDS or any(not isinstance(v, str) or not v.strip() for v in site.values())
                    or site["id"] != review["operator_element_id"]
                    or site["city"].casefold() != review["locality_name"].casefold()
                    or site["zip"] != str(review["locality_postcode"])
                    or site["state"] != "NSW" or site["country"] != "AUS"
                    or not _street_tokens(site["address"]).issubset(_street_tokens(raw_address))):
                raise ValueError("Regional Evie operator address/locality semantic guards disagree")
        keys, files = set(), set()
        for evidence in review["evidence"]:
            key = (evidence["source_file"], evidence["role"])
            if (key in keys or evidence["source_file"] not in sources
                    or not isinstance(evidence["role"], str) or not evidence["role"].strip()
                    or not isinstance(evidence["locator"], str) or not evidence["locator"].strip()):
                raise ValueError("Invalid, duplicate or unpinned regional evidence relationship")
            keys.add(key)
            files.add(evidence["source_file"])
        if not review_required.issubset(files):
            raise ValueError("Regional review evidence omits a required source relationship")
        if not any(item["role"] in {"venue_address", "venue_context"} and item["source_file"] not in review_required
                   for item in review["evidence"]):
            raise ValueError("Regional review requires a separate pinned venue address/context original")
    if len(locations) != len(set(locations)):
        raise ValueError("Multiple regional reviews target one location")
    return config, sources


def _verify_sources(root, sources):
    for filename, source in sources.items():
        path = _path(root, filename)
        if not path.is_file():
            raise FileNotFoundError(f"Regional evidence missing: {filename}")
        meta_path = path.with_name(path.name + ".meta.json")
        if not meta_path.is_file():
            raise ValueError(f"Regional evidence manifest missing: {filename}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (sha256(path.read_bytes()).hexdigest() != source["sha256"]
                or path.stat().st_size != source["bytes"]
                or any(meta.get(key) != source[key] for key in ["url", "sha256", "bytes"])
                or _timestamp(meta["retrieved_at_utc"]) != _timestamp(source["retrieved_at_utc"])
                or meta.get("status_code", 200) != 200):
            raise ValueError(f"Regional evidence source/hash/metadata mismatch: {filename}")


def acquire_regional(offline=False, *, root=ROOT, config=None):
    """Restore only approved original bytes and verify the pinned capture metadata."""
    root = Path(root)
    _, sources = _configuration(root, config)
    for filename, source in sources.items():
        fetch(source["url"], _path(root, filename), offline, expected_sha256=source["sha256"])
    _verify_sources(root, sources)


def _coordinates_valid(value):
    if not isinstance(value, (list, tuple)) or not value:
        return False
    if isinstance(value[0], (list, tuple)):
        return all(_coordinates_valid(child) for child in value)
    return (len(value) == 2 and all(type(n) in (int, float) and math.isfinite(n) for n in value)
            and -180 <= value[0] <= 180 and -90 <= value[1] <= 90)


def _localities(root, config):
    layer = json.loads(_path(root, config["layer_source_file"]).read_text(encoding="utf-8"))
    if (layer.get("error") or layer.get("name") != "Suburb" or layer.get("id") != 2
            or layer.get("geometryType") != "esriGeometryPolygon"
            or layer.get("extent", {}).get("spatialReference", {}).get("wkid") != 7844):
        raise ValueError("Regional locality layer metadata is incompatible")
    data = json.loads(_path(root, config["locality_source_file"]).read_text(encoding="utf-8"))
    if (data.get("type") != "FeatureCollection" or data.get("error") or data.get("exceededTransferLimit")
            or not isinstance(data.get("features"), list) or not data["features"]):
        raise ValueError("Regional locality response is empty or incomplete")
    crs_name = data.get("crs", {}).get("properties", {}).get("name")
    if not crs_name or CRS.from_user_input(crs_name).to_epsg() != 7844:
        raise ValueError("Regional locality requires explicit GDA2020 EPSG:7844")
    features = []
    for feature in data["features"]:
        geom = feature.get("geometry") or {}
        if (feature.get("type") != "Feature" or not isinstance(feature.get("properties"), dict)
                or geom.get("type") not in {"Polygon", "MultiPolygon"}
                or not _coordinates_valid(geom.get("coordinates"))):
            raise ValueError("Regional locality has incomplete/nonfinite polygon geometry")
        polygons = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        if any(len(ring) < 4 or ring[0] != ring[-1] for polygon in polygons for ring in polygon):
            raise ValueError("Regional locality has an incomplete, unclosed polygon ring")
        geometry = shape(geom)
        if not geometry.is_valid or geometry.is_empty or geometry.area <= 0:
            raise ValueError("Regional locality has invalid polygon geometry")
        features.append((feature["properties"], geometry))
    return features


def _operator_map(root, config, sources):
    url = sources[config["operator_map_file"]]["url"]
    parsed = urlparse(url)
    ids = parse_qs(parsed.query).get("mid", [])
    page = _path(root, config["operator_page_file"]).read_text(encoding="utf-8")
    if (parsed.hostname != "www.google.com" or len(ids) != 1
            or not re.search(r"google\.com/maps/d/[^\"<>]*mid=" + re.escape(ids[0]) + r"(?:[&\"<>]|$)", page)):
        raise ValueError("Regional NRMA page does not publish the pinned map")
    return ET.parse(_path(root, config["operator_map_file"])).getroot()


def _evie_point(root, sources, review):
    """Parse one fixed operator site through the archived public map's GET chain."""
    page_url = sources[review["operator_page_file"]]["url"]
    script_url = sources[review["operator_script_file"]]["url"]
    response_url = sources[review["operator_source_file"]]["url"]
    if any(urlparse(url).hostname != "evie.com.au" for url in [page_url, script_url, response_url]):
        raise ValueError("Regional Evie evidence must use the operator's published host")
    page = _path(root, review["operator_page_file"]).read_text(encoding="utf-8")
    script_links = [unescape(link) for link in re.findall(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"']", page, flags=re.I)]
    settings = re.search(r"var\s+wpslSettings\s*=\s*(\{.*?\});", page, flags=re.S)
    query = urlparse(response_url)
    if (script_url not in script_links or settings is None
            or query.path != "/wp-admin/admin-ajax.php"
            or parse_qs(query.query).get("action") != ["store_search"]
            or json.loads(settings.group(1)).get("ajaxurl") != query._replace(query="", fragment="").geturl()):
        raise ValueError("Regional Evie page does not publish the pinned script/GET endpoint")
    script = _path(root, review["operator_script_file"]).read_text(encoding="utf-8")
    if (not re.search(r"action\s*:\s*[\"']store_search[\"']", script)
            or not re.search(r"\bget\s*\(\s*wpslSettings\.ajaxurl\s*,", script)):
        raise ValueError("Regional Evie script does not define the public site-search GET")
    response = json.loads(_path(root, review["operator_source_file"]).read_text(encoding="utf-8"))
    if not isinstance(response, list) or not response or any(not isinstance(site, dict) for site in response):
        raise ValueError("Regional Evie site response is empty or invalid")
    selected = [site for site in response if site.get("id") == review["operator_element_id"]]
    expected = review["operator_expected_values"]
    if len(selected) != 1 or any(selected[0].get(field) != value for field, value in expected.items()):
        raise ValueError("Regional Evie site identity/address/point differs from reviewed original")
    coordinate = [float(selected[0]["lng"]), float(selected[0]["lat"])]
    if not _coordinates_valid(coordinate):
        raise ValueError("Regional Evie map contains invalid coordinates")
    return coordinate


def _guard_record(records, locations, review, raw):
    matches = records.loc[records.record_id.eq(review["record_id"])]
    if len(matches) != 1:
        raise ValueError("Regional source record is missing or duplicated")
    record = matches.iloc[0]
    expected = review["expected_source"]
    position = expected["source_row"] - 2
    original = expected["raw_values"]
    if (position >= len(raw) or raw.iloc[position].to_dict() != original
            or record.source_row != expected["source_row"] or json.loads(record.raw_json) != original
            or identifier("r_", {key: text(value) for key, value in original.items()}) != review["record_id"]):
        raise ValueError("Regional source row/ID/original fields disagree")
    selected = locations.loc[locations.location_id.eq(record.location_id)]
    if len(selected) != 1:
        raise ValueError("Regional location is missing or duplicated")
    location = selected.iloc[0]
    for field, value in review["expected_location"].items():
        actual = location[field]
        if value is None:
            equal = pd.isna(actual)
        elif isinstance(value, bool):
            equal = pd.notna(actual) and actual in (True, False) and bool(actual) is value
        elif isinstance(value, (int, float)):
            equal = pd.notna(actual) and math.isfinite(float(actual)) and float(actual) == value
        else:
            equal = pd.notna(actual) and actual == value
        if not equal:
            raise ValueError(f"Regional location guard failed: {field}")
    expected_operator = "NRMA" if review.get("operator_kind", "nrma_kml") == "nrma_kml" else "Evie"
    if location.address_conflict != True or location.operator_name != expected_operator:
        raise ValueError("Regional review requires an unchanged unresolved operator/location")
    return record, location


def regional_reviews(records, locations, regions, *, root=ROOT, config=None):
    """Return complete regional/evidence audits without modifying any inputs."""
    root = Path(root)
    config, sources = _configuration(root, config)
    _verify_sources(root, sources)
    locality_files = {config["locality_source_file"]} | {
        _review_files(config, review)[0] for review in config["reviews"]}
    localities = {filename: _localities(root, {**config, "locality_source_file": filename}) for filename in locality_files}
    kml = (_operator_map(root, config, sources)
           if any(review.get("operator_kind", "nrma_kml") == "nrma_kml" for review in config["reviews"]) else None)
    raw = pd.read_csv(_path(root, SOURCE_CSV), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if set(raw.columns) != set(FIELDS) or raw.empty:
        raise ValueError("Regional source CSV schema/rows missing")
    if (regions.crs is None or not {"sa4_code", "geometry"}.issubset(regions.columns)
            or regions.sa4_code.isna().any() or not regions.sa4_code.is_unique
            or regions.geometry.isna().any() or regions.geometry.is_empty.any()
            or not regions.geometry.is_valid.all()):
        raise ValueError("Regional ABS boundary schema/geometry is invalid")
    audits, evidence = [], []
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    for review in config["reviews"]:
        record, location = _guard_record(records, locations, review, raw)
        locality_file, _ = _review_files(config, review)
        features = localities[locality_file]
        candidates = [(props, geom) for props, geom in features if props.get("suburbname") == review["locality_name"]]
        if len(candidates) != 1:
            raise ValueError("Regional locality name is missing or ambiguous")
        props, geometry = candidates[0]
        if (props.get("OBJECTID") != review["locality_object_id"]
                or str(props.get("postcode")) != str(review["locality_postcode"])):
            raise ValueError("Regional locality ID/postcode guard failed")
        local = gpd.GeoSeries([geometry], crs=7844)
        projected = local.to_crs(regions.crs).iloc[0]
        covering = regions.loc[regions.geometry.covers(projected), "sa4_code"].tolist()
        intersecting = regions.loc[regions.geometry.intersects(projected), "sa4_code"].tolist()
        if covering != [review["expected_sa4_code"]] or intersecting != covering:
            raise ValueError("Regional complete locality is not wholly in exactly the expected SA4")
        label = review["operator_element_id"]
        if review.get("operator_kind", "nrma_kml") == "nrma_kml":
            operator_file = config["operator_map_file"]
            placemarks = [p for p in kml.findall(".//k:Placemark", ns)
                          if p.findtext("k:name", "", ns) == label]
            if (not label.startswith("NRMA ") or review["locality_name"].casefold() not in label.casefold()
                    or len(placemarks) != 1):
                raise ValueError("Regional NRMA placemark is missing, ambiguous or wrong town")
            points = placemarks[0].findall("k:Point/k:coordinates", ns)
            if len(points) != 1 or not points[0].text or len(points[0].text.split()) != 1:
                raise ValueError("Regional operator placemark must contain one point")
            coordinate = [float(value) for value in points[0].text.strip().split(",")[:2]]
            if not _coordinates_valid(coordinate):
                raise ValueError("Regional operator map contains invalid coordinates")
        else:
            operator_file = review["operator_source_file"]
            coordinate = _evie_point(root, sources, review)
        operator_point = gpd.GeoSeries([Point(coordinate)], crs=4326).to_crs(7844).iloc[0]
        if not geometry.covers(operator_point):
            raise ValueError("Regional operator point lies outside the complete locality")
        audit = dict(zip(AUDIT_COLUMNS, [
            review["review_id"], record.record_id, location.location_id, int(record.source_row),
            location.sa4_code, review["expected_sa4_code"], "official_locality_containment",
            review["locality_name"], int(review["locality_object_id"]), str(review["locality_postcode"]),
            locality_file, operator_file, label, "unresolved", review["reason"],
            config["review_date"], to_wkt(local.to_crs(4326).iloc[0], rounding_precision=-1),
        ]))
        audits.append(audit)
        for item in review["evidence"]:
            evidence.append({"review_id": review["review_id"], **item, "sha256": sources[item["source_file"]]["sha256"]})
    return pd.DataFrame(audits, columns=AUDIT_COLUMNS), pd.DataFrame(evidence, columns=EVIDENCE_COLUMNS)


def database_regional_reviews_valid(con, *, root=ROOT, config=None):
    """Recompute from original sources and current base rows, not from the ledger."""
    try:
        root = Path(root)
        config, sources = _configuration(root, config)
        records = con.execute("SELECT record_id,location_id,source_row,raw_json FROM charger_record").fetchdf()
        locations = con.execute("SELECT l.*,o.operator_name FROM location l JOIN operator o USING(operator_id)").fetchdf()
        regions = gpd.read_file(_path(root, config["abs_source_file"]))
        if regions.crs is None or not {"STE_CODE26", "SA4_CODE26", "SA4_NAME26"}.issubset(regions.columns):
            return False
        regions = regions.loc[regions.STE_CODE26.eq("1") & regions.geometry.notna() & ~regions.geometry.is_empty]
        regions = regions.rename(columns={"SA4_CODE26": "sa4_code", "SA4_NAME26": "sa4_name"}).to_crs(4326)
        expected, evidence = regional_reviews(records, locations, regions, root=root, config=config)
        for filename, source in sources.items():
            stored = con.execute("SELECT url,sha256,byte_count,retrieved_at_utc FROM source_snapshot WHERE source_file=?", [filename]).fetchall()
            if stored != [(source["url"], source["sha256"], source["bytes"], _timestamp(source["retrieved_at_utc"]))]:
                return False
        actual = con.execute("SELECT " + ",".join(AUDIT_COLUMNS[:-1]) + ",ST_AsWKB(locality_geometry) AS locality_wkb FROM reviewed_region ORDER BY review_id").fetchall()
        expected_rows = []
        from shapely import from_wkt
        for row in expected.sort_values("review_id").itertuples(index=False, name=None):
            values = list(row[:-1])
            values[-1] = date.fromisoformat(values[-1])
            expected_rows.append(tuple(values + [to_wkb(from_wkt(row[-1]))]))
        # Compare full WKB, including every island/hole; neither centroid nor area suffices.
        if actual != expected_rows:
            return False
        actual_evidence = con.execute("SELECT " + ",".join(EVIDENCE_COLUMNS) + " FROM reviewed_region_evidence ORDER BY ALL").fetchall()
        expected_evidence = sorted(evidence.itertuples(index=False, name=None))
        return actual_evidence == expected_evidence
    except Exception:
        # The validation API reports failure; the build API above raises errors.
        return False
