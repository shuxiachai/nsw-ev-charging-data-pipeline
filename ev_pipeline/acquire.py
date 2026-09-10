"""Automated official-source acquisition with immutable local cache manifests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
import re
from urllib.parse import urljoin, urlencode, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
TFNSW = "https://opendata.transport.nsw.gov.au/api/3/action/package_show?id=ev-charging-locations"
ABS = "https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-4-july-2026-june-2031/access-and-downloads/digital-boundary-files"
REPO = "https://api.github.com/repos/openchargemap/ocm-export"
OCM_REVISION = "8e3bedca48ca94807d96b2f5e7ee02cffe63ae54"
OSM_QUERY = '[out:json][timeout:90];nwr["amenity"="charging_station"](-37.6,140.9,-28.0,153.7);out center tags;'
OSM_URL = "https://overpass-api.de/api/interpreter?" + urlencode({"data": OSM_QUERY})
JOLT_URL = "https://joltcharge.com/au/find-a-charger/"
NRMA_URL = "https://www.mynrma.com.au/cars-and-driving/electric-vehicles/charging-network"


def session():
    s = requests.Session()
    s.headers["User-Agent"] = "COMP5339-EV-Research/1.0"
    retry = Retry(total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def fetch(url, path, offline=False, expected_sha256=None):
    """Never silently replace a cached input; stage new observations separately."""
    path = Path(path)
    meta = path.with_name(path.name + ".meta.json")
    stored = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else None
    if expected_sha256 is not None:
        expected_sha256 = expected_sha256.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError(f"Invalid expected SHA-256: {path}")
    if stored is not None and stored["url"] != url:
        raise ValueError(f"Cache source/hash mismatch: {path}")

    def check_bytes(digest, size):
        if stored is not None and (digest != stored["sha256"] or
                                   ("bytes" in stored and size != stored["bytes"])):
            raise ValueError(f"Cache source/hash mismatch: {path}")
        if expected_sha256 is not None and digest != expected_sha256:
            raise ValueError(f"Reviewed source SHA-256 mismatch: {path}")

    if path.exists():
        if stored is None:
            raise ValueError(f"Untracked cached input: {path}")
        content = path.read_bytes()
        check_bytes(sha256(content).hexdigest(), len(content))
        return path
    if offline:
        raise FileNotFoundError(f"Offline input missing: {path}. Run acquire online first.")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    meta_partial = meta.with_name(meta.name + ".part")
    try:
        with session() as s:
            # Optional token stays in the header and never enters URLs or manifests.
            if url.startswith("https://api.github.com/") and os.getenv("GITHUB_TOKEN"):
                s.headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
            with s.get(url, timeout=(15, 120), stream=True) as r:
                r.raise_for_status()
                digest = sha256()
                size = 0
                with partial.open("wb") as f:
                    for chunk in r.iter_content(1024 * 1024):
                        f.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                if size == 0:
                    raise ValueError(f"Empty download: {url}")
                check_bytes(digest.hexdigest(), size)
                metadata = stored or {
                    "url": url, "resolved_url": r.url,
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    "sha256": digest.hexdigest(), "bytes": size,
                    "etag": r.headers.get("ETag"), "last_modified": r.headers.get("Last-Modified")}
        # Install provenance first. An interruption can leave a manifest without
        # data, which a retry restores only if the original bytes still match.
        # Never leave a completed new file without its provenance manifest.
        if stored is None:
            meta_partial.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            meta_partial.replace(meta)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
        meta_partial.unlink(missing_ok=True)
    return path


def json_input(url, name, offline=False):
    return json.loads(fetch(url, RAW / name, offline).read_text(encoding="utf-8-sig"))


def tfnsw_resource_status(resource):
    """Classify explicit publisher labels, not filename dates or CKAN 'active'."""
    name = str(resource.get("name") or "").casefold()
    description = str(resource.get("description") or "").casefold()
    historical = (re.search(r"\b(?:historic(?:al)?|archived?|superseded|deprecated)\b", name)
                  or re.search(r"\b(?:no longer current|not current|not updated|for historic(?:al)? purposes(?: only)?)\b",
                               name + " " + description))
    if historical:
        return "historical"
    if (re.search(r"\bcurrent\b", name)
            or re.search(r"\b(?:current|latest) (?:version|data(?:set)?|resource)\b", description)):
        return "current"
    return "unmarked"


def tfnsw_csv_resource(data, *, assignment_version=True, resource_id=None):
    """Keep normal acquisition pinned; candidate staging can inspect a new CSV."""
    if not data.get("success"):
        raise ValueError("TfNSW CKAN response did not report success")
    resources = data["result"]["resources"]
    if assignment_version:
        if resource_id is not None:
            raise ValueError("Explicit TfNSW resource IDs are only supported for candidate staging")
        choices = [r for r in resources if re.search(r"ev_202512\d{2}\.csv$", r["url"])]
    else:
        def is_csv(resource):
            declared = str(resource.get("format") or "").strip().upper()
            return declared == "CSV" if declared else urlsplit(resource["url"]).path.lower().endswith(".csv")

        if resource_id is not None:
            matches = [r for r in resources if r.get("id") == resource_id]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one TfNSW resource with ID {resource_id!r}; found {len(matches)}")
            if not is_csv(matches[0]):
                raise ValueError(f"Selected TfNSW resource ID {resource_id!r} is not a CSV")
            return matches[0]
        csvs = [r for r in resources if is_csv(r)]
        current = [r for r in csvs if tfnsw_resource_status(r) == "current"]
        choices = current or [r for r in csvs if tfnsw_resource_status(r) == "unmarked"]
    if len(choices) != 1:
        if assignment_version:
            raise ValueError("Expected exactly one December 2025 CSV; inspect official catalogue instead of substituting a newer version")
        raise ValueError(f"Expected exactly one candidate CSV resource at the preferred nonhistorical priority; "
                         f"found {len(choices)}. Inspect the catalogue and use --tfnsw-resource-id to choose explicitly.")
    return choices[0]


def tfnsw_metadata_resource(data):
    """Candidate documentation uses the same explicit publisher-label priority."""
    if not data.get("success"):
        raise ValueError("TfNSW CKAN response did not report success")
    documents = [r for r in data["result"]["resources"] if str(r.get("format") or "").strip().upper() == "PDF"]
    current = [r for r in documents if tfnsw_resource_status(r) == "current"]
    choices = current or [r for r in documents if tfnsw_resource_status(r) == "unmarked"]
    if len(choices) != 1:
        raise ValueError(f"Expected exactly one candidate TfNSW metadata PDF at the preferred nonhistorical priority; "
                         f"found {len(choices)}. Inspect the official catalogue.")
    return choices[0]


def abs_boundary_url(page):
    links = set(re.findall(r'href="([^"]*SA4_2026_AUST_SHP_GDA2020\.zip)"', page))
    if len(links) != 1:
        raise ValueError("ABS 2026 SA4 shapefile link missing or ambiguous")
    return urljoin(ABS, links.pop())


def nrma_map_url(page):
    mid = re.search(r'google.com/maps/d/[^"<>]*mid=([^&"<>]+)', page)
    if mid is None:
        raise ValueError("NRMA public map link changed")
    return "https://www.google.com/maps/d/kml?mid=" + mid.group(1) + "&forcekml=1"


def acquire(offline=False):
    data = json_input(TFNSW, "tfnsw_catalog.json", offline)
    fetch(tfnsw_csv_resource(data)["url"], RAW / "ev_20251216.csv", offline)
    docs = [r for r in data["result"]["resources"] if r["format"].upper() == "PDF"]
    if docs:
        fetch(docs[0]["url"], RAW / "tfnsw_metadata.pdf", offline)
    page = fetch(ABS, RAW / "abs_download_page.html", offline).read_text(encoding="utf-8")
    fetch(abs_boundary_url(page), RAW / "SA4_2026_AUST_SHP_GDA2020.zip", offline)

    # Pin every OCM file and lookup table to one commit; a directory Contents API
    # call is capped at 1,000 entries, so use the complete country Git tree.
    commit = json_input(REPO + "/commits/" + OCM_REVISION, "ocm_revision.json", offline)
    revision = commit["sha"]
    root = json_input(REPO + "/git/trees/" + commit["commit"]["tree"]["sha"], "ocm_root_tree.json", offline)
    data_sha = next(x["sha"] for x in root["tree"] if x["path"] == "data")
    tree = json_input(REPO + "/git/trees/" + data_sha, "ocm_data_tree.json", offline)
    au_sha = next(x["sha"] for x in tree["tree"] if x["path"] == "AU")
    au = json_input(REPO + "/git/trees/" + au_sha, "ocm_au_tree.json", offline)
    if au.get("truncated"):
        raise ValueError("OCM country listing truncated")
    base = f"https://raw.githubusercontent.com/openchargemap/ocm-export/{revision}/"
    fetch(base + "data/referencedata.json", RAW / "ocm_reference.json", offline)
    fetch(base + "README.md", RAW / "ocm_source_readme.md", offline)
    entries = [x for x in au["tree"] if x["type"] == "blob" and x["path"].endswith(".json")]
    logging.info("Acquiring/verifying %s Australian OCM records at commit %s", len(entries), revision)

    def one(entry):
        name = entry["path"]
        if Path(name).name != name:
            raise ValueError("Unexpected nested OCM path")
        fetch(base + "data/AU/" + name, RAW / "ocm" / name, offline)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, _ in enumerate(pool.map(one, entries), 1):
            if i % 250 == 0:
                logging.info("OCM inputs: %s/%s", i, len(entries))
    osm = json_input(OSM_URL, "osm_chargers.json", offline)
    if osm.get("remark") or "elements" not in osm:
        raise ValueError("Overpass returned a partial/error response; do not use incomplete data")
    fetch(JOLT_URL, RAW / "jolt_map.html", offline)
    # Retain the operator-published map examined during source-error review.
    # It is contextual evidence only: town-level pins are not street geocodes.
    nrma = fetch(NRMA_URL, RAW / "nrma_network.html", offline).read_text(encoding="utf-8")
    fetch(nrma_map_url(nrma), RAW / "nrma_stations.kml", offline)
    # The reviewed module owns its configuration and source-path validation.
    # Import lazily because it uses fetch() for the same immutable-cache rules.
    from .reviewed import acquire_reviewed
    acquire_reviewed(offline=offline)
    from .regional import acquire_regional
    acquire_regional(offline=offline)
    from .ampol import acquire_ampol
    acquire_ampol(offline=offline)
    # Reviewed identities include frozen POST responses and reviewed venue
    # publications. Verify their pinned originals; do not silently refresh them.
    from .identity import acquire_identities
    acquire_identities(offline=offline)
    logging.info("Acquisition complete; input hashes verified")
