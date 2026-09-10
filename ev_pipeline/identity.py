"""Apply individually reviewed location identities without changing observations.

This is an explicit source-record mapping, not a proximity clustering rule.
Every exception is bound to the complete reviewed membership and original values.
"""
from copy import deepcopy
from datetime import date
from hashlib import sha256
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re

import pandas as pd

from .acquire import ROOT
from .augment import GEOD
from .clean import FIELDS, address_identity, extract_address_postcode, identifier, operator, text

AUDIT_COLUMNS = [
    "record_id", "source_row", "review_id", "original_location_id", "location_id",
    "representative_record_id", "source_file", "reason", "review_date",
]
LEDGER_ATTRIBUTE = "reviewed_location_identities"
EVIDENCE_COLUMNS = ["review_id", "source_file", "role", "element_id", "sha256"]
COUNCIL_VENUE_KINDS = {"cowell_evie_council_venue", "parraween_evie_council_venue"}
VENUE_KINDS = {"campbelltown_tesla_venue", "mount_annan_viva_venue"} | COUNCIL_VENUE_KINDS
VENUE_URLS = {
    "campbelltown_installation": "https://visitcampbelltown.com.au/tesla-ev-charging-station-campbelltown-catholic-club/",
    "campbelltown_address": "https://cathclub.com.au/contact/",
    "mount_annan_site": "https://find.shell.com/au/fuel/10110865-shell-reddy-express-mount-annan/en_AU",
    "mount_annan_supplier": "https://www.switchdin.com/resources/ultrafast-ev-chargers-live-in-an-australian-first",
    "cowell_council_proposal": "https://connect.huntershill.nsw.gov.au/electric-vehicle-charging-proposal",
    "cowell_council_operation": "https://connect.huntershill.nsw.gov.au/ev/widgets/464182/faqs",
    "parraween_council_installation": "https://www.northsydney.nsw.gov.au/news/article/310/north-sydney-powers-up-with-60-new-ev-charging-stations",
    "parraween_council_carpark": "https://www.northsydney.nsw.gov.au/directory-record/134/parraween-street-car-park-cremorne",
}


def _configuration(config, root=ROOT):
    if config is None:
        config = json.loads((Path(root) / "config/reviewed_identities.json").read_text(encoding="utf-8"))
    config = deepcopy(config)
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported reviewed-identity configuration")
    date.fromisoformat(config["review_date"])
    if config["source_file"] != "data/raw/ev_20251216.csv":
        raise ValueError("Reviewed identities must reference the TfNSW source")
    seen_reviews, seen_records, seen_locations = set(), set(), set()
    for group in config["groups"]:
        date.fromisoformat(group.get("review_date", config["review_date"]))
        if group["review_id"] in seen_reviews or not group["reason"] or len(group["members"]) < 2:
            raise ValueError("Duplicate review ID, missing reason, or incomplete identity group")
        seen_reviews.add(group["review_id"])
        members = group["members"]
        for member in members:
            raw = member["raw_values"]
            if set(raw) != set(FIELDS) or not all(isinstance(v, str) for v in raw.values()):
                raise ValueError("Reviewed identity requires every original CSV field")
            if member["record_id"] in seen_records or member["source_row"] < 2:
                raise ValueError("Repeated reviewed record or invalid source row")
            seen_records.add(member["record_id"])
            normalized = {key: text(value) for key, value in raw.items()}
            if identifier("r_", normalized) != member["record_id"]:
                raise ValueError("Reviewed raw values do not produce the reviewed record ID")
        representative = [m for m in members if m["record_id"] == group["representative_record_id"]]
        if len(representative) != 1:
            raise ValueError("Reviewed representative must be one original group member")
        group["location_id"] = representative[0]["original_location_id"]
        # This bound validates only the explicit reviewed membership. It never
        # discovers or merges another nearby record.
        venue = group.get("evidence", {}).get("kind") in VENUE_KINDS
        bound = group.get("max_member_distance_m", 1) if venue else 1
        if not isinstance(bound, (float, int)) or isinstance(bound, bool) or not 0 < bound <= 120:
            raise ValueError("Invalid reviewed venue membership distance bound")
        for a in members:
            for b in members:
                ar, br = a["raw_values"], b["raw_values"]
                distance = GEOD.inv(float(ar["Longitude"]), float(ar["Latitude"]),
                                    float(br["Longitude"]), float(br["Latitude"]))[2]
                if not math.isfinite(distance) or distance >= bound:
                    raise ValueError("Reviewed identity observations exceed the individually reviewed distance bound")
        if group["location_id"] in seen_locations:
            raise ValueError("Reviewed identity groups share a target location")
        seen_locations.add(group["location_id"])
    return config


