"""Evidence-backed source warnings; never change a source point or postcode.

Reviewed originals are frozen inputs. Both online and offline builds require
the archived body and metadata; restoring a missing snapshot requires the same
reviewed bytes, not a newly fetched locality assumed to be equivalent.
"""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

from pyproj import Transformer
from shapely.geometry import Point, shape

from .acquire import ROOT
from .clean import FIELDS, extract_address_postcode, identifier, text


def source_quality_issues(records, *, config=None, root=ROOT, allow_absent=False):
    """Validate complete reviewed records and return quality_issue dictionaries.

    The standalone default requires every configured observation. The cleaner
    permits absent reviews only for a short input that cannot contain their
    configured source rows (useful for independent small input fixtures).
    """
    if config is None:
        config = json.loads((Path(root) / "config/reviewed_source_issues.json").read_text(encoding="utf-8"))
    config = deepcopy(config)
    if config.get("schema_version") != 1 or config.get("source_file") != "data/raw/ev_20251216.csv":
        raise ValueError("Invalid reviewed source-quality configuration")
    date.fromisoformat(config["review_date"])
    sources = {}
    for source in config["sources"]:
        filename = source["file"]
        if filename in sources or not re.fullmatch(r"data/raw/reviewed/[A-Za-z0-9_.-]+", filename):
            raise ValueError("Invalid reviewed source-quality evidence path")
        parsed = urlparse(source["url"])
        query = parse_qs(parsed.query)
        if (parsed.scheme != "https" or parsed.netloc != "portal.spatial.nsw.gov.au"
                or parsed.path != "/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/MapServer/2/query"
                or query.get("outFields") != ["*"] or query.get("returnGeometry") != ["true"]
                or query.get("outSR") != ["7844"] or query.get("f") != ["geojson"]):
            raise ValueError("Source-quality evidence is not the complete official locality query")
        path = Path(root) / filename
        manifest_path = path.with_name(path.name + ".meta.json")
        if not path.is_file() or not manifest_path.is_file():
            raise FileNotFoundError(f"Frozen source-quality evidence missing: {filename}; restore the reviewed snapshot")
        body = path.read_bytes()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        digest = sha256(body).hexdigest()
        if (digest != source["sha256"] or manifest.get("sha256") != digest
                or len(body) != source["bytes"] or manifest.get("bytes") != len(body)
                or manifest.get("url") != source["url"] or manifest.get("method", "GET") != "GET"
                or manifest.get("status_code") != 200
                or manifest.get("retrieved_at_utc") != source["retrieved_at_utc"]):
            raise ValueError("Reviewed source-quality evidence hash/metadata mismatch")
        data = json.loads(body)
        if (data.get("type") != "FeatureCollection" or data.get("exceededTransferLimit")
                or data.get("crs", {}).get("properties", {}).get("name") != "EPSG:7844"
                or len(data.get("features", [])) != 1):
            raise ValueError("Source-quality locality geometry is incomplete or has wrong CRS")
        feature = data["features"][0]
        geometry = shape(feature["geometry"])
        if (geometry.geom_type not in ("Polygon", "MultiPolygon") or geometry.is_empty
                or not geometry.is_valid or not all(math.isfinite(v) for v in geometry.bounds)):
            raise ValueError("Invalid source-quality locality geometry")
        sources[filename] = (source, query, feature["properties"], geometry)
    rows, used_sources, review_ids, record_ids = [], set(), set(), set()
    for review in config["reviews"]:
        raw = review["raw_values"]
        if (set(raw) != set(FIELDS) or not all(isinstance(v, str) for v in raw.values())
                or identifier("r_", {k: text(v) for k, v in raw.items()}) != review["record_id"]
                or review["review_id"] in review_ids or review["record_id"] in record_ids):
            raise ValueError("Invalid or repeated source-quality review guard")
        review_ids.add(review["review_id"]); record_ids.add(review["record_id"])
        source, query, properties, geometry = sources[review["source_file"]]
        used_sources.add(review["source_file"])
        name, postcode = properties.get("suburbname"), str(properties.get("postcode"))
        if (name != review["locality_name"] or properties.get("OBJECTID") != review["locality_object_id"]
                or postcode != review["reviewed_postcode"] or not re.fullmatch(r"\d{4}", str(postcode))
                or query.get("where") != [f"suburbname='{name}'"]
                or not re.search(rf"\b{re.escape(name)}\s+NSW\s+\d{{4}}\b", text(raw["Station_address"]), re.I)
                or extract_address_postcode(raw["Station_address"]) == postcode):
            raise ValueError("Reviewed postcode/locality warning disagrees with official properties or source address")
        selected = records.loc[records.record_id.eq(review["record_id"]) | records.source_row.eq(review["source_row"])]
        if selected.empty and allow_absent and len(records) < review["source_row"] - 1:
            continue
        if len(selected) != 1:
            raise ValueError("Reviewed source-quality record is missing or ambiguous")
        row = selected.iloc[0]
        if (row.record_id != review["record_id"] or row.source_row != review["source_row"]
                or json.loads(row.raw_json) != raw or row.address != text(raw["Station_address"])
                or row.address_postcode != extract_address_postcode(raw["Station_address"])
                or float(row.latitude) != float(raw["Latitude"]) or float(row.longitude) != float(raw["Longitude"])):
            raise ValueError("Reviewed source-quality original record guard changed")
        x, y = Transformer.from_crs(4326, 7844, always_xy=True).transform(float(raw["Longitude"]), float(raw["Latitude"]))
        if not geometry.covers(Point(x, y)):
            raise ValueError("Reviewed source point is outside the official named locality")
        rows.append({"record_id": row.record_id, "source_row": int(row.source_row),
                     "code": "address_postcode_locality_mismatch", "severity": "warning",
                     "detail": (f"{review['review_id']}: source address postcode={row.address_postcode}; "
                                f"official locality {name} has reviewed_postcode={postcode}. Original address, "
                                "postcode fields and coordinates retained; this internal address warning is not a "
                                "coordinate/address_conflict decision. The original point is inside the official locality. "
                                f"Evidence={review['source_file']}#OBJECTID={properties['OBJECTID']}; "
                                f"sha256={source['sha256']}; review_date={config['review_date']}")})
    if used_sources != set(sources):
        raise ValueError("Unreferenced reviewed source-quality evidence")
    return rows
