"""Conservative point matching plus separately identified operator enrichment."""
from difflib import SequenceMatcher
from itertools import combinations
import json
import math
import re

import geopandas as gpd
import pandas as pd
from pyproj import Geod

from .acquire import RAW
from .clean import extract_address_postcode, operator, text
from .matching_review import load_address_exceptions
from .augmentation_semantics import classify_url_attribute, operator_website_hosts, source_verified_at
from .operator_review import load_operator_reviews, usable_operator_details

GEOD = Geod(ellps="WGS84")
EMPTY_OPS = {"", "(unknown operator)", "(business owner at location)", "(non-networked)", "non-networked"}
STREET_TYPES = {
    "street": "st", "st": "st", "road": "rd", "rd": "rd",
    "avenue": "ave", "ave": "ave", "highway": "hwy", "hwy": "hwy",
    "drive": "dr", "dr": "dr", "lane": "ln", "ln": "ln",
    "parade": "pde", "pde": "pde", "way": "way",
    "crescent": "cres", "cres": "cres", "place": "pl", "pl": "pl",
    "court": "ct", "ct": "ct",
}


def address_key(value):
    value = text(value).lower()
    for long, short in STREET_TYPES.items():
        value = re.sub(r"\b" + long + r"\b", short, value)
    return re.sub(r"[^a-z0-9 ]", " ", value).split()


def address_similarity(left, right):
    # A site label may precede the street, and commas may be absent. Select the
    # first actual street component rather than comparing 'Car park' with a road.
    a = street_component(left)
    b = street_component(right)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def _street_parts(part):
    """Locate a street type after a name, not a Saint/name token after a number.

    For example, the first St in '10 St Johns Road' belongs to the name;
    treating it as the type discards Johns Road and defeats number checks.
    """
    suffix = "|".join(STREET_TYPES)
    for match in re.finditer(r"\b(" + suffix + r")\b", part, flags=re.I):
        prefix = part[:match.start()].strip()
        name = re.sub(r"^(?:(?:unit|shop|suite)\s+)?\d+[a-z]?\s*/\s*", "", prefix, flags=re.I)
        name = re.sub(r"^\d+[a-z]?(?:\s*[-–—]\s*\d+[a-z]?)?\s*", "", name, flags=re.I)
        if re.search(r"[a-z]", name, flags=re.I):
            return prefix, match.group(1).lower(), part[:match.end()]
    return None


def street_component(value, *, fallback=True):
    value = text(value)
    for part in value.split(","):
        parsed = _street_parts(part)
        if parsed:
            return " ".join(address_key(parsed[2]))
    # Ordinary proximity matching retains a label fallback. Callers making
    # coordinate corrections must explicitly require a parsed street instead.
    return " ".join(address_key(value.split(",")[0])) if fallback else ""


def _street_evidence(value):
    """Extract only simple street evidence; uncertain forms stay unknown.

    A unit prefix is not a street number. Number suffixes such as 15c do not
    establish a contradiction with 15, and a lot number is not a house number.
    Intersections and venue labels are deliberately not forced into this form.
    """
    value = text(value).lower()
    if re.search(r"\b(?:cnr|corner|intersection)\b|&", value):
        return None
    for part in value.split(","):
        parsed = _street_parts(part.strip())
        if not parsed:
            continue
        prefix, street_type, _ = parsed
        prefix = re.sub(r"^(?:(?:unit|shop|suite)\s+)?\d+[a-z]?\s*/\s*", "", prefix)
        number = re.match(r"^(\d+)[a-z]?(?:\s*[-–—]\s*(\d+)[a-z]?)?\s+(.+)$", prefix)
        interval = None
        if number:
            low = int(number.group(1))
            high = int(number.group(2) or number.group(1))
            if low <= high:
                interval = (low, high)
            prefix = number.group(3)
        # Numeric leftovers, floor/unit labels and cadastral lots cannot safely
        # establish a street identity for this extra rejection rule.
        if re.search(r"\d|\b(?:unit|shop|suite|level|floor|lot)\b", prefix):
            return None
        name = " ".join(address_key(prefix))
        name = re.sub(r"^st\b", "saint", name)
        if name:
            return name, STREET_TYPES[street_type], interval
    return None


def extended_address_conflict(left, right):
    """Find explicit address contradictions at any matching distance.

    Compare numbers only on the same named street. Different venue entrances,
    absent numbers and unparsed addresses are not proof of a conflict.
    """
    a, b = _street_evidence(left), _street_evidence(right)
    if a is None or b is None or a[0] != b[0]:
        return ""
    if a[1] != b[1]:
        return "street_type_conflict"
    if a[2] is not None and b[2] is not None:
        if a[2][1] < b[2][0] or b[2][1] < a[2][0]:
            return "house_number_conflict"
    return ""