def _evidence_path(root, filename):
    if not isinstance(filename, str) or not re.fullmatch(r"data/raw/reviewed/[A-Za-z0-9_.-]+", filename):
        raise ValueError("Invalid reviewed identity evidence path")
    path = (Path(root) / filename).resolve()
    if not path.is_relative_to((Path(root) / "data/raw/reviewed").resolve()):
        raise ValueError("Reviewed identity evidence escapes raw directory")
    return path


class _LocationDetail(HTMLParser):
    """Read the published heading and address, including nested inline markup."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.headings, self.paragraphs = [], []
        self.active = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h2", "p") and self.active is None:
            self.active, self.parts = tag, []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == self.active:
            (self.headings if tag == "h2" else self.paragraphs).append(text("".join(self.parts)))
            self.active = None


class _PublishedHTML(HTMLParser):
    """Read visible page text and JSON-LD without adding an HTML dependency."""
    def __init__(self, payload):
        super().__init__(convert_charrefs=True)
        self.parts, self.jsonld, self.script_parts = [], [], []
        self.hidden = None
        self.ld = False
        self.feed(payload)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden = tag
            self.ld = tag == "script" and dict(attrs).get("type") == "application/ld+json"
            self.script_parts = []

    def handle_data(self, data):
        if self.hidden is None:
            self.parts.append(data)
        elif self.ld:
            self.script_parts.append(data)

    def handle_endtag(self, tag):
        if tag == self.hidden:
            if self.ld:
                self.jsonld.append(json.loads("".join(self.script_parts)))
            self.hidden, self.ld = None, False

    @property
    def visible(self):
        return text(" ".join(self.parts))


class _TableRows(HTMLParser):
    """Keep published table cells together so another site's count cannot leak in."""
    def __init__(self, payload):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None
        self.feed(payload)

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(text(" ".join(self.cell)))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row, self.cell = None, None


