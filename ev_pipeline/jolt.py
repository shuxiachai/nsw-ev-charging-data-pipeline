"""Parse station data embedded in the operator's public map, without JS execution."""
import json
import re
import pandas as pd
from .acquire import RAW, JOLT_URL
from .augment import match_sites
from .clean import extract_address_postcode, text


SNAPSHOT_STATUS_VALUES = {
    "networkStatus": {"available", "temporarily unavailable", "long-term unavailable"},
    "evseStatus": {"available", "occupied", "unavailable", "out of order"},
}


def snapshot_status(value, field):
    """Preserve a reported per-station state, never synthesize availability.

    These fields are used by the official map for its station card and marker.
    They describe the archived response, not today's state or the 2025 source
    period. The separate map ``status`` field (including its JS ``active``
    fallback) must not substitute for a missing network/EVSE observation.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"JOLT {field} must be a string or null")
    value = value.strip().lower()
    if value in {"", "unknown", "n/a"}:
        return None
    if value not in SNAPSHOT_STATUS_VALUES[field]:
        raise ValueError(f"Unrecognised JOLT {field}: {value!r}; inspect source semantics")
    return value


def parse_map(page):
    match = re.search(r"\bvar\s+jolt\s*=\s*", page)
    if match is None:
        raise ValueError("JOLT map data variable missing; inspect source format")
    config, _ = json.JSONDecoder().raw_decode(page[match.end():])
    points = config.get("charging_points")
    if not isinstance(points, dict) or not points:
        raise ValueError("JOLT charging_points missing/empty")
    return list(points.values())


def carpark_hours_text(address):
    """Retain an explicit carpark-hours note, not invented charger opening hours.

    The map stores notes on separate address lines. Extract only the observed
    labelled time-range form; no weekday, timezone or charger access guarantee
    is inferred. The complete original address remains in jolt_site and raw HTML.
    """
    notes = []
    for line in (address or "").splitlines():
        line = line.strip()
        match = re.fullmatch(r"Carpark open (\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", line, flags=re.I)
        if not match:
            continue
        h1, m1, h2, m2 = map(int, match.groups())
        if not (0 <= h1 <= 23 and 0 <= m1 <= 59 and 0 <= h2 <= 24 and 0 <= m2 <= 59
                and (h2 < 24 or m2 == 0)):
            raise ValueError(f"Invalid JOLT carpark-hours note: {line!r}")
        notes.append(line)
    if len(set(notes)) > 1:
        raise ValueError("Conflicting JOLT carpark-hours notes")
    return notes[0] if notes else None


def jolt_augment(locations, records):
    points = parse_map((RAW / "jolt_map.html").read_text(encoding="utf-8"))
    rows, proxy = [], []
    seen = {}
    for p in sorted(points, key=lambda x: int(x["id"])):
        jolt_id = int(p["id"])
        canonical = dict(p, id=jolt_id)
        if jolt_id in seen:
            if seen[jolt_id] != canonical:
                raise ValueError(f"Conflicting JOLT entries for station ID {jolt_id}")
            continue
        seen[jolt_id] = canonical
        if not text(p["name"]):
            raise ValueError(f"JOLT station code missing for station ID {jolt_id}")
        rows.append({"jolt_id": jolt_id, "station_code": p["name"], "description": p.get("description"),
                     "address": p["address"], "latitude": p["lat"], "longitude": p["lng"], "status_snapshot": p.get("status"),
                     "network_status_snapshot": snapshot_status(p.get("networkStatus"), "networkStatus"),
                     "evse_status_snapshot": snapshot_status(p.get("evseStatus"), "evseStatus"),
                     "carpark_hours_text": carpark_hours_text(p["address"]),
                     "source_file": "data/raw/jolt_map.html", "source_url": JOLT_URL})
        # Map addresses may have opening-hour notes on subsequent lines.
        # Never substitute a four-digit street number for a missing postcode.
        postcodes = {pc for line in p["address"].splitlines() if (pc := extract_address_postcode(line))}
        if len(postcodes) > 1:
            raise ValueError(f"Conflicting JOLT postal suffixes for station ID {jolt_id}")
        proxy.append({"ocm_id": jolt_id, "ocm_operator": "JOLT", "address": p["address"],
                      "postcode": next(iter(postcodes), ""), "latitude": p["lat"], "longitude": p["lng"], "has_dc": True})
    sites = pd.DataFrame(rows)
    proxy = pd.DataFrame(proxy)
    matches, audit = match_sites(locations, records, proxy)
    for frame in (matches, audit):
        frame.rename(columns={"ocm_id": "jolt_id"}, inplace=True)
    attrs = []
    lookup = sites.set_index("jolt_id")
    for m in matches.itertuples():
        site = lookup.loc[m.jolt_id]
        for attribute, field in [
            ("operator_station_code", "station_code"),
            ("operator_network_status_snapshot", "network_status_snapshot"),
            ("operator_evse_status_snapshot", "evse_status_snapshot"),
            ("operator_carpark_hours_text", "carpark_hours_text"),
        ]:
            if text(site[field]):
                attrs.append({"location_id": m.location_id, "attribute": attribute, "value": text(site[field]),
                              "scope": "site", "ocm_id": None, "ocm_operator_id": None, "osm_id": None, "jolt_id": m.jolt_id,
                              "source_file": "data/raw/jolt_map.html", "method": "coordinate_operator_address_match"})
    return sites, matches, audit, pd.DataFrame(attrs, columns=["location_id", "attribute", "value", "scope", "ocm_id", "ocm_operator_id", "osm_id", "jolt_id", "source_file", "method"])