def address_evidence_conflicts(addresses, postcodes=()):
    """Reject explicit contradictions across all supplied address observations.

    Missing/unparsed fields remain unknown. A full address and its structured
    fields must agree internally even when neither can be compared to a source
    street. Read postal suffixes only; four-digit house numbers are not postcodes.
    """
    addresses = tuple(addresses)
    conflict = next((reason for left, right in combinations(addresses, 2)
                     if (reason := extended_address_conflict(left, right))), "")
    known_postcodes = {extract_address_postcode(value) for value in addresses} - {None}
    known_postcodes.update(text(value) for value in postcodes
                           if re.fullmatch(r"\d{4}", text(value)))
    return conflict, len(known_postcodes) > 1


def acceptable_candidate(distance, same_operator, address_score, postcode_conflict, source_conflict,
                         address_evidence_conflict=False):
    if not 0 <= distance <= 250:
        return False
    if source_conflict or postcode_conflict or not same_operator or address_evidence_conflict:
        return False
    return distance <= 100 or address_score >= 0.65


def nonnegative_count(value, *, context):
    """Validate optional JSON counts before SQL INTEGER can round them.

    Zero and missing observations retain their source meaning. Fractional,
    boolean, nonnumeric, nonfinite and out-of-range values need source review.
    """
    if value is None:
        return None
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not 0 <= value <= 2_147_483_647
            or not math.isfinite(value) or int(value) != value):
        raise ValueError(f"Invalid nonnegative integer count ({context}): {value!r}")
    return int(value)


def external_data():
    ref = json.loads((RAW / "ocm_reference.json").read_text(encoding="utf-8"))
    lookup = {k: {x["ID"]: x for x in ref[k]} for k in ["Operators", "ConnectionTypes", "DataProviders", "UsageTypes", "StatusTypes"]}
    sites, connectors = [], []
    manifest = json.loads((RAW / "ocm_au_tree.json").read_text(encoding="utf-8"))
    for entry in manifest["tree"]:
        if entry["type"] != "blob" or not entry["path"].endswith(".json"):
            continue
        path = RAW / "ocm" / entry["path"]
        d = json.loads(path.read_text(encoding="utf-8"))
        a = d["AddressInfo"]
        if a.get("CountryID") != 18:
            raise ValueError(f"Non-Australian POI in AU export: {d['ID']}")
        lat, lon = a.get("Latitude"), a.get("Longitude")
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Invalid OCM coordinates: {d['ID']}")
        op = lookup["Operators"].get(d.get("OperatorID"), {})
        provider = lookup["DataProviders"].get(d.get("DataProviderID"), {})
        cs = d.get("Connections") or []
        count_context = f"{path.name}, OCM {d['ID']}"
        number_of_points = nonnegative_count(d.get("NumberOfPoints"), context=count_context + ", NumberOfPoints")
        sites.append({"ocm_id": d["ID"], "ocm_operator_id": d.get("OperatorID"), "ocm_operator": operator(op.get("Title")),
                      "title": a.get("Title"), "address": a.get("AddressLine1"), "town": a.get("Town"),
                      "postcode": text(a.get("Postcode")), "latitude": lat, "longitude": lon,
                      "usage_cost": text(d.get("UsageCost")) or None,
                      "access_comments": text(a.get("AccessComments")) or None,
                      "usage_type": lookup["UsageTypes"].get(d.get("UsageTypeID"), {}).get("Title"),
                      "status": lookup["StatusTypes"].get(d.get("StatusTypeID"), {}).get("Title"),
                      "last_verified": d.get("DateLastVerified"),
                      "last_verified_at": source_verified_at(d.get("DateLastVerified")), "number_of_points": number_of_points,
                      "data_provider": provider.get("Title"), "data_license": provider.get("License"),
                      "source_file": "data/raw/ocm/" + entry["path"], "source_url": f"https://openchargemap.org/site/poi/details/{d['ID']}",
                      "has_dc": any(c.get("CurrentTypeID") == 30 for c in cs)})
        for c in cs:
            ct = lookup["ConnectionTypes"].get(c.get("ConnectionTypeID"), {})
            status = lookup["StatusTypes"].get(c.get("StatusTypeID"), {})
            quantity = nonnegative_count(c.get("Quantity"), context=f"{count_context}, connection {c['ID']}, Quantity")
            connectors.append({"ocm_id": d["ID"], "connection_id": c["ID"], "connection_type": ct.get("Title"),
                               "current_type_id": c.get("CurrentTypeID"), "power_kw": c.get("PowerKW"), "quantity": quantity,
                               "status_type_id": c.get("StatusTypeID"), "status": status.get("Title"),
                               "is_operational": status.get("IsOperational")})
    return pd.DataFrame(sites), pd.DataFrame(connectors), ref


