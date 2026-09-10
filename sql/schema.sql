-- All geometry columns use longitude/latitude WGS84 (EPSG:4326).
-- INSTALL spatial is performed by the Python setup when online; LOAD is needed
-- for each DuckDB connection. This DDL is for a new, empty database.
LOAD spatial;

CREATE TABLE source_snapshot (
    source_file VARCHAR PRIMARY KEY,
    url VARCHAR NOT NULL,
    retrieved_at_utc TIMESTAMPTZ NOT NULL,
    sha256 VARCHAR NOT NULL CHECK (regexp_full_match(sha256,'[0-9a-f]{64}')),
    byte_count BIGINT NOT NULL CHECK (byte_count > 0)
);
CREATE TABLE region (
    sa4_code VARCHAR PRIMARY KEY,
    sa4_name VARCHAR NOT NULL,
    asgs_edition INTEGER NOT NULL CHECK (asgs_edition = 4),
    geometry GEOMETRY NOT NULL
);
CREATE TABLE operator (
    operator_id VARCHAR PRIMARY KEY,
    operator_name VARCHAR UNIQUE NOT NULL
);
CREATE TABLE location (
    location_id VARCHAR PRIMARY KEY,
    operator_id VARCHAR NOT NULL REFERENCES operator(operator_id),
    station_name VARCHAR,
    address VARCHAR NOT NULL,
    latitude DOUBLE CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE CHECK (longitude BETWEEN -180 AND 180),
    postcode VARCHAR,
    address_postcode VARCHAR,
    address_conflict BOOLEAN NOT NULL,
    source_lga VARCHAR,
    sa4_code VARCHAR REFERENCES region(sa4_code),
    sa4_method VARCHAR NOT NULL CHECK (sa4_method IN
        ('point_in_polygon','coastal_nearest_within_50m','ambiguous','unmatched','invalid_coordinates')),
    sa4_distance_m DOUBLE CHECK (isfinite(sa4_distance_m) AND sa4_distance_m >= 0),
    original_latitude DOUBLE,
    original_longitude DOUBLE,
    original_postcode VARCHAR,
    original_address_conflict BOOLEAN NOT NULL,
    resolution_method VARCHAR NOT NULL,
    geometry GEOMETRY,
    CHECK ((sa4_method='point_in_polygon' AND sa4_code IS NOT NULL
            AND sa4_distance_m IS NOT NULL AND sa4_distance_m=0)
        OR (sa4_method='coastal_nearest_within_50m' AND sa4_code IS NOT NULL
            AND sa4_distance_m IS NOT NULL AND sa4_distance_m BETWEEN 0 AND 50)
        OR (sa4_method IN ('ambiguous','unmatched','invalid_coordinates')
            AND sa4_code IS NULL AND sa4_distance_m IS NULL))
);
CREATE TABLE charger_record (
    record_id VARCHAR PRIMARY KEY,
    location_id VARCHAR NOT NULL REFERENCES location(location_id),
    source_row INTEGER UNIQUE NOT NULL CHECK (source_row > 0),
    source_objectid VARCHAR,
    charger_type VARCHAR NOT NULL CHECK (charger_type IN ('AC','DC','UPCOMING','UNKNOWN')),
    number_of_plugs INTEGER CHECK (number_of_plugs > 0),
    power_min_kw DOUBLE CHECK (isfinite(power_min_kw) AND power_min_kw > 0),
    power_max_kw DOUBLE CHECK (isfinite(power_max_kw) AND power_max_kw > 0 AND power_max_kw >= power_min_kw),
    power_kind VARCHAR NOT NULL,
    power_raw VARCHAR NOT NULL,
    source_category VARCHAR,
    raw_json JSON NOT NULL,
    CHECK ((power_min_kw IS NULL) = (power_max_kw IS NULL))
);
-- Verified same-site observations retain their own source rows and coordinates.
CREATE TABLE reviewed_identity (
    record_id VARCHAR PRIMARY KEY REFERENCES charger_record(record_id),
    source_row INTEGER NOT NULL,
    review_id VARCHAR NOT NULL,
    original_location_id VARCHAR NOT NULL,
    location_id VARCHAR NOT NULL REFERENCES location(location_id),
    representative_record_id VARCHAR NOT NULL REFERENCES charger_record(record_id),
    source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    reason VARCHAR NOT NULL,
    review_date DATE NOT NULL
);
CREATE TABLE reviewed_identity_evidence (
    review_id VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    role VARCHAR NOT NULL,
    element_id VARCHAR,
    sha256 VARCHAR NOT NULL CHECK (regexp_full_match(sha256,'[0-9a-f]{64}')),
    PRIMARY KEY (review_id,source_file,role)
);
CREATE TABLE external_site (
    ocm_id BIGINT PRIMARY KEY,
    ocm_operator_id BIGINT,
    ocm_operator VARCHAR,
    title VARCHAR,
    address VARCHAR,
    town VARCHAR,
    postcode VARCHAR,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    usage_cost VARCHAR,
    access_comments VARCHAR,
    usage_type VARCHAR,
    status VARCHAR,
    last_verified VARCHAR,
    last_verified_at TIMESTAMPTZ,
    number_of_points INTEGER CHECK (number_of_points >= 0),
    data_provider VARCHAR,
    data_license VARCHAR,
    source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    source_url VARCHAR NOT NULL,
    has_dc BOOLEAN NOT NULL
);
CREATE TABLE external_connector (
    ocm_id BIGINT NOT NULL REFERENCES external_site(ocm_id),
    connection_id BIGINT NOT NULL,
    connection_type VARCHAR,
    current_type_id INTEGER,
    power_kw DOUBLE CHECK (isfinite(power_kw) AND power_kw >= 0),
    quantity INTEGER CHECK (quantity >= 0),
    status_type_id INTEGER,
    status VARCHAR,
    is_operational BOOLEAN,
    PRIMARY KEY (ocm_id, connection_id)
);
CREATE TABLE site_match (
    location_id VARCHAR PRIMARY KEY REFERENCES location(location_id),
    ocm_id BIGINT UNIQUE NOT NULL REFERENCES external_site(ocm_id),
    distance_m DOUBLE NOT NULL CHECK (distance_m >= 0 AND distance_m <= 250),
    address_similarity DOUBLE NOT NULL CHECK (address_similarity BETWEEN 0 AND 1),
    score DOUBLE NOT NULL,
    method VARCHAR NOT NULL,
    address_exception_review_id VARCHAR,
    address_exception_source_file VARCHAR REFERENCES source_snapshot(source_file),
    CHECK ((address_exception_review_id IS NULL) = (address_exception_source_file IS NULL))
);
-- A reviewed withholding keeps the original external observation available,
-- while excluding only the unsupported source-location/external-site link.
CREATE TABLE reviewed_match_exclusion (
    review_id VARCHAR PRIMARY KEY,
    record_id VARCHAR NOT NULL REFERENCES charger_record(record_id),
    source_row INTEGER NOT NULL,
    location_id VARCHAR NOT NULL REFERENCES location(location_id),
    ocm_id BIGINT NOT NULL REFERENCES external_site(ocm_id),
    source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    external_source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    evidence_source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    supporting_source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    decision VARCHAR NOT NULL CHECK (decision='withheld_pending_location_evidence'),
    reason VARCHAR NOT NULL,
    review_date DATE NOT NULL,
    UNIQUE(record_id,ocm_id)
);
CREATE TABLE osm_site (
    osm_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    operator_name VARCHAR,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    address VARCHAR,
    dc_connector_types VARCHAR,
    opening_hours VARCHAR,
    access VARCHAR,
    fee VARCHAR,
    website VARCHAR,
    tags_json JSON NOT NULL,
    source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    source_url VARCHAR NOT NULL
);
CREATE TABLE osm_site_match (
    location_id VARCHAR PRIMARY KEY REFERENCES location(location_id),
    osm_id VARCHAR UNIQUE NOT NULL REFERENCES osm_site(osm_id),
    distance_m DOUBLE NOT NULL CHECK (distance_m >= 0 AND distance_m <= 250),
    address_similarity DOUBLE NOT NULL,
    score DOUBLE NOT NULL,
    method VARCHAR NOT NULL
);
CREATE TABLE jolt_site (
    jolt_id BIGINT PRIMARY KEY,
    station_code VARCHAR NOT NULL,
    description VARCHAR,
    address VARCHAR NOT NULL,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    status_snapshot VARCHAR,
    network_status_snapshot VARCHAR CHECK (network_status_snapshot IN
        ('available','temporarily unavailable','long-term unavailable')),
    evse_status_snapshot VARCHAR CHECK (evse_status_snapshot IN
        ('available','occupied','unavailable','out of order')),
    carpark_hours_text VARCHAR,
    source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    source_url VARCHAR NOT NULL
);
CREATE TABLE jolt_site_match (
    location_id VARCHAR PRIMARY KEY REFERENCES location(location_id),
    jolt_id BIGINT UNIQUE NOT NULL REFERENCES jolt_site(jolt_id),
    distance_m DOUBLE NOT NULL CHECK (distance_m >= 0 AND distance_m <= 250),
    address_similarity DOUBLE NOT NULL,
    score DOUBLE NOT NULL,
    method VARCHAR NOT NULL
);
-- Publisher-provided connector observations from individual Ampol venue pages.
-- These are dated publication claims, not live state or a complete bay inventory.
CREATE TABLE amp_charge_site (
    ampol_id VARCHAR PRIMARY KEY,
    guid VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    address VARCHAR NOT NULL,
    address_raw VARCHAR NOT NULL,
    postcode VARCHAR NOT NULL,
    latitude DOUBLE NOT NULL CHECK (isfinite(latitude) AND latitude BETWEEN -90 AND 90),
    longitude DOUBLE NOT NULL CHECK (isfinite(longitude) AND longitude BETWEEN -180 AND 180),
    dc_connector_types VARCHAR,
    ev_charging_json JSON NOT NULL,
    source_file VARCHAR UNIQUE NOT NULL REFERENCES source_snapshot(source_file),
    source_url VARCHAR NOT NULL,
    has_dc BOOLEAN NOT NULL
);
CREATE TABLE amp_charge_site_match (
    location_id VARCHAR PRIMARY KEY REFERENCES location(location_id),
    ampol_id VARCHAR UNIQUE NOT NULL REFERENCES amp_charge_site(ampol_id),
    distance_m DOUBLE NOT NULL CHECK (isfinite(distance_m) AND distance_m BETWEEN 0 AND 250),
    address_similarity DOUBLE NOT NULL CHECK (address_similarity BETWEEN 0 AND 1),
    score DOUBLE NOT NULL CHECK (isfinite(score)),
    method VARCHAR NOT NULL
);
CREATE TABLE augmentation (
    augmentation_id VARCHAR PRIMARY KEY,
    location_id VARCHAR NOT NULL REFERENCES location(location_id),
    attribute VARCHAR NOT NULL,
    value VARCHAR NOT NULL CHECK (length(value) > 0),
    scope VARCHAR NOT NULL CHECK (scope IN ('site','operator')),
    ocm_id BIGINT REFERENCES external_site(ocm_id),
    ocm_operator_id BIGINT,
    osm_id VARCHAR REFERENCES osm_site(osm_id),
    jolt_id BIGINT REFERENCES jolt_site(jolt_id),
    ampol_id VARCHAR REFERENCES amp_charge_site(ampol_id),
    source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    method VARCHAR NOT NULL,
    CHECK ((scope = 'site' AND ocm_operator_id IS NULL AND
            ((ocm_id IS NOT NULL)::INTEGER + (osm_id IS NOT NULL)::INTEGER + (jolt_id IS NOT NULL)::INTEGER
                + (ampol_id IS NOT NULL)::INTEGER) = 1)
        OR (scope = 'operator' AND ampol_id IS NULL AND
            ((ocm_operator_id IS NOT NULL AND ocm_id IS NULL AND osm_id IS NULL AND jolt_id IS NULL)
             OR (ocm_operator_id IS NULL AND jolt_id IS NULL AND
                 ((ocm_id IS NOT NULL)::INTEGER + (osm_id IS NOT NULL)::INTEGER)=1
                 AND attribute IN ('operator_website','operator_network_map_url')))))
);
CREATE TABLE source_resolution (
    record_id VARCHAR PRIMARY KEY REFERENCES charger_record(record_id),
    source_row INTEGER NOT NULL,
    decision VARCHAR NOT NULL CHECK (decision IN ('resolved','unresolved')),
    reason VARCHAR NOT NULL,
    source_address VARCHAR NOT NULL,
    old_latitude DOUBLE,
    old_longitude DOUBLE,
    old_postcode VARCHAR,
    new_latitude DOUBLE,
    new_longitude DOUBLE,
    new_postcode VARCHAR,
    ocm_id BIGINT REFERENCES external_site(ocm_id),
    osm_id VARCHAR REFERENCES osm_site(osm_id),
    address_similarity DOUBLE,
    cross_source_distance_m DOUBLE,
    coordinate_change_m DOUBLE,
    ocm_source_file VARCHAR REFERENCES source_snapshot(source_file),
    CHECK (decision='unresolved' OR (ocm_id IS NOT NULL AND osm_id IS NOT NULL
        AND new_latitude IS NOT NULL AND new_latitude BETWEEN -90 AND 90
        AND new_longitude IS NOT NULL AND new_longitude BETWEEN -180 AND 180
        AND new_postcode IS NOT NULL AND regexp_full_match(new_postcode, '[0-9]{4}')
        AND address_similarity IS NOT NULL AND cross_source_distance_m IS NOT NULL
        AND address_similarity BETWEEN 0.85 AND 1 AND cross_source_distance_m BETWEEN 0 AND 150))
);
-- A separate reviewed stage supplements automatic OCM/OSM resolution without
-- inventing missing source IDs or hiding the automatic stage's original result.
CREATE TABLE reviewed_resolution (
    record_id VARCHAR PRIMARY KEY REFERENCES charger_record(record_id),
    source_row INTEGER NOT NULL,
    decision VARCHAR NOT NULL CHECK (decision = 'resolved'),
    old_latitude DOUBLE NOT NULL,
    old_longitude DOUBLE NOT NULL,
    old_postcode VARCHAR,
    new_latitude DOUBLE NOT NULL CHECK (new_latitude BETWEEN -90 AND 90),
    new_longitude DOUBLE NOT NULL CHECK (new_longitude BETWEEN -180 AND 180),
    new_postcode VARCHAR NOT NULL,
    coordinate_source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    coordinate_element_id VARCHAR NOT NULL,
    corroborating_source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    corroborating_element_id VARCHAR NOT NULL,
    address_source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    evidence_distance_m DOUBLE NOT NULL CHECK (evidence_distance_m BETWEEN 0 AND 150),
    coordinate_change_m DOUBLE NOT NULL CHECK (coordinate_change_m >= 0),
    reason VARCHAR NOT NULL,
    review_date DATE NOT NULL,
    supporting_address_source_file VARCHAR REFERENCES source_snapshot(source_file),
    supporting_address_locator VARCHAR,
    corroborating_role VARCHAR NOT NULL CHECK (corroborating_role IN
        ('same_operator_charger','mapped_landmark')),
    CHECK ((supporting_address_source_file IS NULL) = (supporting_address_locator IS NULL))
);
CREATE TABLE quality_issue (
    issue_id BIGINT PRIMARY KEY,
    record_id VARCHAR NOT NULL REFERENCES charger_record(record_id),
    source_row INTEGER NOT NULL,
    code VARCHAR NOT NULL,
    severity VARCHAR NOT NULL CHECK (severity IN ('info','warning','error')),
    detail VARCHAR NOT NULL
);
-- Regional certainty is distinct from the still-conflicting point coordinates.
-- locality_geometry describes the entire official locality, never a charger bay.
CREATE TABLE reviewed_region (
    review_id VARCHAR PRIMARY KEY,
    record_id VARCHAR UNIQUE NOT NULL REFERENCES charger_record(record_id),
    location_id VARCHAR UNIQUE NOT NULL REFERENCES location(location_id),
    source_row INTEGER NOT NULL,
    source_point_sa4_code VARCHAR NOT NULL REFERENCES region(sa4_code),
    reviewed_sa4_code VARCHAR NOT NULL REFERENCES region(sa4_code),
    method VARCHAR NOT NULL CHECK (method='official_locality_containment'),
    locality_name VARCHAR NOT NULL,
    locality_object_id BIGINT NOT NULL,
    locality_postcode VARCHAR NOT NULL CHECK (regexp_full_match(locality_postcode,'[0-9]{4}')),
    locality_source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    operator_source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    operator_element_id VARCHAR NOT NULL,
    coordinate_status VARCHAR NOT NULL CHECK (coordinate_status='unresolved'),
    reason VARCHAR NOT NULL,
    review_date DATE NOT NULL,
    locality_geometry GEOMETRY NOT NULL CHECK (ST_IsValid(locality_geometry) AND NOT ST_IsEmpty(locality_geometry))
);
CREATE TABLE reviewed_region_evidence (
    review_id VARCHAR NOT NULL REFERENCES reviewed_region(review_id),
    source_file VARCHAR NOT NULL REFERENCES source_snapshot(source_file),
    role VARCHAR NOT NULL,
    locator VARCHAR NOT NULL,
    sha256 VARCHAR NOT NULL CHECK (regexp_full_match(sha256,'[0-9a-f]{64}')),
    PRIMARY KEY(review_id,source_file,role)
);
CREATE INDEX location_region_idx ON location(sa4_code);
CREATE INDEX location_geometry_idx ON location USING RTREE(geometry);
CREATE INDEX region_geometry_idx ON region USING RTREE(geometry);
CREATE INDEX charger_location_idx ON charger_record(location_id);
CREATE INDEX augmentation_location_idx ON augmentation(location_id);
CREATE VIEW dc_locations AS
    SELECT l.*, o.operator_name FROM location l JOIN operator o USING(operator_id)
    WHERE EXISTS (SELECT 1 FROM charger_record c WHERE c.location_id=l.location_id AND c.charger_type='DC');
