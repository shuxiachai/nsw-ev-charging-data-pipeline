"""Report enrichment composition against every retained, distinct DC location."""


def attribute_coverage(con):
    """Attribute rows overlap; source observations are not covered locations."""
    return con.execute("""
        WITH dc AS (SELECT DISTINCT location_id FROM charger_record WHERE charger_type='DC')
        SELECT a.scope, a.attribute, count(DISTINCT a.location_id) AS covered_dc_locations,
               count(*) AS source_observations,
               count(DISTINCT a.location_id)::DOUBLE / nullif((SELECT count(*) FROM dc),0) AS fraction_all_dc
        FROM augmentation a JOIN dc USING(location_id)
        GROUP BY a.scope,a.attribute ORDER BY a.scope,a.attribute
    """).df()


def augmentation_composition(con):
    """Mutually exclusive groups; station codes remain valid site attributes."""
    return con.execute("""
        WITH dc AS (SELECT DISTINCT location_id FROM charger_record WHERE charger_type='DC'),
        classified AS (
            SELECT location_id, CASE
                WHEN EXISTS (SELECT 1 FROM augmentation a WHERE a.location_id=dc.location_id
                             AND a.scope='site' AND a.attribute<>'operator_station_code')
                    THEN 'non_identifier_site_attribute'
                WHEN EXISTS (SELECT 1 FROM augmentation a WHERE a.location_id=dc.location_id
                             AND a.scope='site') THEN 'station_code_only'
                ELSE 'no_site_augmentation' END AS category FROM dc
        ), categories(category) AS (VALUES ('non_identifier_site_attribute'),('station_code_only'),('no_site_augmentation'))
        SELECT categories.category, count(classified.location_id) AS dc_locations,
               count(classified.location_id)::DOUBLE / nullif((SELECT count(*) FROM dc),0) AS fraction_all_dc
        FROM categories LEFT JOIN classified USING(category)
        GROUP BY categories.category ORDER BY categories.category
    """).df()