def _council_venue_evidence(group, sources, payloads):
    """Two fixed Council carparks, with no Sydney/suburb or nearby-point rule."""
    evidence = group["evidence"]
    cowell = evidence["kind"] == "cowell_evie_council_venue"
    expected = ({"proposal_file": "cowell_council_proposal", "operation_file": "cowell_council_operation"}
                if cowell else {"installation_file": "parraween_council_installation", "carpark_file": "parraween_council_carpark"})
    pages = {}
    for field, provider in expected.items():
        filename = evidence[field]
        if filename not in sources or sources[filename].get("provider") != provider:
            raise ValueError("Reviewed Council venue evidence roles disagree")
        pages[field] = _PublishedHTML(payloads[filename]).visible
    if cowell:
        if ("Council endorsed the installation of our first Electric Vehicle charging station in the Council carpark at 3A Cowell St, Gladesville." not in pages["proposal_file"]
                or "Evie Networks for the installation of a fast charger at 3A Cowell St, Gladesville within the carpark" not in pages["proposal_file"]
                or "The proposal is for 1 x charger with 2 x charging bays." not in pages["proposal_file"]
                or "NSW EV Kerbside Charging Grants (Round 1)" not in pages["proposal_file"]
                or "only 1 public charger available in the Hunters Hill LGA (Cowell St carpark, Gladesville, owned and operated by Evie)" not in pages["operation_file"]):
            raise ValueError("Reviewed Cowell Council address/operator/two-bay evidence changed")
        address, old_address, postcode, plugs = "3A Cowell St Gladesville NSW 2111 Australia", "3A Cowell St, Sydney, 2111", "2111", 2
        old_row, new_row = 512, 1528
        rows = [(evidence["proposal_file"], "council_venue_proposal", "4 March 2025 update;3A Cowell St;1 charger/2 bays"),
                (evidence["operation_file"], "council_venue_operation", "Background;Cowell St carpark;Evie")]
    else:
        table_rows = _TableRows(payloads[evidence["installation_file"]]).rows
        selected = [row for row in table_rows if row and row[0] == "Parraween Street, Cremorne (Evie)"]
        if (selected != [["Parraween Street, Cremorne (Evie)", "4", "75kW DC fast charger"]]
                or "Parraween Street car park, Cremorne" not in pages["carpark_file"]
                or "Address Parraween Street, Cremorne, 2090" not in pages["carpark_file"]
                or "Two dual 75kW DC fast chargers (four charging bays) operated by Evie" not in pages["carpark_file"]):
            raise ValueError("Reviewed Parraween Council address/operator/four-bay evidence changed")
        address, old_address, postcode, plugs = "106 Parraween St Cremorne NSW 2090 Australia", "106 Parraween St, Sydney, 2090", "2090", 4
        old_row, new_row = 69, 1861
        rows = [(evidence["installation_file"], "council_venue_installation", "Car park table;Parraween Street, Cremorne (Evie)"),
                (evidence["carpark_file"], "council_venue_operation", "Directory 134;Address;Electric charging bays")]
    if (evidence.get("address") != address or evidence.get("network") != "Evie"
            or evidence.get("source_plugs") != plugs or group.get("max_member_distance_m", 1) > 20):
        raise ValueError("Reviewed Council venue configuration disagrees with its evidence")
    expected_members = {
        (old_row, address_identity(old_address), "Existing Fast Chargers"),
        (new_row, address_identity(address), "Kerbside Charging R1"),
    }
    actual_members = set()
    for member in group["members"]:
        raw = member["raw_values"]
        actual_members.add((member["source_row"], address_identity(raw["Station_address"]), raw["Source"]))
        if (operator(raw["Operator"]) != "Evie" or raw["Charger_Type"] != "DC"
                or raw["Number_of_plugs"] != str(plugs) or raw["Charger_rating"] != "75 kW"
                or raw["PCODE"] != postcode):
            raise ValueError("Reviewed Council venue evidence disagrees with source observations")
    if len(group["members"]) != 2 or actual_members != expected_members:
        raise ValueError("Reviewed Council venue membership/address/source categories changed")
    return rows