-- Keep unresolved source rows in the full database and denominator, but do not
-- silently use their questionable point/address identity in regional analysis.
CREATE VIEW analysis_ready_locations AS
    SELECT * FROM location WHERE NOT address_conflict AND sa4_code IS NOT NULL;
-- Deliberately expose no point geometry/coordinates in this regional-only view.
-- Unreviewed conflicts are absent; original point SA4 remains separately labelled.
CREATE VIEW regional_analysis_locations AS
    SELECT l.location_id,l.operator_id,l.station_name,l.address,
           coalesce(r.reviewed_sa4_code,l.sa4_code) AS sa4_code,
           l.sa4_code AS source_point_sa4_code,
           coalesce(r.method,l.sa4_method) AS regional_assignment_method,
           r.review_id AS regional_review_id,
           CASE WHEN r.review_id IS NOT NULL THEN 'unresolved' ELSE 'analysis_ready' END AS coordinate_status
    FROM location l LEFT JOIN reviewed_region r USING(location_id)
    WHERE r.review_id IS NOT NULL OR (NOT l.address_conflict AND l.sa4_code IS NOT NULL);
CREATE VIEW dc_augmentation_coverage AS
    SELECT count(*) AS dc_locations,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM augmentation a WHERE a.location_id=d.location_id)) AS augmented_any_scope,
           count(*) FILTER (WHERE EXISTS (SELECT 1 FROM augmentation a WHERE a.location_id=d.location_id AND a.scope='site')) AS augmented_site_scope
    FROM dc_locations d;
-- Every reported power observation remains linked to its original source row.
-- These are charger-record ratings, not a sum or a station-wide maximum.
CREATE VIEW location_power_observations AS
    SELECT c.location_id,c.record_id,c.source_row,c.charger_type,c.power_min_kw,
           c.power_max_kw,c.power_kind,c.power_raw,s.source_file,s.url AS source_url,
           s.retrieved_at_utc AS source_captured_at
    FROM charger_record c JOIN source_snapshot s
      ON s.source_file='data/raw/ev_20251216.csv'
    WHERE c.power_min_kw IS NOT NULL OR c.power_max_kw IS NOT NULL;
