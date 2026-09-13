# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Source-attributed semantic review, without choosing a winning observation."""
from datetime import datetime, timezone
import json
import re
from urllib.parse import urlsplit

import pandas as pd

from .clean import text


DIFFERENCE_COLUMNS = ["location_id", "attribute", "values_json", "note", "category", "observations_json"]
CONNECTOR_QUALITY_COLUMNS = ["location_id", "ocm_id", "connection_id", "category", "site_status",
                             "connection_status", "quantity", "detail", "source_file"]
# The archived nrma_network.html and its manifest establish both the requested
# network page and its resolved URL. Exact paths only: child pages, queries and
# fragments may identify an individual station and must retain site scope.
REVIEWED_NETWORK_PAGES = {
    ("NRMA", "mynrma.com.au", "/cars-and-driving/electric-vehicles/charging-network"),
    ("NRMA", "mynrma.com.au", "/electric-vehicles/charging"),
}


def source_verified_at(value):
    """Parse only a source-supplied, timezone-qualified verification timestamp.

    This describes OCM's POI verification field, not when its price was effective
    or when the project retrieved the JSON. Never fill it from retrieval time.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        raise ValueError(f"OCM DateLastVerified needs an explicit ISO timestamp and timezone: {value!r}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid OCM DateLastVerified: {value!r}") from error
    return parsed.astimezone(timezone.utc)


def _url(value):
    value = text(value)
    # Only a complete single URL is a link observation. Text containing a URL
    # can still contain useful access instructions and is retained as text.
    if not value or re.search(r"\s", value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        return parsed
    except ValueError:
        return None


def _host(parsed):
    return parsed.hostname.lower().removeprefix("www.")


def operator_website_hosts(details):
    """Use independently named operator website observations to identify hosts."""
    hosts = {}
    if details is None or details.empty:
        return hosts
    for row in details.loc[details.attribute.eq("operator_website")].itertuples():
        parsed = _url(row.value)
        if parsed:
            hosts.setdefault(row.operator_name, set()).add(_host(parsed))
    return hosts


def classify_url_attribute(value, operator_name, hosts, *, original_attribute):
    """A network landing page is not an individual site's access restriction.

    Only a known operator host plus an explicit generic path establishes the
    operator scope. Unknown hosts and individual detail URLs are not generalized.
    """
    parsed = _url(value)
    if parsed is None:
        return original_attribute, "site"
    known_host = _host(parsed) in hosts.get(operator_name, set())
    path = parsed.path.rstrip("/").lower()
    if known_host and not parsed.query and not parsed.fragment:
        if path == "":
            return "operator_website", "operator"
        if (path in {"/our-network", "/charging-network", "/find-a-charger"}
                or (operator_name, _host(parsed), path) in REVIEWED_NETWORK_PAGES):
            return "operator_network_map_url", "operator"
    return ("access_information_url" if original_attribute == "access_comments" else original_attribute), "site"


def _observations(group):
    fields = ["attribute", "value", "scope", "source_file", "ocm_id", "osm_id", "jolt_id", "ampol_id", "ocm_operator_id"]
    records = []
    for row in group.to_dict("records"):
        out = {}
        for name in fields:
            value = row.get(name)
            if value is None or pd.isna(value):
                out[name] = None
            elif name in {"ocm_id", "jolt_id", "ocm_operator_id"}:
                out[name] = int(value)
            else:
                out[name] = str(value)
        records.append(out)
    return json.dumps(sorted(records, key=lambda row: json.dumps(row, sort_keys=True)), ensure_ascii=False)


def connector_difference_category(values):
    """Classify observed set differences, not physical ground-truth truth."""
    sets = [set(part.strip() for part in value.split(";") if part.strip()) for value in values]
    if all(group == sets[0] for group in sets[1:]):
        return "connector_order_or_format"
    # Explicit CCS1/CCS2 disagreements need hardware review even when a Tesla
    # label also occurs; a network label is not evidence of physical equivalence.
    ccs1, ccs2 = "CCS (Type 1)", "CCS (Type 2)"
    if any(ccs1 in a and ccs2 not in a and ccs2 in b and ccs1 not in b for a in sets for b in sets):
        return "connector_physical_type_conflict"
    if any("tesla" in token.lower() for group in sets for token in group):
        return "connector_tesla_naming_or_hardware_review"
    if all(a <= b or b <= a for a in sets for b in sets):
        return "connector_set_inclusion"
    return "connector_physical_type_conflict"


def _positive_cost(value):
    # Currency amounts and cents are explicit paid-cost evidence. Bare numbers
    # (parking times, free kWh allowances, connector counts) are insufficient.
    return any(float(match.group(1)) > 0 for match in re.finditer(
        r"(?:\$\s*|\bAUD\s*)(\d+(?:\.\d+)?)", value, flags=re.I)) or any(
        float(match.group(1)) > 0 for match in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(?:c\b|cents?\b)", value, flags=re.I))


def _free_only_cost(value):
    # Full-string statements only: a free allowance, membership condition or
    # future change is not an unconditional no-charge observation.
    return text(value).casefold().rstrip(".! ") in {"free", "free charging", "no charge", "free of charge"}


def attribute_differences(attributes):
    """Include cross-field fee evidence while preserving every source value.

    Flags request review: OSM fee may describe different conditions or a
    different observation date from OCM UsageCost. They do not replace either.
    """
    rows = []
    site = attributes.loc[attributes.scope.eq("site")]
    for (lid, attribute), group in site.groupby(["location_id", "attribute"], sort=True):
        values = sorted(set(group.value))
        if len(values) < 2:
            continue
        category = connector_difference_category(values) if attribute == "dc_connector_types" else "source_text_difference"
        rows.append({"location_id": lid, "attribute": attribute, "values_json": json.dumps(values),
                     "note": "Source observations retained; naming, coverage, conditions or dates may differ. No automatic overwrite.",
                     "category": category, "observations_json": _observations(group)})
    for lid, group in site.groupby("location_id", sort=True):
        fees = group.loc[group.attribute.eq("fee")]
        costs = group.loc[group.attribute.eq("usage_cost_text")]
        no_fees = fees.loc[fees.value.map(lambda value: text(value).casefold() == "no")]
        yes_fees = fees.loc[fees.value.map(lambda value: text(value).casefold() == "yes")]
        positive = costs.loc[costs.value.map(_positive_cost).astype(bool)]
        free_only = costs.loc[costs.value.map(_free_only_cost).astype(bool)]
        relevant_groups, reasons = [], []
        if not no_fees.empty and not positive.empty:
            relevant_groups.extend([no_fees, positive])
            reasons.append("fee=no coexists with explicit positive cost text")
        if not yes_fees.empty and not free_only.empty:
            relevant_groups.extend([yes_fees, free_only])
            reasons.append("fee=yes coexists with an explicit unconditional free-cost statement")
        if not relevant_groups:
            continue
        relevant = pd.concat(relevant_groups).drop_duplicates()
        rows.append({"location_id": lid, "attribute": "fee_vs_usage_cost_text",
                     "values_json": json.dumps(sorted(set(relevant.value))),
                     "note": "; ".join(reasons) + "; review dates and charging/parking/member conditions. Neither source is overridden.",
                     "category": "fee_semantic_review", "observations_json": _observations(relevant)})
    return pd.DataFrame(rows, columns=DIFFERENCE_COLUMNS).sort_values(["location_id", "attribute"], ignore_index=True)


def connector_quality(sites, connectors, matches):
    """Audit accepted DC connection observations, without inferring live uptime."""
    rows = []
    lookup = sites.set_index("ocm_id")
    for match in matches.itertuples():
        site = lookup.loc[match.ocm_id]
        dc = connectors.loc[connectors.ocm_id.eq(match.ocm_id) & connectors.current_type_id.eq(30)]
        for connection in dc.itertuples():
            common = dict(location_id=match.location_id, ocm_id=match.ocm_id, connection_id=connection.connection_id,
                          site_status=site.status, connection_status=connection.status, quantity=connection.quantity,
                          source_file=site.source_file)
            if pd.notna(connection.quantity) and connection.quantity == 0:
                rows.append(dict(common, category="zero_quantity_dc_connection",
                                 detail="Source reports Quantity=0: retained connector row, excluded from dc_connector_types. Site matching is not proof of available equipment."))
            if text(site.status) not in {"", "Unknown"} and text(connection.status) not in {"", "Unknown"} and site.status != connection.status:
                rows.append(dict(common, category="site_connection_status_difference",
                                 detail="Site and connection report different OCM status labels. Labels and quantities are historical source observations, not live availability."))
    return pd.DataFrame(rows, columns=CONNECTOR_QUALITY_COLUMNS)