def _venue_evidence(group, sources, payloads):
    """Individual venue reviews, not a reusable proximity-based discovery rule.

    Addresses, network and charger class are corroborated by published originals.
    Every member/coordinate is still guarded separately; equipment observations
    and their differing power ratings are retained, never added together.
    """
    evidence = group["evidence"]
    kind = evidence["kind"]
    if kind in COUNCIL_VENUE_KINDS:
        return _council_venue_evidence(group, sources, payloads)
    expected = ({"installation_file": "campbelltown_installation", "address_file": "campbelltown_address"}
                if kind == "campbelltown_tesla_venue" else
                {"site_file": "mount_annan_site", "supplier_file": "mount_annan_supplier"})
    pages = {}
    for field, provider in expected.items():
        filename = evidence[field]
        if filename not in sources or sources[filename].get("provider") != provider:
            raise ValueError("Reviewed venue evidence roles disagree")
        pages[field] = _PublishedHTML(payloads[filename])
    if kind == "campbelltown_tesla_venue":
        if ("Campbelltown Catholic Club has installed 12 Tesla Superchargers." not in pages["installation_file"].visible
                or "Address 20-22 Camden Rd Campbelltown NSW 2560" not in pages["address_file"].visible
                or "Campbelltown Catholic Club" not in pages["address_file"].visible):
            raise ValueError("Reviewed Tesla venue/address/12-charger evidence changed")
        address, network, plugs = "20-22 Camden Rd Campbelltown NSW 2560 Australia", "Tesla", 12
        rows = [(evidence["installation_file"], "venue_charger_installation", "Campbelltown Catholic Club:12 Tesla Superchargers"),
                (evidence["address_file"], "venue_address", "Contact:20-22 Camden Rd")]
    elif kind == "mount_annan_viva_venue":
        sites = [item.get("location") for item in pages["site_file"].jsonld if isinstance(item, dict) and isinstance(item.get("location"), dict)]
        if len(sites) != 1:
            raise ValueError("Reviewed Shell station JSON-LD is missing or ambiguous")
        site = sites[0]
        if (site.get("@id") != "https://find.shell.com/au/fuel/10110865-shell-reddy-express-mount-annan"
                or site.get("name") != "SHELL REDDY EXPRESS MOUNT ANNAN"
                or site.get("address", {}).get("streetAddress") != "241 WATERWORTH DRIVE"
                or site["address"].get("addressLocality") != "MOUNT ANNAN"
                or site["address"].get("postalCode") != "2567"
                or site["address"].get("addressCountry") != "AU"
                or "service station with EV charging located in MOUNT ANNAN" not in pages["site_file"].visible
                or "Viva Energy’s Reddy Express Mt. Annan’s ultrafast EV charging site" not in pages["supplier_file"].visible
                or "350kW per charger" not in pages["supplier_file"].visible):
            raise ValueError("Reviewed Shell/Viva site or charging-project identity changed")
        lat, lon = float(site["geo"]["latitude"]), float(site["geo"]["longitude"])
        if [lat, lon] != evidence["site_point_latlon"] or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Reviewed venue point changed")
        bound = evidence["max_source_distance_m"]
        if not isinstance(bound, (float, int)) or not 0 < bound <= 30:
            raise ValueError("Invalid reviewed Shell venue-distance bound")
        for member in group["members"]:
            raw = member["raw_values"]
            distance = GEOD.inv(float(raw["Longitude"]), float(raw["Latitude"]), lon, lat)[2]
            if not math.isfinite(distance) or distance > bound:
                raise ValueError("Source observation is outside the reviewed Shell venue bound")
        address, network, plugs = "241 Waterworth Dr, Mount Annan NSW 2567, Australia", "Viva Energy Australia", 4
        rows = [(evidence["site_file"], "operator_venue_map", "10110865"),
                (evidence["supplier_file"], "charging_project_supplier", "Reddy Express Mt. Annan")]
    else:
        raise ValueError("Unknown reviewed venue evidence kind")
    if evidence.get("address") != address or evidence.get("network") != network or evidence.get("source_plugs") != plugs:
        raise ValueError("Reviewed venue configuration disagrees with its parsed evidence")
    for member in group["members"]:
        raw = member["raw_values"]
        if (operator(raw["Operator"]) != network or raw["Charger_Type"] != "DC"
                or int(raw["Number_of_plugs"]) != plugs
                or address_identity(raw["Station_address"]) != address_identity(address)):
            raise ValueError("Reviewed venue evidence disagrees with source observations")
    return rows


