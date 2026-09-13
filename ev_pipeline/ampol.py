# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Site-specific AmpCharge connector observations from official Ampol pages.

Only each page's currentLocation.services.EVCharging is interpreted. Published
bay labels are retained as observations, never converted to device/plug counts,
and OPEN or a listed connector does not establish current charger availability.
"""
from datetime import datetime
from hashlib import sha256
from html import unescape
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

import pandas as pd

from .acquire import ROOT, fetch
from .augment import address_evidence_conflicts, match_sites
from .clean import operator, text


METHOD = "coordinate_operator_address_match"
SITE_COLUMNS = ["ampol_id", "guid", "name", "address", "address_raw", "postcode", "latitude", "longitude",
                "dc_connector_types", "ev_charging_json", "has_dc", "source_file", "source_url"]
ATTRIBUTE_COLUMNS = ["location_id", "attribute", "value", "scope", "ocm_id", "ocm_operator_id", "osm_id",
                     "jolt_id", "ampol_id", "source_file", "method"]


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Ampol snapshot capture time is missing")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Ampol snapshot capture time needs a timezone")
    return result


def _checked_sources(*, root=ROOT, config=None):
    """Validate the review and manifests before reading or restoring any body."""
    root = Path(root)
    if config is None:
        config = json.loads((root / "config/ampol_sources.json").read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or not isinstance(config.get("sources"), list) or not config["sources"]:
        raise ValueError("Ampol requires a nonempty versioned source manifest")
    result, filenames, urls = [], set(), set()
    for source in config["sources"]:
        filename, url = source["file"], source["url"]
        if not isinstance(filename, str) or not re.fullmatch(r"data/raw/ampol/[a-zA-Z0-9_.-]+\.html", filename):
            raise ValueError("Invalid Ampol raw source path")
        path = (root / filename).resolve()
        if not path.is_relative_to((root / "data/raw/ampol").resolve()):
            raise ValueError("Ampol source escapes its raw directory")
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "locations.ampol.com.au"
                or not re.fullmatch(r"/en/[a-z0-9-]+", parsed.path) or parsed.query or parsed.fragment):
            raise ValueError("Ampol source is not an official individual station URL")
        if filename in filenames or url in urls:
            raise ValueError("Repeated Ampol source file or station URL")
        filenames.add(filename)
        urls.add(url)
        if not isinstance(source["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
            raise ValueError("Invalid Ampol source SHA-256")
        if isinstance(source["bytes"], bool) or not isinstance(source["bytes"], int) or source["bytes"] <= 0:
            raise ValueError("Invalid Ampol source byte count")
        meta_path = path.with_name(path.name + ".meta.json")
        if not meta_path.exists():
            raise FileNotFoundError(f"Ampol manifest missing: {meta_path}; restore the supplied snapshot and manifest")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if (metadata.get("sha256") != source["sha256"] or metadata.get("bytes") != source["bytes"]
                or metadata.get("url") != url or metadata.get("resolved_url", url) != url or metadata.get("final_url", url) != url
                or metadata.get("method", "GET") != "GET" or metadata.get("status_code", 200) != 200
                or metadata.get("retrieved_at_utc") != source["retrieved_at_utc"]):
            raise ValueError(f"Ampol source bytes or provenance changed: {filename}")
        _timestamp(source["retrieved_at_utc"])
        result.append((source, path))
    return result


def load_sources(*, root=ROOT, config=None):
    """Verify exact response bytes, publisher URLs and complete capture metadata."""
    result = []
    for source, path in _checked_sources(root=root, config=config):
        body = path.read_bytes()
        if sha256(body).hexdigest() != source["sha256"] or len(body) != source["bytes"]:
            raise ValueError(f"Ampol source bytes or provenance changed: {source['file']}")
        result.append((source, body.decode("utf-8")))
    return result


def acquire_ampol(offline=False, *, root=ROOT, config=None):
    """Restore an absent fixed GET body only if the publisher returns its hash.

    The original manifest must already exist. Never generate a new capture time
    for a reviewed observation or silently replace an existing response body.
    Changed publisher bytes require a separately documented source review.
    """
    entries = _checked_sources(root=root, config=config)
    for source, path in entries:
        fetch(source["url"], path, offline=offline, expected_sha256=source["sha256"])
    return load_ampol_sites(root=root, config=config)


def _street_address(address):
    """Keep original components while ordering an explicit terminal street number.

    The publisher may encode 'Central Coast Hwy, 69-71'. This one unambiguous
    representation is rearranged for street comparison; the raw fullAddress
    and the complete response remain available. Corner/venue text is not guessed.
    """
    street, number = text(address.get("street")), text(address.get("number"))
    backwards = re.fullmatch(r"(.+?),\s*(\d+[a-zA-Z]?(?:\s*[-–—]\s*\d+[a-zA-Z]?)?)", street)
    if backwards:
        if number and number != backwards.group(2):
            raise ValueError("Ampol street and number components contradict")
        street = backwards.group(2) + " " + backwards.group(1)
    elif number:
        existing = re.match(r"^(\d+[a-zA-Z]?(?:\s*[-–—]\s*\d+[a-zA-Z]?)?)(?:\s|$)", street)
        if existing and number != existing.group(1):
            raise ValueError("Ampol street and number components require review")
        if not existing:
            street = number + " " + street
    if not street:
        raise ValueError("Ampol station has no street-address evidence")
    return ", ".join(filter(None, [street, text(address.get("locality")), text(address.get("zipCode")), "Australia"]))


def parse_page(page, *, source_file, source_url):
    """Decode one published location object without executing page JavaScript."""
    markers = list(re.finditer(r"\bcurrentLocation\s*:\s*", page))
    if len(markers) != 1:
        raise ValueError("Ampol page must contain exactly one currentLocation object")
    current, _ = json.JSONDecoder().raw_decode(page[markers[0].end():])
    if not isinstance(current, dict):
        raise ValueError("Invalid Ampol currentLocation")
    ampol_id, guid = current.get("externalId"), current.get("guid")
    if not isinstance(ampol_id, str) or not re.fullmatch(r"\d+", ampol_id):
        raise ValueError("Ampol externalId must be its original numeric string")
    if not isinstance(guid, str) or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", guid):
        raise ValueError("Ampol station GUID is missing or malformed")
    if source_url != "https://locations.ampol.com.au/en/" + text(current.get("slug")):
        raise ValueError("Ampol page URL and parsed station slug disagree")
    if not text(current.get("name")).casefold().startswith("ampol "):
        raise ValueError("Ampol page lacks its named station identity")
    address = current.get("address")
    if not isinstance(address, dict) or text(address.get("country")).casefold() not in {"au", "australia"}:
        raise ValueError("Ampol source is not an Australian station")
    latitude, longitude = address.get("latitude"), address.get("longitude")
    for value, low, high in [(latitude, -90, 90), (longitude, -180, 180)]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Ampol coordinates must be finite numeric degrees")
    postcode = text(address.get("zipCode"))
    if not re.fullmatch(r"\d{4}", postcode) or not text(address.get("locality")):
        raise ValueError("Ampol station needs explicit locality/postcode evidence")
    if not isinstance(address.get("fullAddress"), str) or not address["fullAddress"].strip():
        raise ValueError("Ampol station has no complete original address")
    services = current.get("services")
    if not isinstance(services, dict):
        raise ValueError("Ampol services must be an object")
    ev = services.get("EVCharging", [])
    if not isinstance(ev, list) or not all(isinstance(item, dict) for item in ev):
        raise ValueError("Ampol EVCharging must be a list of source observations")
    has_ampcharge = False
    connectors = set()
    for item in ev:
        facet = item.get("contentFacet")
        if not isinstance(facet, dict):
            raise ValueError("Ampol EVCharging observation lacks contentFacet")
        if item.get("externalId") == "EVChargingAmpCharge" and text(facet.get("title")) == "EV Charging (AmpCharge)":
            has_ampcharge = True
        # Only a complete published connector statement is parsed. An unknown
        # service label stays in ev_charging_json and establishes no connector.
        description = unescape(text(facet.get("longContent")))
        match = re.fullmatch(r"(CCS\s*1|CCS\s*2|CHAdeMO)(?:\s*\((\d+(?:\.\d+)?)\s*kW\))?", description, flags=re.I)
        if match:
            if match.group(2) is not None and (not math.isfinite(float(match.group(2))) or float(match.group(2)) <= 0):
                raise ValueError("Ampol connector description has invalid stated power")
            label = re.sub(r"\s+", "", match.group(1)).casefold()
            connectors.add({"ccs1": "CCS (Type 1)", "ccs2": "CCS (Type 2)", "chademo": "CHAdeMO"}[label])
    return dict(ampol_id=ampol_id, guid=guid, name=text(current["name"]), address=_street_address(address),
                address_raw=address["fullAddress"], postcode=postcode, latitude=latitude, longitude=longitude,
                dc_connector_types="; ".join(sorted(connectors)) or None,
                ev_charging_json=json.dumps(ev, ensure_ascii=False, sort_keys=True), has_dc=bool(connectors and has_ampcharge),
                source_file=source_file, source_url=source_url)


def load_ampol_sites(*, root=ROOT, config=None):
    sources = load_sources(root=root, config=config)
    rows = [parse_page(page, source_file=source["file"], source_url=source["url"]) for source, page in sources]
    sites = pd.DataFrame(rows, columns=SITE_COLUMNS).sort_values("ampol_id", ignore_index=True)
    if sites.ampol_id.duplicated().any() or sites.guid.duplicated().any():
        raise ValueError("Ampol snapshots repeat a provider station identity")
    return sites


def ampol_address_conflicts(source, external):
    """Check complete and structured evidence without replacing either value.

    Ampol's native fullAddress uses street,postcode,locality,Au. Recognize that
    complete layout explicitly, including a reversed street,number component;
    other formats still receive the shared conservative address checks.
    """
    addresses = [source.address, external.address, external.address_raw]
    postcodes = [text(source.address_postcode) or text(source.postcode), external.postcode]
    native = re.fullmatch(r"(.+),\s*(\d{4})\s*,\s*([^,]+),\s*(?:Au|Australia)",
                          text(external.address_raw), flags=re.I)
    if native:
        postcodes.append(native.group(2))
        if text(native.group(1)):
            addresses.append(_street_address({"street": native.group(1)}))
    return address_evidence_conflicts(addresses, postcodes)


def ampol_augment(locations, records, *, root=ROOT, config=None):
    sites = load_ampol_sites(root=root, config=config)
    proxy = sites[["address", "address_raw", "postcode", "latitude", "longitude", "has_dc"]].copy()
    proxy["ocm_id"] = range(1, len(sites) + 1)
    proxy["ocm_operator"] = operator("Ampol")
    mapping = dict(zip(proxy.ocm_id, sites.ampol_id))
    matches, audit = match_sites(locations, records, proxy, additional_address_evidence=ampol_address_conflicts)
    for frame in [matches, audit]:
        frame["ampol_id"] = frame.ocm_id.map(mapping)
        frame.drop(columns="ocm_id", inplace=True)
    lookup = sites.set_index("ampol_id")
    attributes = [dict(location_id=row.location_id, attribute="dc_connector_types", value=lookup.loc[row.ampol_id].dc_connector_types,
                       scope="site", ocm_id=None, ocm_operator_id=None, osm_id=None, jolt_id=None, ampol_id=row.ampol_id,
                       source_file=lookup.loc[row.ampol_id].source_file, method=METHOD) for row in matches.itertuples()]
    return sites, matches, audit, pd.DataFrame(attributes, columns=ATTRIBUTE_COLUMNS)
