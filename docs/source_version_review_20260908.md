# TfNSW source-version investigation — 8 September 2026

**Status: current official resource verified; December 2025 historical-content interpretation remains unresolved.** The project cache is byte-for-byte identical to the file currently served by TfNSW. However, the official publication metadata and public activity history do not establish that these bytes represent an unchanged December 2025 snapshot. No raw input was replaced, and no question or message was sent to the course staff or data publisher.

This note records an investigation conducted on 2026-09-08, approximately 12:25–12:27 UTC (22:25–22:27 Sydney time). It is evidence for the version limitation and a prepared course question, not a course ruling or an instruction to change the dataset.

## What was checked

Read-only HTTPS GET requests were made to the current official TfNSW, Data.NSW and data.gov.au CKAN catalogues; their public activity lists; and the exact historical download URLs found in TfNSW's activity records. Downloaded responses were inspected in memory. The supplied `data/raw/ev_20251216.csv` and its manifest were read without modification. The web search results were used to locate official pages; older search-index dates were not treated as the current resource's observation date.

## Findings

### 1. All three current catalogues point to the same TfNSW file

At 12:25:35 UTC, all three official APIs returned HTTP 200 with `success=true`, and their current “EV Charging Locations in NSW” entries pointed to the same TfNSW resource, `7bbb6461-e52d-4fe7-ace4-a15c30198de0`, with a download filename of `ev_20251216.csv`. Data.NSW and data.gov.au therefore did not expose an independently dated December copy in their current resource lists. Sources: [TfNSW catalogue API](https://opendata.transport.nsw.gov.au/api/3/action/package_show?id=ev-charging-locations), [Data.NSW catalogue API](https://data.nsw.gov.au/data/api/3/action/package_show?id=2-ev-charging-locations), [data.gov.au catalogue API](https://data.gov.au/data/api/3/action/package_show?id=nsw-2-ev-charging-locations).

The live TfNSW resource had these fields:

| Field | Observed value |
| --- | --- |
| Resource ID | `7bbb6461-e52d-4fe7-ace4-a15c30198de0` |
| Filename | `ev_20251216.csv` |
| Description | `Effective 20 April 2026` |
| Resource created | `2024-09-13T01:49:05.536121` |
| Resource last modified | `2026-04-20T00:33:22.518559` |
| Resource metadata modified | `2026-04-20T00:33:22.574482` |

The documentation resource was also described as effective 20 April 2026 and linked to `ev-charging-locations-v2.1.pdf`. A resource's creation date is its catalogue-entry date; it does not prove that the currently downloadable contents existed on that date. Dataset-level metadata changes in July 2026 likewise do not establish a July observation date for each charging station. Source: [TfNSW catalogue API](https://opendata.transport.nsw.gov.au/api/3/action/package_show?id=ev-charging-locations).

### 2. The existing cache matches the current official response exactly

A fresh in-memory GET of the [current official CSV](https://opendata.transport.nsw.gov.au/data/dataset/be1c4de4-4517-4bd0-8a09-2965ddfc7179/resource/7bbb6461-e52d-4fe7-ace4-a15c30198de0/download/ev_20251216.csv) returned:

| Observation | Value |
| --- | --- |
| HTTP status | `200` |
| Response bytes | `283033` |
| SHA-256 | `43970e7751b951ab459a1be7bfd6141756c60ff8aa797debf11c5a597109865a` |
| HTTP Last-Modified | `Mon, 20 Apr 2026 00:33:22 GMT` |
| HTTP ETag | `"1776645202.651-283033-2219905807"` |
| Match to project CSV and existing manifest | Exact |

This confirms that the project did not accidentally use different bytes from the presently published resource. It cannot prove the content's historical observation date. In particular, the filename date, HTTP upload/modification date and dates when individual sites were observed are different concepts.

### 3. Official activity history supplies stronger publication evidence, but no December snapshot

The [TfNSW public activity API](https://opendata.transport.nsw.gov.au/api/3/action/package_activity_list?id=ev-charging-locations&limit=100&include_data=true) returned 33 events. Among the events returned, the relevant resource changed from a September 2025 CSV to a December-named spreadsheet in April 2026, followed by the current CSV. The following are selected event fields, in chronological order; timestamps are reproduced as returned by the API, which does not append a timezone offset to these strings.

| Activity timestamp | Activity ID | Resource filename | Resource description | Recorded bytes |
| --- | --- | --- | --- | ---: |
| `2025-09-03T04:00:48.998453` | `41903041-c5a0-49d4-b764-a53a0898020c` | `ev_chargers_consolidated_sep25.csv` | `Effective 2 September 2025` | 214633 |
| `2026-04-19T23:57:11.003093` | `958deff7-4b3c-41aa-a32f-3c6d416e1283` | `ev_20251216.xlsx` | `Effective 20 April 2026` | 180429 |
| `2026-04-20T00:33:23.201687` | `6842a1d8-58b5-4c11-bd2e-2f380ee1c5af` | `ev_20251216.csv` | `Effective 20 April 2026` | 283033 |

No December 2025 publication event was present in the returned list. This is a finding about the available public activity records, not proof that no December observation or unpublished snapshot ever existed. The differing XLSX and CSV byte counts do not, by themselves, establish a change in station content because the formats differ. Source: [TfNSW public activity API](https://opendata.transport.nsw.gov.au/api/3/action/package_activity_list?id=ev-charging-locations&limit=100&include_data=true).

The [Data.NSW activity API](https://data.nsw.gov.au/data/api/3/action/package_activity_list?id=2-ev-charging-locations&limit=100&include_data=true) returned 9 events. Its September 2025 catalogue entries linked to the September-named CSV; its 20 April 2026 entry linked to the current December-named CSV. The [data.gov.au activity API](https://data.gov.au/data/api/3/action/package_activity_list?id=nsw-2-ev-charging-locations&limit=100&include_data=true) returned a successful empty list. Neither supplied an independently recoverable December snapshot in this check.

### 4. Historical filename URLs currently return the current bytes

Five distinct download URLs associated with the same resource ID were found in the official TfNSW activity response. Every one returned HTTP 200, 283033 bytes, the same SHA-256 shown above, and the same April 2026 Last-Modified header when checked at 12:27 UTC:

| URL obtained from official history | Result |
| --- | --- |
| [Current December-named CSV](https://opendata.transport.nsw.gov.au/data/dataset/be1c4de4-4517-4bd0-8a09-2965ddfc7179/resource/7bbb6461-e52d-4fe7-ace4-a15c30198de0/download/ev_20251216.csv) | Current bytes |
| [December-named XLSX path](https://opendata.transport.nsw.gov.au/data/dataset/be1c4de4-4517-4bd0-8a09-2965ddfc7179/resource/7bbb6461-e52d-4fe7-ace4-a15c30198de0/download/ev_20251216.xlsx) | Current bytes |
| [September 2025 CSV path](https://opendata.transport.nsw.gov.au/data/dataset/be1c4de4-4517-4bd0-8a09-2965ddfc7179/resource/7bbb6461-e52d-4fe7-ace4-a15c30198de0/download/ev_chargers_consolidated_sep25.csv) | Current bytes |
| [Earlier XLSX path under /data/dataset](https://opendata.transport.nsw.gov.au/data/dataset/be1c4de4-4517-4bd0-8a09-2965ddfc7179/resource/7bbb6461-e52d-4fe7-ace4-a15c30198de0/download/nsw_ev_chargers.xlsx) | Current bytes |
| [Earlier XLSX path under /dataset](https://opendata.transport.nsw.gov.au/dataset/be1c4de4-4517-4bd0-8a09-2965ddfc7179/resource/7bbb6461-e52d-4fe7-ace4-a15c30198de0/download/nsw_ev_chargers.xlsx) | Current bytes |

The server also echoed the requested filename in Content-Disposition. Consequently, changing only the URL's filename suffix does **not** recover a historical file in these observed cases. A successful download or a historical-looking filename must not be counted as historical-content verification. This conclusion follows from the direct byte comparisons above, rather than an assumption about CKAN routing internals.

## Decision for this project

Keep the existing immutable raw input and its manifest. It is the currently published official file, it carries a December 2025 date in its filename, and its identity is now independently rechecked. Do not replace it with a supposedly historical path: the tested paths served the same current content.

The investigation **does not resolve course acceptance of the version**. Two plausible interpretations remain: the named file may be a December collection published later, or it may contain updates that make the filename an unreliable reference-period label. The official facts above do not choose between those interpretations. The course staff must clarify whether the currently served `ev_20251216.csv` is the intended input, or supply an authoritative historical snapshot or checksum if strict December contents are required.

Facts to verify and explain in the team's report: the official filename, the
different effective date, the raw-file checksum, the date of this verification,
the identical bytes served by historical filename URLs, and the unresolved
distinction between publication date and the observation period of each record.

## Prepared Ed question — not sent

**Title:** Assignment 1: intended TfNSW December 2025 dataset version

Hi teaching team, Assignment 1 asks us to use the December 2025 NSW EV charging dataset. The current TfNSW, Data.NSW and data.gov.au catalogues all link to `ev_20251216.csv`, but TfNSW describes it as “Effective 20 April 2026” and its HTTP Last-Modified date is 20 April 2026. The public activity history first records this CSV filename in April 2026; older filename URLs now return identical bytes. Could you confirm whether this currently served file is the intended assignment input? If a strict December 2025 snapshot is required, could you provide the authoritative download or checksum? We have retained the raw data and documented the date discrepancy.

## Evidence identifiers

These hashes identify the in-memory response bodies observed during this investigation; complete new API response files were not added to `data/raw`.

| Response | Checked at UTC | SHA-256 |
| --- | --- | --- |
| TfNSW current catalogue | `2026-09-08T12:25:35` | `9f8e4e2533386d85b74e5969e0feaf29a9788db8052195d2d458e973fc158904` |
| Data.NSW current catalogue | `2026-09-08T12:25:35` | `17032cb0057df4caf82250bd42a08e72c9a4be87b7b7a789416743a917930fd0` |
| data.gov.au current catalogue | `2026-09-08T12:25:35` | `e94284e9762ce11823a09e9120126b2acd479525e2d7670006b768252e888df1` |
| TfNSW public activity response | `2026-09-08T12:27:06` | `b8a6afb012f2e5f4320a45a5ea9c1167c473a40105cf57f5a9d05bfc62a96711` |
| Current CSV; also returned by all five tested download URLs | `2026-09-08T12:25:35` and `12:27:06–12:27:07` | `43970e7751b951ab459a1be7bfd6141756c60ff8aa797debf11c5a597109865a` |