def _evidence_audit(config, root):
    """Validate immutable originals and parse the actual operator map/details.

    These public AJAX responses were obtained by POST. They are frozen evidence,
    not inputs for the generic GET downloader; missing files require restoration
    of the reviewed snapshot or a new documented review.
    """
    sources, payloads = {}, {}
    for source in config.get("evidence_sources", []):
        filename = source["file"]
        path = _evidence_path(root, filename)
        if filename in sources or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
            raise ValueError("Duplicate reviewed identity source or invalid SHA-256")
        method = source.get("method")
        provider = source.get("provider")
        expected_url = (VENUE_URLS.get(provider) if provider is not None else
                        "https://exploren.com.au/find-a-charger/" if method == "GET"
                        else "https://exploren.com.au/wp-admin/admin-ajax.php")
        if method not in ("GET", "POST") or source["url"] != expected_url:
            raise ValueError("Reviewed identity evidence must reference its published primary endpoint")
        if provider is not None and method != "GET":
            raise ValueError("Reviewed venue evidence requires the published GET original")
        manifest_path = path.with_name(path.name + ".meta.json")
        if not path.is_file() or not manifest_path.is_file():
            raise FileNotFoundError(f"Frozen reviewed identity evidence missing: {filename}; restore the reviewed snapshot or perform a new review")
        body = path.read_bytes()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        actual_hash = sha256(body).hexdigest()
        if (actual_hash != source["sha256"] or manifest.get("sha256") != actual_hash
                or manifest.get("url") != source["url"] or manifest.get("bytes") != len(body)
                or manifest.get("status_code") != 200 or not manifest.get("retrieved_at_utc")
                or manifest.get("method", "GET") != method):
            raise ValueError(f"Reviewed identity evidence source/hash/metadata mismatch: {filename}")
        if method == "POST" and (
                source.get("request_action") != "exploren_get_location_detail"
                or manifest.get("request_action") != source["request_action"]
                or manifest.get("location_id") != source.get("location_id")
                or manifest.get("published_at_url") != f"https://exploren.com.au/find-a-charger/?charger_location={source.get('location_id')}"):
            raise ValueError("Reviewed identity POST request metadata mismatch")
        sources[filename], payloads[filename] = source, body.decode("utf-8")
    used, rows = set(), []
    for group in config["groups"]:
        evidence = group.get("evidence")
        if evidence is None:
            if group.get("evidence_required"):
                raise ValueError("Reviewed identity group requires operator evidence")
            continue
        if evidence.get("kind") in VENUE_KINDS:
            for filename, role, element_id in _venue_evidence(group, sources, payloads):
                used.add(filename)
                rows.append({"review_id": group["review_id"], "source_file": filename, "role": role,
                             "element_id": element_id, "sha256": sources[filename]["sha256"]})
            continue
        if "kind" in evidence:
            raise ValueError("Unknown reviewed identity evidence kind")
        map_file, detail_file = evidence["map_file"], evidence["detail_file"]
        if map_file not in sources or detail_file not in sources:
            raise ValueError("Unpinned reviewed identity evidence reference")
        element_id = evidence["operator_location_id"]
        if (sources[map_file]["method"] != "GET" or sources[detail_file]["method"] != "POST"
                or sources[detail_file].get("location_id") != element_id):
            raise ValueError("Reviewed identity map/detail roles or element IDs disagree")
        matches = list(re.finditer(r"\bvar\s+locations\s*=\s*", payloads[map_file]))
        if len(matches) != 1:
            raise ValueError("Reviewed operator map does not contain one locations array")
        points, _ = json.JSONDecoder().raw_decode(payloads[map_file][matches[0].end():])
        selected = [point for point in points if point.get("id") == element_id]
        if len(selected) != 1:
            raise ValueError("Reviewed operator map element is missing or ambiguous")
        point = selected[0]
        latitude, longitude = float(point["lat"]), float(point["lng"])
        if (text(point["name"]) != evidence["name"] or point["current_type"] != "ac"
                or not -90 <= latitude <= 90 or not -180 <= longitude <= 180
                or [latitude, longitude] != evidence["map_point_latlon"]):
            raise ValueError("Reviewed operator map name/type/coordinates disagree")
        detail = json.loads(payloads[detail_file])
        parser = _LocationDetail()
        if detail.get("success") is not True or not isinstance(detail.get("data"), str):
            raise ValueError("Reviewed operator location detail is not a successful response")
        parser.feed(detail["data"])
        if parser.headings != [evidence["name"]] or not parser.paragraphs or parser.paragraphs[0] != evidence["address"]:
            raise ValueError("Reviewed operator detail name/address disagree")
        bound = evidence["max_source_distance_m"]
        if not isinstance(bound, (float, int)) or not 0 < bound <= 100:
            raise ValueError("Invalid individually reviewed map-distance bound")
        for member in group["members"]:
            raw = member["raw_values"]
            distance = GEOD.inv(float(raw["Longitude"]), float(raw["Latitude"]), longitude, latitude)[2]
            if (operator(raw["Operator"]) != "Exploren" or raw["Charger_Type"] != "AC"
                    or extract_address_postcode(raw["Station_address"]) != extract_address_postcode(evidence["address"])
                    or not math.isfinite(distance) or distance > bound):
                raise ValueError("Reviewed operator evidence disagrees with source observations")
        for filename, role in [(map_file, "operator_map"), (detail_file, "operator_location_detail")]:
            used.add(filename)
            rows.append({"review_id": group["review_id"], "source_file": filename, "role": role,
                         "element_id": str(element_id), "sha256": sources[filename]["sha256"]})
    if used != set(sources):
        raise ValueError("Unreferenced reviewed identity evidence source")
    return pd.DataFrame(rows, columns=EVIDENCE_COLUMNS)


