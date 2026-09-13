# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Download a new observation for review without changing the frozen project."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ev_pipeline.acquire import (
    ABS, JOLT_URL, NRMA_URL, OCM_REVISION, OSM_URL, TFNSW,
    abs_boundary_url, fetch, nrma_map_url, tfnsw_csv_resource, tfnsw_metadata_resource, tfnsw_resource_status,
)

# Candidate CSV has a neutral name: a newly published version is not December 2025.
SOURCES = {
    "tfnsw_catalog": ("tfnsw_catalog.json", "tfnsw_catalog.json"),
    "tfnsw_csv": ("tfnsw_chargers.csv", "ev_20251216.csv"),
    "tfnsw_metadata": ("tfnsw_metadata.pdf", "tfnsw_metadata.pdf"),
    "abs_page": ("abs_download_page.html", "abs_download_page.html"),
    "abs_boundary": ("SA4_2026_AUST_SHP_GDA2020.zip", "SA4_2026_AUST_SHP_GDA2020.zip"),
    "osm": ("osm_chargers.json", "osm_chargers.json"),
    "jolt": ("jolt_map.html", "jolt_map.html"),
    "nrma_page": ("nrma_network.html", "nrma_network.html"),
    "nrma_map": ("nrma_stations.kml", "nrma_stations.kml"),
}


def _candidate_directory(root, label):
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{i}" for prefix in ["COM", "LPT"] for i in range(1, 10)}
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", label) or label.upper() in reserved:
        raise ValueError("Label must be 1-64 letters, digits, underscores or hyphens; start with a letter/digit and avoid reserved names")
    parent = root / ".runtime/source_candidates"
    # Reject redirected directories, including a link into the active raw folder.
    if parent.resolve() != parent or not parent.resolve().is_relative_to(root):
        raise ValueError("Candidate directory must remain at ROOT/.runtime/source_candidates without redirection")
    target = parent / label
    target.mkdir(parents=True, exist_ok=False)
    return target


def _dependencies(config, filename):
    result = []
    publication = config.get("map_publication", {})
    for entry in config.get("resolutions", []):
        roles = [role for role in ["coordinate", "corroborating"] if entry.get(role, {}).get("file") == filename]
        if entry.get("address_source_file") == filename:
            roles.append("address_evidence")
        if publication.get("source_file") == filename:
            roles.append("map_publication")
        if roles:
            result.append({"record_id": entry["record_id"], "roles": roles})
    return result


def _regional_dependencies(config, filename):
    """Report pinned evidence relationships without applying a regional review."""
    sources = {source["file"]: source for source in config.get("sources", [])}
    return [
        {"review_id": review["review_id"], "record_id": review["record_id"], "role": evidence["role"],
         "pinned_sha256": sources[filename]["sha256"], "pinned_url": sources[filename]["url"]}
        for review in config.get("reviews", [])
        for evidence in review.get("evidence", [])
        if evidence["source_file"] == filename
    ]