def match_sites(locations, records, sites, *, address_exceptions=None, additional_address_evidence=None):
    """Match candidates after all provider-specific contradiction gates.

    An optional callback returns (address conflict reason, postcode conflict)
    for a source/external row pair. It can only add rejection evidence; the
    distance, similarity, ranking and reuse rules stay common to all providers.
    """
    address_exceptions = address_exceptions or {}
    dcids = set(records.loc[records.charger_type == "DC", "location_id"])
    src = locations[locations.location_id.isin(dcids) & locations.latitude.notna() & locations.longitude.notna()].copy()
    ext = sites.loc[sites.has_dc.astype(bool)].copy()
    src = gpd.GeoDataFrame(src, geometry=gpd.points_from_xy(src.longitude, src.latitude), crs=4326)
    ext = gpd.GeoDataFrame(ext, geometry=gpd.points_from_xy(ext.longitude, ext.latitude), crs=4326)
    # Indexed, projected search followed by exact ellipsoidal distance in metres.
    candidates = gpd.sjoin(src[["location_id", "geometry"]].to_crs(3577), ext[["ocm_id", "geometry"]].to_crs(3577),
                           how="inner", predicate="dwithin", distance=300)
    src_lookup = src.set_index("location_id")
    ext_lookup = ext.set_index("ocm_id")
    evidence = []
    for c in candidates.itertuples():
        s, e = src_lookup.loc[c.location_id], ext_lookup.loc[c.ocm_id]
        _, _, dist = GEOD.inv(float(s.longitude), float(s.latitude), float(e.longitude), float(e.latitude))
        source_operator, external_operator = text(s.operator_name), text(e.ocm_operator)
        same = source_operator == external_operator and source_operator.casefold() not in EMPTY_OPS
        sim = address_similarity(s.address, e.address)
        address_conflict = extended_address_conflict(s.address, e.address)
        # Prefer postcode parsed from the address over a contradictory PCODE,
        # but contradictions in the source disqualify automatic site matching.
        pc = text(s.address_postcode) or text(s.postcode)
        pc_conflict = bool(pc and text(e.postcode) and pc != text(e.postcode))
        _, embedded_pc_conflict = address_evidence_conflicts((s.address, e.address), (pc, e.postcode))
        pc_conflict = pc_conflict or embedded_pc_conflict
        extra_conflict = ""
        if additional_address_evidence is not None:
            extra_conflict, extra_pc_conflict = additional_address_evidence(s, e)
            address_conflict = address_conflict or extra_conflict
            pc_conflict = pc_conflict or extra_pc_conflict
        exception = address_exceptions.get((c.location_id, int(c.ocm_id)), {})
        # A reviewed exception to the primary address does not waive additional
        # contradictory fields that were not covered by that exception.
        exception_applied = bool(address_conflict and not extra_conflict
                                 and exception.get("allowed_conflict") == address_conflict)
        eligible = acceptable_candidate(dist, same, sim, pc_conflict, bool(s.address_conflict),
                                        bool(address_conflict) and not exception_applied)
        evidence.append({"location_id": c.location_id, "ocm_id": int(c.ocm_id), "distance_m": dist,
                         "address_similarity": sim, "same_operator": same, "postcode_conflict": pc_conflict,
                         "source_address_conflict": bool(s.address_conflict),
                         "extended_address_conflict": address_conflict, "eligible": eligible,
                         "address_exception_applied": exception_applied,
                         "address_exception_review_id": exception.get("review_id", "") if exception_applied else "",
                         "address_exception_record_id": exception.get("record_id", "") if exception_applied else "",
                         "address_exception_source_file": exception.get("source_file", "") if exception_applied else "",
                         "address_exception_evidence_sha256": exception.get("evidence_sha256", "") if exception_applied else "",
                         "address_exception_reason": exception.get("reason", "") if exception_applied else "",
                         "score": 0.65 * max(0, 1 - dist / 300) + 0.35 * sim,
                         "decision": "candidate" if eligible else "rejected_evidence",
                         "source_address": s.address, "external_address": e.address,
                         "source_operator": s.operator_name, "external_operator": e.ocm_operator})
    columns = ["location_id", "ocm_id", "distance_m", "address_similarity", "same_operator", "postcode_conflict",
               "source_address_conflict", "extended_address_conflict", "eligible", "score", "decision", "source_address", "external_address",
               "source_operator", "external_operator", "address_exception_applied", "address_exception_review_id",
               "address_exception_record_id", "address_exception_source_file", "address_exception_evidence_sha256",
               "address_exception_reason"]
    audit = pd.DataFrame(evidence, columns=columns)
    for _, group in audit.loc[audit.eligible.astype(bool)].groupby("location_id"):
        ranked = group.sort_values(["score", "ocm_id"], ascending=[False, True])
        if len(ranked) > 1 and ranked.iloc[0].score - ranked.iloc[1].score < 0.10:
            audit.loc[ranked.index, "decision"] = "ambiguous_candidates"
        else:
            audit.loc[ranked.index, "decision"] = "lower_rank"
            audit.loc[ranked.index[0], "decision"] = "accepted"
    # Do not silently reuse one external POI for different source locations.
    accepted = audit[audit.decision == "accepted"]
    reused = accepted.ocm_id[accepted.ocm_id.duplicated(keep=False)]
    audit.loc[(audit.decision == "accepted") & audit.ocm_id.isin(reused), "decision"] = "external_poi_reused_review"
    matches = audit[audit.decision == "accepted"].copy()
    return matches, audit


