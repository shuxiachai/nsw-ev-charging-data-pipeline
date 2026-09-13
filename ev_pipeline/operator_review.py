# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Withhold specifically reviewed operator assignments without changing source labels."""
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from .acquire import ROOT
from .clean import FIELDS, identifier, operator, text

ISSUE_CODE = "operator_assignment_pending_review"
ISSUE_FIELDS = ["record_id", "source_row", "code", "severity", "detail"]
ATTRIBUTE_KEYS = {"operator_website": "WebsiteURL", "operator_phone": "PhonePrimaryContact"}


def load_operator_reviews(locations, records, reference, *, root=ROOT, config=None):
    """Bind each pending decision to complete original rows and a lookup value.

    A country domain is not an exclusion rule. The ledger withholds only the
    named location/lookup/attribute assignment; other locations remain eligible.
    Missing or changed reviewed evidence requires a new explicit review.
    """
    root = Path(root)
    if config is None:
        config = json.loads((root / "config/reviewed_operator_assignments.json").read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported operator assignment review configuration")
    date.fromisoformat(config["review_date"])
    originals = {}
    for name, expected_file in [("source_snapshot", "data/raw/ev_20251216.csv"),
                                ("external_snapshot", "data/raw/ocm_reference.json")]:
        source = config[name]
        if source["file"] != expected_file:
            raise ValueError("Operator review has an unexpected evidence file")
        body = (root / expected_file).read_bytes()
        if sha256(body).hexdigest() != source["sha256"]:
            raise ValueError("Operator review evidence hash mismatch")
        originals[name] = body
    original_reference = json.loads(originals["external_snapshot"])
    result, review_ids = {}, set()
    for review in config["reviews"]:
        review_id, raw = review["review_id"], review["expected_raw_source"]
        attribute = review["attribute"]
        if (not text(review_id) or review_id in review_ids or not text(review["reason"])
                or review["decision"] != "withheld_pending_identity_review"
                or attribute not in ATTRIBUTE_KEYS or not text(review["value"])
                or set(raw) != set(FIELDS) or not all(isinstance(v, str) for v in raw.values())
                or identifier("r_", {k: text(v) for k, v in raw.items()}) != review["record_id"]):
            raise ValueError("Invalid or duplicate operator assignment review")
        review_ids.add(review_id)
        selected = records.loc[records.record_id.eq(review["record_id"]) | records.source_row.eq(review["source_row"])]
        if len(selected) != 1:
            raise ValueError("Reviewed operator source record is missing or ambiguous")
        record = selected.iloc[0]
        if (record.record_id != review["record_id"] or record.source_row != review["source_row"]
                or json.loads(record.raw_json) != raw):
            raise ValueError("Reviewed operator original source guard failed")
        selected_location = locations.loc[locations.location_id.eq(record.location_id)]
        if len(selected_location) != 1:
            raise ValueError("Reviewed operator location is missing or ambiguous")
        location = selected_location.iloc[0]
        if (location.operator_name != operator(raw["Operator"])
                or text(location.address) != text(raw["Station_address"])):
            raise ValueError("Reviewed operator location identity guard failed")
        for supplied in [original_reference, reference]:
            candidates = [op for op in supplied["Operators"] if op["ID"] == review["ocm_operator_id"]]
            if (len(candidates) != 1 or candidates[0]["Title"] != review["ocm_operator_title"]
                    or operator(candidates[0]["Title"]) != location.operator_name
                    or text(candidates[0].get(ATTRIBUTE_KEYS[attribute])) != review["value"]):
                raise ValueError("Reviewed operator lookup identity/value guard failed")
        key = (record.location_id, int(review["ocm_operator_id"]), attribute, review["value"])
        if key in result:
            raise ValueError("Duplicate reviewed operator assignment")
        evidence = {"review_id": review_id, "review_date": config["review_date"],
                    "decision": review["decision"], "location_id": record.location_id,
                    "source_operator": raw["Operator"], "ocm_operator_id": review["ocm_operator_id"],
                    "ocm_operator_title": review["ocm_operator_title"], "attribute": attribute,
                    "candidate_value": review["value"], "source_snapshot": config["source_snapshot"],
                    "external_snapshot": config["external_snapshot"], "reason": review["reason"]}
        result[key] = {"record_id": record.record_id, "source_row": int(record.source_row),
                       "code": ISSUE_CODE, "severity": "warning",
                       "detail": json.dumps(evidence, sort_keys=True, ensure_ascii=False)}
    return result


def usable_operator_details(locations, details, reviews):
    """Remove shared lookup rows only when every current assignment is withheld.

    This also stops downstream URL classification from using a lookup that has
    no eligible current location. A review for one location cannot suppress a
    different location's otherwise unchanged operator information.
    """
    keep = []
    remaining = set(reviews)
    for row in details.itertuples():
        keys = {(loc, int(row.ocm_operator_id), row.attribute, row.value)
                for loc in locations.loc[locations.operator_name.eq(row.operator_name), "location_id"]}
        remaining.difference_update(keys)
        keep.append(bool(keys - reviews.keys()))
    if remaining:
        raise ValueError("Reviewed operator assignment is absent from lookup candidates")
    return details.loc[keep].copy()


def database_operator_reviews_valid(con, *, root=ROOT, config=None):
    """Require the pending audit and the absence of its withheld assignment."""
    try:
        locations = con.execute("SELECT l.location_id,l.address,o.operator_name FROM location l JOIN operator o USING(operator_id)").df()
        records = con.execute("SELECT record_id,source_row,location_id,raw_json FROM charger_record").df()
        reference = json.loads((Path(root) / "data/raw/ocm_reference.json").read_text(encoding="utf-8"))
        reviews = load_operator_reviews(locations, records, reference, root=root, config=config)
        expected = sorted(tuple(issue[key] for key in ISSUE_FIELDS) for issue in reviews.values())
        actual = con.execute("SELECT record_id,source_row,code,severity,detail FROM quality_issue WHERE code=? ORDER BY ALL", [ISSUE_CODE]).fetchall()
        if actual != expected:
            return False
        for location_id, external_id, attribute, value in reviews:
            # Block altered/reintroduced values under the reviewed relationship,
            # not merely one exact string. The original value is guarded above.
            if con.execute("SELECT count(*) FROM augmentation WHERE location_id=? AND ocm_operator_id=? AND attribute=?",
                           [location_id, external_id, attribute]).fetchone()[0]:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False
