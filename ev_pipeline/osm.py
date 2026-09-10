"""OpenStreetMap station enrichment, attributed separately from OCM."""
import json
import math
import pandas as pd
from .acquire import RAW
from .clean import operator, text
from .augment import match_sites
from .augmentation_semantics import classify_url_attribute, operator_website_hosts

DC_SOCKETS = {"type2_combo": "CCS (Type 2)", "type1_combo": "CCS (Type 1)", "chademo": "CHAdeMO",
              "tesla_supercharger": "Tesla Supercharger", "tesla_supercharger_ccs": "Tesla CCS"}


def positive_socket(value):
    """Presence needs an explicit yes or finite positive count in any token.

    OSM can retain conflicting semicolon-separated observations. An unparsed
    token must not hide a later positive observation or make order significant.
    Raw tags remain available for any subsequent count/quality interpretation.
    """
    for token in text(value).lower().split(";"):
        token = token.strip()
        if token == "yes":
            return True
        try:
            number = float(token)
        except ValueError:
            continue
        if math.isfinite(number) and number > 0:
            return True
    return False


def osm_augment(locations, records, *, operator_details=None):
    data = json.loads((RAW / "osm_chargers.json").read_text(encoding="utf-8"))
    if data.get("remark"):
        raise ValueError("Partial Overpass output")
    rows, proxy = [], []
    for i, e in enumerate(sorted(data["elements"], key=lambda x: (x["type"], x["id"])), 1):
        tags = e["tags"]
        point = e if e["type"] == "node" else e["center"]
        op = operator(tags.get("operator") or tags.get("brand") or tags.get("network"))
        sockets = sorted(label for key, label in DC_SOCKETS.items() if positive_socket(tags.get("socket:" + key)))
        addr = " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street")]))
        osm_id = f"{e['type']}/{e['id']}"
        rows.append({"osm_id": osm_id, "name": tags.get("name"), "operator_name": op,
                     "latitude": point["lat"], "longitude": point["lon"], "address": addr,
                     "dc_connector_types": "; ".join(sockets) or None, "opening_hours": tags.get("opening_hours"),
                     "access": tags.get("access"), "fee": tags.get("fee"), "website": tags.get("website"),
                     "tags_json": json.dumps(tags, ensure_ascii=False), "source_file": "data/raw/osm_chargers.json",
                     "source_url": "https://www.openstreetmap.org/" + osm_id})
        proxy.append({"ocm_id": i, "osm_id": osm_id, "ocm_operator": op, "address": addr,
                      "postcode": tags.get("addr:postcode", ""), "latitude": point["lat"], "longitude": point["lon"],
                      "has_dc": bool(sockets) or tags.get("frequency") == "0"})
    # An empty, complete Overpass response is valid and must retain the same
    # output schema as a nonempty response (a 'remark' still fails above).
    sites = pd.DataFrame(rows, columns=["osm_id", "name", "operator_name", "latitude", "longitude", "address",
                                       "dc_connector_types", "opening_hours", "access", "fee", "website",
                                       "tags_json", "source_file", "source_url"])
    proxy = pd.DataFrame(proxy, columns=["ocm_id", "osm_id", "ocm_operator", "address", "postcode",
                                        "latitude", "longitude", "has_dc"])
    mapping = proxy.set_index("ocm_id").osm_id
    matches, audit = match_sites(locations, records, proxy)
    for frame in (matches, audit):
        frame["osm_id"] = frame.ocm_id.map(mapping)
        frame.drop(columns="ocm_id", inplace=True)
    values = []
    website_hosts = operator_website_hosts(operator_details)
    lookup = sites.set_index("osm_id")
    for m in matches.itertuples():
        s = lookup.loc[m.osm_id]
        for attr in ["dc_connector_types", "opening_hours", "access", "fee", "website"]:
            if text(s[attr]):
                attribute, scope = (classify_url_attribute(s[attr], s.operator_name, website_hosts, original_attribute=attr)
                                    if attr == "website" else (attr, "site"))
                values.append({"location_id": m.location_id, "attribute": attribute, "value": text(s[attr]), "scope": scope,
                               "ocm_id": None, "ocm_operator_id": None, "osm_id": m.osm_id,
                               "source_file": "data/raw/osm_chargers.json", "method": "coordinate_operator_address_match"})
    attrs = pd.DataFrame(values, columns=["location_id", "attribute", "value", "scope", "ocm_id", "ocm_operator_id", "osm_id", "source_file", "method"])
    return sites, matches, audit, attrs