def identity_evidence_audit(*, config=None, root=ROOT):
    """Return the complete evidence ledger only after verifying and parsing it."""
    return _evidence_audit(_configuration(config, root), root)


def acquire_identities(offline=False, *, root=ROOT, config=None):
    """Verify frozen identity originals in either acquisition mode.

    GET and POST evidence both belong to a specific documented review. An
    online run must not silently substitute a current page for that original;
    missing evidence requires restoration or another explicit review.
    """
    return identity_evidence_audit(config=config, root=root)


def _member_agrees(row, member, expected_location):
    """Guard source identity, all raw fields, and the observations used downstream."""
    raw = member["raw_values"]
    try:
        if (row.record_id != member["record_id"] or row.source_row != member["source_row"]
                or row.location_id != expected_location or json.loads(row.raw_json) != raw):
            return False
        postcode_match = re.fullmatch(r"(?:NSW\s+)?(\d{4})", text(raw["PCODE"]), flags=re.I)
        postcode = postcode_match.group(1) if postcode_match else None
        expected_text = {
            "source_objectid": raw["OBJECTID"], "station_name": raw["Station_name"],
            "address": raw["Station_address"], "operator_name": operator(raw["Operator"]),
            "operator_id": identifier("o_", operator(raw["Operator"]).casefold()),
            "postcode": postcode, "address_postcode": extract_address_postcode(raw["Station_address"]),
            "lga": raw["LGANAME"], "charger_type": raw["Charger_Type"],
            "power_raw": raw["Charger_rating"], "source_category": raw["Source"],
        }
        if any(text(row[field]) != text(value) for field, value in expected_text.items()):
            return False
        if row.number_of_plugs != int(raw["Number_of_plugs"]):
            return False
        for field, original in [("latitude", "Latitude"), ("longitude", "Longitude")]:
            value = float(row[field])
            if not math.isfinite(value) or value != float(raw[original]):
                return False
            # Resolution adds these fields after the identity stage. Original
            # evidence must still agree when the ledger is consumed later.
            if "original_" + field in row.index and row["original_" + field] != value:
                return False
        if "original_postcode" in row.index and text(row.original_postcode) != text(postcode):
            return False
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    return True