def operator_details(locations, reference):
    """Lookup candidates using canonical names and documented regional aliases.

    A shared name is not independent proof of a site's operator identity.
    Reviewed assignments are withheld before these candidates are propagated.
    Operator attributes never prove site equipment, prices or current status.
    """
    rows = []
    for name in sorted(locations.operator_name.unique()):
        if name.casefold() in EMPTY_OPS:
            continue
        for op in reference["Operators"]:
            if operator(op["Title"]) != name:
                continue
            for attribute, key in [("operator_website", "WebsiteURL"), ("operator_phone", "PhonePrimaryContact")]:
                value = text(op.get(key))
                if value:
                    rows.append({"operator_name": name, "ocm_operator_id": op["ID"], "ocm_operator_title": op["Title"],
                                 "attribute": attribute, "value": value, "scope": "operator", "method": "exact_canonical_operator_name",
                                 "source_file": "data/raw/ocm_reference.json"})
    return pd.DataFrame(rows, columns=["operator_name", "ocm_operator_id", "ocm_operator_title", "attribute", "value", "scope", "method", "source_file"])


def augment(locations, records, *, issues=None):
    sites, connections, ref = external_data()
    exceptions = load_address_exceptions(locations, records, sites)
    matches, audit = match_sites(locations, records, sites, address_exceptions=exceptions)
    details = operator_details(locations, ref)
    operator_reviews = load_operator_reviews(locations, records, ref)
    details = usable_operator_details(locations, details, operator_reviews)
    website_hosts = operator_website_hosts(details)
    rows = []
    by_site = sites.set_index("ocm_id")
    for m in matches.itertuples():
        s = by_site.loc[m.ocm_id]
        # Missing quantity is not zero; an explicit zero cannot establish a
        # present connector type. Status remains a separate reported observation:
        # these names never assert that equipment is operational or available.
        dc = connections.loc[(connections.ocm_id == m.ocm_id) & (connections.current_type_id == 30)]
        names = sorted(set(dc.loc[dc.quantity.isna() | dc.quantity.gt(0), "connection_type"].dropna()) - {"Unknown"})
        attrs = {"dc_connector_types": "; ".join(names), "usage_cost_text": s.usage_cost,
                 "access_comments": s.access_comments, "usage_type": s.usage_type}
        for attribute, value in attrs.items():
            if text(value):
                scope = "site"
                if attribute == "access_comments":
                    attribute, scope = classify_url_attribute(value, s.ocm_operator, website_hosts,
                                                              original_attribute=attribute)
                rows.append({"location_id": m.location_id, "attribute": attribute, "value": text(value), "scope": scope,
                             "ocm_id": m.ocm_id, "ocm_operator_id": None, "source_file": s.source_file,
                             "method": "coordinate_operator_address_match"})
    for l in locations.itertuples():
        for d in details[details.operator_name == l.operator_name].itertuples():
            if (l.location_id, int(d.ocm_operator_id), d.attribute, d.value) in operator_reviews:
                continue
            rows.append({"location_id": l.location_id, "attribute": d.attribute, "value": d.value, "scope": "operator",
                         "ocm_id": None, "ocm_operator_id": d.ocm_operator_id, "source_file": d.source_file, "method": d.method})
    attributes = pd.DataFrame(rows, columns=["location_id", "attribute", "value", "scope", "ocm_id", "ocm_operator_id", "source_file", "method"])
    if issues is not None:
        issues.extend(operator_reviews.values())
    return sites, connections, matches, audit, details, attributes