def _write_report(path, report):
    partial = path.with_name(path.name + ".part")
    try:
        partial.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def stage_candidates(label, *, root=ROOT, tfnsw_resource_id=None):
    root = Path(root).resolve()
    target = _candidate_directory(root, label)
    report_path = target / "candidate_report.json"
    report = {
        "schema_version": 1, "label": label, "complete": False, "status": "in_progress",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "New observations for manual review; not a buildable or approved submission version.",
        "ocm": {"refreshed": False, "retained_commit": OCM_REVISION},
        "tfnsw_requested_resource_id": tfnsw_resource_id,
        "sources": {},
    }
    _write_report(report_path, report)
    logging.info("Candidate report: %s", report_path)
    stage = "read_review_configuration"
    try:
        config = json.loads((root / "config/reviewed_resolutions.json").read_text(encoding="utf-8"))
        pinned = {source["file"]: source for source in config["sources"]}
        match_path = root / "config/reviewed_match_exceptions.json"
        matching = json.loads(match_path.read_text(encoding="utf-8")) if match_path.is_file() else {}
        identity_path = root / "config/reviewed_identities.json"
        identities = json.loads(identity_path.read_text(encoding="utf-8")) if identity_path.is_file() else {}
        regional_path = root / "config/reviewed_regions.json"
        regional = json.loads(regional_path.read_text(encoding="utf-8")) if regional_path.is_file() else {}
        for name, (candidate_name, current_name) in SOURCES.items():
            current = root / "data/raw" / current_name
            relative = current.relative_to(root).as_posix()
            report["sources"][name] = {
                "status": "not_downloaded", "candidate_file": "data/raw/" + candidate_name,
                "current_file": relative,
                "current_sha256": sha256(current.read_bytes()).hexdigest() if current.is_file() else None,
                "review_pinned_sha256": pinned.get(relative, {}).get("sha256"),
                "review_pinned_url": pinned.get(relative, {}).get("url"),
                "reviewed_dependencies": _dependencies(config, relative),
                "matching_review_dependencies": [
                    {"review_id": entry["review_id"], "record_id": entry["record_id"], "role": role,
                     "pinned_sha256": entry[role]["sha256"]}
                    for entry in matching.get("exceptions", [])
                    for role in ["source_snapshot", "external_snapshot", "evidence"]
                    if entry.get(role, {}).get("file") == relative],
                "identity_review_groups": ([group["review_id"] for group in identities.get("groups", [])]
                                           if identities.get("source_file") == relative else []),
                "regional_review_dependencies": _regional_dependencies(regional, relative),
            }

        def download(name, url):
            nonlocal stage
            stage = name
            entry = report["sources"][name]
            entry["requested_url"] = url
            path = target / entry["candidate_file"]
            # This is a distinct candidate, never a replacement for review-pinned bytes.
            fetch(url, path)
            meta = json.loads(path.with_name(path.name + ".meta.json").read_text(encoding="utf-8"))
            actual = sha256(path.read_bytes()).hexdigest()
            if (meta.get("url") != url or meta.get("sha256") != actual
                    or meta.get("bytes") != path.stat().st_size or not meta.get("retrieved_at_utc")):
                raise ValueError(f"Candidate source/manifest mismatch: {name}")
            entry.update(status="downloaded", sha256=actual, bytes=path.stat().st_size,
                         manifest_file=entry["candidate_file"] + ".meta.json", resolved_url=meta.get("resolved_url"),
                         comparison=("current_missing" if entry["current_sha256"] is None else
                                     "identical" if actual == entry["current_sha256"] else "changed"))
            if entry["review_pinned_sha256"] is not None:
                entry["review_evidence_status"] = ("unchanged_pinned_bytes" if actual == entry["review_pinned_sha256"]
                                                   else "new_bytes_require_review_before_adoption")
                entry["review_source_url_changed"] = url != entry["review_pinned_url"]
                if entry["review_source_url_changed"]:
                    entry["review_evidence_status"] = "new_source_url_requires_review_before_adoption"
            if name == "tfnsw_csv":
                entry["review_target_note"] = (
                    "Check reviewed correction record IDs, original-value guards and the listed identity groups before "
                    "adopting changed source rows. Matching-exception and regional-review snapshot dependencies "
                    "are listed separately. "
                    "Changes elsewhere do not by themselves invalidate an unchanged reviewed correction record.")
            for dependency in entry["matching_review_dependencies"]:
                dependency["snapshot_status"] = ("unchanged_pinned_bytes" if actual == dependency["pinned_sha256"]
                                                 else "new_bytes_require_review_before_adoption")
            for dependency in entry["regional_review_dependencies"]:
                dependency["bytes_changed"] = actual != dependency["pinned_sha256"]
                dependency["source_url_changed"] = url != dependency["pinned_url"]
                dependency["requires_review"] = dependency["bytes_changed"] or dependency["source_url_changed"]
                dependency["snapshot_status"] = (
                    "new_source_url_requires_review_before_adoption" if dependency["source_url_changed"] else
                    "new_bytes_require_review_before_adoption" if dependency["bytes_changed"] else
                    "unchanged_pinned_bytes_and_url")
            _write_report(report_path, report)
            return path

        catalogue = json.loads(download("tfnsw_catalog", TFNSW).read_text(encoding="utf-8-sig"))
        stage = "discover_tfnsw_csv"
        resource = tfnsw_csv_resource(catalogue, assignment_version=False, resource_id=tfnsw_resource_id)
        classification = tfnsw_resource_status(resource)
        report["tfnsw_selected_resource"] = {key: resource.get(key) for key in ["id", "name", "description", "format", "url"]}
        report["tfnsw_selection"] = {
            "method": "explicit_resource_id" if tfnsw_resource_id is not None else "official_current_historical_labels",
            "official_label_status": classification,
            "note": ("Officially marked historical and explicitly selected for comparison; not a current or "
                     "assignment-approved replacement. The separately downloaded catalogue documentation is contextual; "
                     "its version correspondence to this historical CSV has not been established."
                     if classification == "historical" else
                     "Selection uses the publisher's resource labels or an explicit ID, not filename dates. "
                     "Unmarked means no explicit current/historical label was found; assignment version still needs review."),
        }
        download("tfnsw_csv", resource["url"])
        stage = "discover_tfnsw_metadata"
        document = tfnsw_metadata_resource(catalogue)
        report["tfnsw_selected_metadata"] = {key: document.get(key) for key in ["id", "name", "description", "format", "url"]}
        download("tfnsw_metadata", document["url"])
        page = download("abs_page", ABS).read_text(encoding="utf-8")
        stage = "discover_abs_boundary"
        download("abs_boundary", abs_boundary_url(page))
        osm = json.loads(download("osm", OSM_URL).read_text(encoding="utf-8-sig"))
        stage = "check_osm_response"
        if osm.get("remark") or not isinstance(osm.get("elements"), list):
            raise ValueError("Overpass returned a partial/error response; candidate is incomplete")
        download("jolt", JOLT_URL)
        page = download("nrma_page", NRMA_URL).read_text(encoding="utf-8")
        stage = "discover_nrma_map"
        download("nrma_map", nrma_map_url(page))
        report.update(complete=True, status="downloaded_for_review")
    except Exception as exc:
        report.update(status="failed", error={"stage": stage, "type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        _write_report(report_path, report)
    return report_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="Unique candidate label; an existing directory is never overwritten")
    parser.add_argument("--tfnsw-resource-id", help="Exact catalogue CSV resource ID, including an explicitly requested historical resource")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = stage_candidates(args.label, tfnsw_resource_id=args.tfnsw_resource_id)
    print(f"Downloaded candidate sources for review: {report}")


if __name__ == "__main__":
    main()