def reviewed_identity_groups(records):
    """Return only fully guarded groups eligible for the local identity exception.

    Missing/additional members or any coordinate/source drift disable the
    exception. The ordinary group conflict checks then remain in force.
    """
    ledger = records.attrs.get(LEDGER_ATTRIBUTE)
    if not isinstance(ledger, dict):
        return {}
    approved = {}
    for group in ledger.get("groups", []):
        members = group["members"]
        rows = records.loc[records.location_id.eq(group["location_id"])]
        if len(rows) != len(members) or set(rows.record_id) != {m["record_id"] for m in members}:
            continue
        if all(len(found := rows.loc[rows.record_id.eq(member["record_id"])]) == 1
               and _member_agrees(found.iloc[0], member, group["location_id"]) for member in members):
            approved[group["location_id"]] = group["representative_record_id"]
    return approved


def _audit(config):
    return pd.DataFrame([
        {"record_id": member["record_id"], "source_row": member["source_row"],
         "review_id": group["review_id"], "original_location_id": member["original_location_id"],
         "location_id": group["location_id"], "representative_record_id": group["representative_record_id"],
         "source_file": config["source_file"], "reason": group["reason"], "review_date": group.get("review_date", config["review_date"])}
        for group in config["groups"] for member in group["members"]
    ], columns=AUDIT_COLUMNS)


def identity_audit_matches_configuration(con):
    """Detect removed, added or relabelled persisted reviewed members."""
    expected = sorted(_audit(_configuration(None)).itertuples(index=False, name=None))
    actual = con.execute("""
        SELECT record_id,source_row,review_id,original_location_id,location_id,
               representative_record_id,source_file,reason,CAST(review_date AS VARCHAR)
        FROM reviewed_identity ORDER BY ALL
    """).fetchall()
    return actual == expected


def apply_reviewed_identities(records, issues, *, config=None, root=ROOT):
    """Map reviewed original locations; retain every row and all observations.

    The serializable attrs ledger survives pipeline DataFrame copies. The audit
    separately persists membership, old IDs, the whole-row representative and
    source reference. It is not reconstructed implicitly when reading a CSV.
    """
    config = _configuration(config, root)
    _evidence_audit(config, root)
    existing = records.attrs.get(LEDGER_ATTRIBUTE)
    if existing is not None:
        if existing != config or set(reviewed_identity_groups(records)) != {g["location_id"] for g in config["groups"]}:
            raise ValueError("Reviewed identity ledger no longer agrees with the source records")
        return records.copy(deep=True), _audit(config)
    result = records.copy(deep=True)
    # Validate the complete batch before changing any location or adding issues.
    for group in config["groups"]:
        ids = {member["record_id"] for member in group["members"]}
        original_locations = {member["original_location_id"] for member in group["members"]}
        if not set(result.loc[result.location_id.isin(original_locations), "record_id"]) <= ids:
            raise ValueError(f"Unreviewed member in original identity group {group['review_id']}")
        for member in group["members"]:
            rows = result.loc[result.record_id.eq(member["record_id"])]
            if len(rows) != 1 or not _member_agrees(rows.iloc[0], member, member["original_location_id"]):
                raise ValueError(f"Reviewed identity source guard failed: {member['record_id']}")
    pending = []
    for group in config["groups"]:
        ids = {member["record_id"] for member in group["members"]}
        result.loc[result.record_id.isin(ids), "location_id"] = group["location_id"]
        for member in group["members"]:
            pending.append({"record_id": member["record_id"], "source_row": member["source_row"],
                            "code": "reviewed_location_identity", "severity": "info",
                            "detail": f"{group['review_id']}: {member['original_location_id']} -> {group['location_id']}; "
                                      f"representative={group['representative_record_id']}; "
                                      f"original Source={member['raw_values']['Source']}; {group['reason']}"})
    result.attrs[LEDGER_ATTRIBUTE] = config
    issues.extend(pending)
    return result, _audit(config)
