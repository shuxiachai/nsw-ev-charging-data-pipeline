# JOLT per-station status snapshot evidence — 9 September 2026

The existing official map contains two useful station observations beyond its
station code: `networkStatus` and `evseStatus`. The parser now retains these
separately. They are values reported in an archived operator response, not live
availability, verified hardware uptime, connector counts, or December 2025
measurements. The older, separate `status` field is not used to create these
attributes, and a missing field never defaults to `active` or `available`.

## Sources and time semantics

The observations come from the unmodified [official Australian map](https://joltcharge.com/au/find-a-charger/),
stored as `data/raw/jolt_map.html`:

- SHA-256: `82a66d3632a52c8e88f7aa2c4f3f7ed84b0e2af3efc746b9c91e2b537601e915`.
- Response retrieval time: `2026-09-06T05:00:00.972541+00:00`.
- HTTP Last-Modified: `Sun, 06 Sep 2026 04:50:29 GMT`.
- 173 distinct map IDs, each with its own address, coordinates and both fields.

The retrieval time records when the project obtained the page. The page may
have been cached, and the underlying EVSE measurement times are not supplied.
Consequently a snapshot value such as `available` is never a promise that the
charger is usable now. Its provenance joins to the same `source_snapshot` as
the station-code observation; no new observation date is fabricated.

The public JavaScript actually linked by that archived page was separately
downloaded using the project's normal `fetch` function and an expected hash:

- File: `data/raw/jolt_details_map_app_20260909.js` and its standard `.meta.json`.
- [Official script URL](https://joltcharge.com/au/wp-content/themes/jolt/dist/js/app.js?id=8de5c10e7baf820327a111a8a6903e24&ver=1.0.0).
- SHA-256: `a76834802c206dffcbf71fce08c85b999204981866bbd8e72d28805c40418fc3`.
- Length: 470,149 bytes; retrieved `2026-09-09T03:21:15.698220+00:00`.
- HTTP Last-Modified: `Wed, 05 Aug 2026 05:52:53 GMT`.

This JavaScript is archived evidence of field usage, not an additional network
request required by every build and not the source of the state values. Builds
parse the existing map as JSON without running the site's JavaScript or using
embedded keys, authenticated services or a charging-session API.

## Why these are station observations

The minified script can be inspected using these literal locators:

1. `window.jolt.charging_points` is enumerated into distinct map entities.
2. On a selected station's marker click, `hardwareStatus:s.evseStatus` passes
   that entity's field into the information window (around character 25344).
3. The station card's footer displays `s.hardwareStatus` as its status text
   (around character 33237), rather than replacing it with a fixed label.
4. `t.networkStatus` is passed into the per-station marker function (around
   character 34319); the function explicitly tests `long-term unavailable`
   when choosing its marker. The network and EVSE fields retain separate meanings.

The exact IDs have nonuniform reported values. These fields are not the site's
filter options or a single initial map default. Nor does this evidence establish
independent ground truth: it establishes what the operator page reports about
each identified station.

## Extraction and relational mapping

|Map field|`jolt_site` / processed site column|Site augmentation attribute|
|---|---|---|
|`networkStatus`|`network_status_snapshot`|`operator_network_status_snapshot`|
|`evseStatus`|`evse_status_snapshot`|`operator_evse_status_snapshot`|

`snapshot_status(value, field)` trims and lowercases strings. Missing values,
empty strings, `unknown` and `n/a` become NULL and produce no augmentation.
Unexpected nonempty values and non-string values raise an explicit error so
upstream changes cannot silently become meaningful attributes. This contract
uses the states actually observed in the source snapshot:

- Network: `available`, `temporarily unavailable`, `long-term unavailable`.
- EVSE: `available`, `occupied`, `out of order`, `unavailable`.

The fields are independent: for example, network `available` and EVSE `out of
order` are both retained without choosing one or deriving a combined flag.
The existing raw field `status` remains a separate observation in `jolt_site`;
it never supplies a missing network or EVSE value.

The matching algorithm, thresholds, original source records and JOLT IDs are
unchanged. Only an already accepted source-location/JOLT-ID association can
receive the new observations, each with `scope='site'`, its JOLT ID,
`source_file='data/raw/jolt_map.html'` and the existing
`coordinate_operator_address_match` method. Unmatched map entries remain in
the external-site table without creating source-location augmentation.

## Observed coverage and distributions

At the isolated integration-check stage, the current 41 accepted JOLT matches
were unchanged. The complete source enumeration is retained by the raw map and
the regenerated 173-row `data/processed/jolt_sites.csv`; accepted identities
are retained in `data/processed/jolt_site_matches.csv` and candidate audits.

|Reported field/state|All 173 map points|41 accepted matches|32 previously code-only matches|
|---|---:|---:|---:|
|Network available|152|37|28|
|Network long-term unavailable|20|4|4|
|Network temporarily unavailable|1|0|0|
|EVSE available|115|19|15|
|EVSE occupied|15|7|6|
|EVSE out of order|42|15|11|
|EVSE unavailable|1|0|0|

This adds 82 source observations, not 82 newly covered locations. Against that
430-location DC snapshot, the number with a non-identifier site observation
rises from 199 to 231 (53.72%); the 32 formerly code-only locations receive
reported states. Overall site coverage remains 231, and the denominator does
not change. These figures describe the JOLT extraction change in isolation;
`outputs/validation.json` and generated composition CSVs are authoritative if
later matching reviews alter accepted identities.

The final combined improvement has 233/430 site and non-identifier coverage;
see [the integrated self-check](improvement_self_check_20260909.md). Excluding
status and station codes leaves 200/430 with other site attributes.

Source-provided status snapshots are substantive station observations, but
their short lifetime is a limitation. They do not establish a 50% threshold
specifically for static connector, power, fee or access attributes. The project
must not rename their coverage as such, nor use image filenames or a generic
network FAQ to invent per-site power, sockets or prices.

## Focused verification

The 52 focused tests in `tests/test_jolt_snapshots.py` and
`tests/test_edge_matching.py` passed at implementation. Tests verify real raw
ID-to-value equality, unchanged accepted match pairs and raw hashes, nullable
state behavior, independent field meanings, rejected unknown/nontext states,
absence of a legacy-status fallback, and no augmentation for unmatched IDs.
The independent database checks additionally compare every persisted JOLT
state and state augmentation with the original map and accepted relationship.
The final source check also binds actual bytes and manifest URL/hash/size/capture
time to the database snapshot. Metadata mutation tests cover each persisted field.
These checks validate extraction and provenance; they do not measure matching
precision or real-world charger uptime.
