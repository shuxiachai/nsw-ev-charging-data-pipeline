-- Run LOAD spatial in each new connection before spatial queries.
LOAD spatial;
SELECT * FROM dc_augmentation_coverage;

-- Operator-reported states in the archived response, never live availability.
-- Capture time is known; underlying equipment observation times are not supplied.
SELECT c.source_row,l.address,j.station_code,j.network_status_snapshot,
       j.evse_status_snapshot,s.retrieved_at_utc AS response_captured_at,s.url
FROM jolt_site_match m JOIN location l USING(location_id)
JOIN charger_record c USING(location_id) JOIN jolt_site j USING(jolt_id)
JOIN source_snapshot s ON s.source_file=j.source_file
WHERE c.charger_type='DC' ORDER BY c.source_row;

-- Attribute coverage overlaps. Keep source observations separate from locations.
WITH dc AS (SELECT DISTINCT location_id FROM charger_record WHERE charger_type='DC')
SELECT a.scope, a.attribute, count(DISTINCT a.location_id) AS covered_dc_locations,
       count(*) AS source_observations,
       round(100.0 * count(DISTINCT a.location_id) / nullif((SELECT count(*) FROM dc),0),2) AS percent_all_dc
FROM augmentation a JOIN dc USING(location_id)
GROUP BY a.scope,a.attribute ORDER BY a.scope,a.attribute;

-- Audited same-site membership does not sum heterogeneous plug observations.
SELECT review_id, source_row, original_location_id, location_id, representative_record_id, reason
FROM reviewed_identity ORDER BY review_id,source_row;

-- Reviewed withheld links are distinct from malformed or proven wrong sites.
SELECT source_row,ocm_id,decision,reason,evidence_source_file,supporting_source_file
FROM reviewed_match_exclusion ORDER BY source_row,ocm_id;

-- Regional statistics use the reviewed regional view, which contains no points.
-- Preserve the location grain: never count a location once per plug or attribute.
SELECT r.sa4_code, r.sa4_name, count(d.location_id) AS dc_location_count
FROM region r LEFT JOIN (
    SELECT v.location_id,v.sa4_code FROM regional_analysis_locations v
    WHERE EXISTS (SELECT 1 FROM charger_record c WHERE c.location_id=v.location_id AND c.charger_type='DC')
) d USING (sa4_code)
GROUP BY r.sa4_code, r.sa4_name ORDER BY dc_location_count DESC;

-- Point-derived and independently reviewed SA4 are separate observations.
SELECT q.source_row,q.locality_name,q.source_point_sa4_code,q.reviewed_sa4_code,
       q.coordinate_status,q.method,e.role,e.locator,s.url
FROM reviewed_region q JOIN reviewed_region_evidence e USING(review_id)
JOIN source_snapshot s USING(source_file) ORDER BY q.source_row,e.role;

SELECT code, severity, count(*) AS issue_count
FROM quality_issue GROUP BY code, severity ORDER BY issue_count DESC;

-- Independent verification of exact point-in-polygon assignments.
SELECT l.location_id, l.address, r.sa4_name
FROM location l JOIN region r USING (sa4_code)
WHERE l.sa4_method='point_in_polygon' AND NOT ST_Intersects(l.geometry,r.geometry);

-- Audit approximate coastline cases separately.
SELECT location_id,address,sa4_code,sa4_method,sa4_distance_m
FROM location WHERE sa4_method <> 'point_in_polygon';

-- Representative source-to-external matching evidence.
SELECT l.address, e.title, e.address AS external_address, m.distance_m,
       m.address_similarity, e.last_verified, e.source_url
FROM site_match m JOIN location l USING(location_id) JOIN external_site e USING(ocm_id)
ORDER BY m.distance_m DESC LIMIT 20;

-- Final conflicts after both resolution stages; preserve the full DC denominator.
SELECT c.source_row, l.address, l.original_postcode, l.postcode, l.sa4_code
FROM location l JOIN charger_record c USING(location_id)
WHERE l.address_conflict ORDER BY c.source_row;

-- Reviewed corrections are distinct from the automatic stage's audit history.
SELECT r.source_row, l.address, r.coordinate_element_id,
       r.corroborating_element_id, r.evidence_distance_m,
       r.coordinate_change_m, s.url AS address_evidence_url
FROM reviewed_resolution r
JOIN charger_record c USING(record_id) JOIN location l USING(location_id)
JOIN source_snapshot s ON s.source_file=r.address_source_file
ORDER BY r.source_row;

-- Power from every source record, including nonrepresentative rows at one site.
-- Do not sum these ranges into station capacity.
SELECT * FROM location_power_observations ORDER BY location_id,source_row;

-- Reported interface, count and source status are separate observations.
-- IsOperational is an OCM status classification, not live availability.
SELECT m.location_id,e.ocm_id,e.status AS site_status,c.connection_id,
       c.connection_type,c.quantity,c.status_type_id,c.status AS connector_status,
       c.is_operational,e.last_verified_at,s.retrieved_at_utc AS response_captured_at
FROM site_match m JOIN external_site e USING(ocm_id)
JOIN external_connector c USING(ocm_id) JOIN source_snapshot s USING(source_file)
WHERE c.current_type_id=30 ORDER BY e.ocm_id,c.connection_id;

-- Keep the parking-hours note as supplied, without inventing days of operation.
SELECT m.location_id,j.station_code,j.carpark_hours_text,s.retrieved_at_utc,s.url
FROM jolt_site_match m JOIN jolt_site j USING(jolt_id)
JOIN source_snapshot s USING(source_file)
WHERE j.carpark_hours_text IS NOT NULL ORDER BY m.location_id;

-- A review queue, not a labelled accuracy estimate: inspect the preserved raw
-- evidence with the corresponding rejected/ambiguous candidate CSVs.
SELECT m.location_id,l.address,m.osm_id,m.distance_m,o.address AS external_address,
       o.source_url
FROM osm_site_match m JOIN location l USING(location_id) JOIN osm_site o USING(osm_id)
WHERE nullif(trim(o.address),'') IS NULL AND m.distance_m>=50
ORDER BY m.distance_m DESC,m.location_id;

-- Ampol labels are published site observations, not surveyed equipment counts.
-- The complete EVCharging service list retains original bay labels and text.
SELECT c.source_row,l.address,s.ampol_id,s.name,s.dc_connector_types,
       m.distance_m,m.address_similarity,p.retrieved_at_utc,s.source_url
FROM amp_charge_site_match m JOIN amp_charge_site s USING(ampol_id)
JOIN location l USING(location_id) JOIN charger_record c USING(location_id)
JOIN source_snapshot p USING(source_file)
WHERE c.charger_type='DC' ORDER BY c.source_row;
