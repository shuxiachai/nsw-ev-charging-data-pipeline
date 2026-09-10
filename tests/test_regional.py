from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
import xml.etree.ElementTree as ET

import duckdb
import geopandas as gpd
import pandas as pd
import pytest
from shapely import from_wkt
from shapely.geometry import MultiPolygon, Polygon, box, mapping

from ev_pipeline.acquire import ROOT
from ev_pipeline.clean import FIELDS, identifier, text
from ev_pipeline.regional import (
    AUDIT_COLUMNS, EVIDENCE_COLUMNS, SOURCE_CSV, acquire_regional,
    database_regional_reviews_valid, flag_reviewed_geographic_conflicts, regional_reviews,
)


def rebind(root, config, filename):
    """Approve changed synthetic fixture bytes; never alter a production review."""
    path = root / filename
    source = next(item for item in config["sources"] if item["file"] == filename)
    source.update({"sha256": sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    path.with_name(path.name + ".meta.json").write_text(json.dumps({key: source[key]
        for key in ["url", "sha256", "bytes", "retrieved_at_utc"]}), encoding="utf-8")


@pytest.fixture
def regional_fixture(tmp_path):
    values = dict(zip(FIELDS, ["", "", "81 Hickory St, Testville NSW 2453, Australia", "NRMA", "4", "DC",
                              "75 kW", "-32", "147", "Example Council", "2829", "TfNSW Regional"]))
    record_id = identifier("r_", {key: text(value) for key, value in values.items()})
    expected_location = {"location_id": "location_one", "address": values["Station_address"], "operator_name": "NRMA",
                         "latitude": -32.0, "longitude": 147.0, "postcode": "2829", "address_postcode": "2453",
                         "address_conflict": True, "original_latitude": -32.0, "original_longitude": 147.0,
                         "original_postcode": "2829", "original_address_conflict": True, "sa4_code": "105"}
    locality = box(151, -31, 151.02, -30.98)
    source_names = [SOURCE_CSV, "data/raw/localities.geojson", "data/raw/layer.json", "data/raw/abs.geojson",
                    "data/raw/nrma.html", "data/raw/map.kml", "data/raw/venue.html"]
    urls = ["https://source.example/chargers.csv", "https://spatial.example/localities", "https://spatial.example/layer",
            "https://abs.example/boundaries", "https://nrma.example/network",
            "https://www.google.com/maps/d/kml?mid=reviewed-map", "https://council.example/venue"]
    roles = ["source_record", "locality_boundary", "layer_definition", "statistical_boundary", "operator_publication",
             "operator_locality", "venue_address"]
    sources = [{"file": filename, "url": url, "sha256": "", "bytes": 1,
                "retrieved_at_utc": "2026-09-09T00:00:00+00:00"} for filename, url in zip(source_names, urls)]
    for filename in source_names:
        (tmp_path / filename).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([values], columns=FIELDS).to_csv(tmp_path / SOURCE_CSV, index=False)
    (tmp_path / source_names[1]).write_text(json.dumps({"type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:7844"}},
        "features": [{"type": "Feature", "properties": {"suburbname": "TESTVILLE", "OBJECTID": 7, "postcode": 2453},
                      "geometry": mapping(locality)}]}), encoding="utf-8")
    (tmp_path / source_names[2]).write_text(json.dumps({"name": "Suburb", "id": 2, "geometryType": "esriGeometryPolygon",
        "extent": {"spatialReference": {"wkid": 7844}}}), encoding="utf-8")
    abs_regions = gpd.GeoDataFrame({"SA4_CODE26": ["104", "105"], "SA4_NAME26": ["Target", "Original"], "STE_CODE26": ["1", "1"]},
                                   geometry=[box(150, -32, 152, -30), box(146, -33, 148, -31)], crs=7844)
    (tmp_path / source_names[3]).write_text(abs_regions.to_json(), encoding="utf-8")
    (tmp_path / source_names[4]).write_text('<iframe src="https://www.google.com/maps/d/embed?mid=reviewed-map"></iframe>', encoding="utf-8")
    (tmp_path / source_names[5]).write_text('<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark>'
        '<name>NRMA Fast Charger Testville</name><Point><coordinates>151.01,-30.99,0</coordinates></Point>'
        '</Placemark></Document></kml>', encoding="utf-8")
    (tmp_path / source_names[6]).write_text("Synthetic first-party address/venue original", encoding="utf-8")
    config = {"schema_version": 1, "review_date": "2026-09-09", "sources": sources, "source_csv_file": SOURCE_CSV,
              "locality_source_file": source_names[1], "layer_source_file": source_names[2], "abs_source_file": source_names[3],
              "operator_page_file": source_names[4], "operator_map_file": source_names[5], "reviews": [{
                  "review_id": "RR_TEST", "record_id": record_id,
                  "expected_source": {"source_row": 2, "raw_values": values}, "expected_location": expected_location,
                  "locality_name": "TESTVILLE", "locality_object_id": 7, "locality_postcode": "2453",
                  "expected_sa4_code": "104", "operator_element_id": "NRMA Fast Charger Testville",
                  "evidence": [{"source_file": filename, "role": role, "locator": "Synthetic reviewed locator"}
                               for filename, role in zip(source_names, roles)], "reason": "Regional evidence only; retain point conflict.",
              }]}
    for filename in source_names:
        rebind(tmp_path, config, filename)
    records = pd.DataFrame([{"record_id": record_id, "location_id": "location_one", "source_row": 2,
                             "raw_json": json.dumps(values)}])
    locations = pd.DataFrame([expected_location])
    regions = abs_regions.rename(columns={"SA4_CODE26": "sa4_code", "SA4_NAME26": "sa4_name"}).to_crs(4326)
    return tmp_path, config, records, locations, regions


def run(fixture):
    root, config, records, locations, regions = fixture
    return regional_reviews(records, locations, regions, root=root, config=config)


def rewrite_locality(fixture, mutate):
    root, config, *_ = fixture
    filename = config["locality_source_file"]
    data = json.loads((root / filename).read_text(encoding="utf-8"))
    mutate(data)
    (root / filename).write_text(json.dumps(data), encoding="utf-8")
    rebind(root, config, filename)


def test_regional_audit_preserves_all_input_values_and_point_uncertainty(regional_fixture):
    _, _, records, locations, regions = regional_fixture
    before = [frame.copy(deep=True) for frame in [records, locations, regions]]
    audit, evidence = run(regional_fixture)
    assert list(audit) == AUDIT_COLUMNS and list(evidence) == EVIDENCE_COLUMNS
    assert audit.iloc[0].source_point_sa4_code == "105" and audit.iloc[0].reviewed_sa4_code == "104"
    assert audit.iloc[0].coordinate_status == "unresolved" and len(evidence) == 7
    assert from_wkt(audit.iloc[0].locality_wkt).area > 0
    for actual, original in zip([records, locations, regions], before):
        pd.testing.assert_frame_equal(actual, original)


def test_empty_review_list_has_fixed_schemas(regional_fixture):
    regional_fixture[1]["reviews"] = []
    audit, evidence = run(regional_fixture)
    assert audit.empty and evidence.empty
    assert list(audit) == AUDIT_COLUMNS and list(evidence) == EVIDENCE_COLUMNS


@pytest.mark.parametrize("change", ["missing_crs", "wrong_crs", "truncated", "empty", "duplicate", "wrong_id", "wrong_postcode",
                                   "nonfinite", "self_crossing", "unclosed", "missing_geometry"])
def test_invalid_or_ambiguous_locality_is_rejected(regional_fixture, change):
    def mutate(data):
        feature = data["features"][0]
        if change == "missing_crs":
            data.pop("crs")
        elif change == "wrong_crs":
            data["crs"]["properties"]["name"] = "EPSG:4326"
        elif change == "truncated":
            data["exceededTransferLimit"] = True
        elif change == "empty":
            data["features"] = []
        elif change == "duplicate":
            data["features"].append(deepcopy(feature))
        elif change == "wrong_id":
            feature["properties"]["OBJECTID"] = 99
        elif change == "wrong_postcode":
            feature["properties"]["postcode"] = 9999
        elif change == "nonfinite":
            feature["geometry"]["coordinates"][0][0][0] = float("nan")
        elif change == "self_crossing":
            feature["geometry"]["coordinates"] = [[[151,-31],[151.02,-30.98],[151,-30.98],[151.02,-31],[151,-31]]]
        elif change == "unclosed":
            feature["geometry"]["coordinates"][0].pop()
        else:
            feature["geometry"] = None
    rewrite_locality(regional_fixture, mutate)
    with pytest.raises(ValueError, match="Regional locality"):
        run(regional_fixture)


def test_whole_multipolygon_is_checked_including_an_outlying_island(regional_fixture):
    rewrite_locality(regional_fixture, lambda data: data["features"][0].update({"geometry": mapping(
        MultiPolygon([box(151,-31,151.02,-30.98), box(147,-32,147.01,-31.99)]))}))
    with pytest.raises(ValueError, match="complete locality"):
        run(regional_fixture)


def test_operator_point_in_polygon_hole_is_not_in_the_locality(regional_fixture):
    geometry = Polygon(box(151,-31,151.02,-30.98).exterior.coords,
                       [box(151.009,-30.991,151.011,-30.989).exterior.coords])
    rewrite_locality(regional_fixture, lambda data: data["features"][0].update({"geometry": mapping(geometry)}))
    with pytest.raises(ValueError, match="outside the complete locality"):
        run(regional_fixture)


def test_other_region_touching_locality_boundary_prevents_unique_confirmation(regional_fixture):
    regions = regional_fixture[4]
    # Touching is an intersection even if one region covers the complete locality.
    regions.loc[regions.sa4_code.eq("105"), "geometry"] = box(151.02,-31,151.03,-30.98)
    with pytest.raises(ValueError, match="complete locality"):
        run(regional_fixture)


@pytest.mark.parametrize("change", ["operator_point", "placemark_name", "duplicate", "publication", "layer_crs"])
def test_operator_and_layer_semantics_are_parsed(regional_fixture, change):
    root, config, *_ = regional_fixture
    filename = config["operator_map_file"]
    if change == "publication":
        filename = config["operator_page_file"]
        (root / filename).write_text("Unrelated page without map", encoding="utf-8")
    elif change == "layer_crs":
        filename = config["layer_source_file"]
        data = json.loads((root / filename).read_text(encoding="utf-8"))
        data["extent"]["spatialReference"]["wkid"] = 4326
        (root / filename).write_text(json.dumps(data), encoding="utf-8")
    else:
        xml = ET.parse(root / filename).getroot()
        ns = {"k":"http://www.opengis.net/kml/2.2"}
        marker = xml.find(".//k:Placemark",ns)
        if change == "operator_point":
            marker.find("k:Point/k:coordinates",ns).text = "147,-32,0"
        elif change == "placemark_name":
            marker.find("k:name",ns).text = "Tesla Testville"
        else:
            xml.find("k:Document",ns).append(deepcopy(marker))
        ET.ElementTree(xml).write(root / filename,encoding="utf-8")
    rebind(root, config, filename)
    with pytest.raises(ValueError, match="Regional"):
        run(regional_fixture)


@pytest.mark.parametrize("change", ["town", "postcode", "raw_operator", "current_operator", "venue_role"])
def test_valid_geometry_cannot_authorize_wrong_source_semantics(regional_fixture, change):
    review = regional_fixture[1]["reviews"][0]
    if change == "town":
        review["locality_name"] = "ANOTHER TOWN"
    elif change == "postcode":
        review["locality_postcode"] = "9999"
    elif change == "raw_operator":
        review["expected_source"]["raw_values"]["Operator"] = "Tesla"
    elif change == "current_operator":
        review["expected_location"]["operator_name"] = "Tesla"
    else:
        review["evidence"][-1]["role"] = "unrelated_picture"
    with pytest.raises(ValueError, match="semantic guards|venue address/context"):
        run(regional_fixture)


@pytest.mark.parametrize("field,value", [("latitude",-30.0),("original_longitude",148.0),("postcode","2453"),
                                        ("address_conflict",False),("sa4_code","104")])
def test_current_and_original_location_values_cannot_change(regional_fixture, field, value):
    regional_fixture[3].loc[0,field] = value
    with pytest.raises(ValueError, match="location guard"):
        run(regional_fixture)


@pytest.mark.parametrize("change", ["source_row", "raw_json", "missing_record", "duplicate_record", "wrong_membership"])
def test_source_record_identity_and_membership_are_guarded(regional_fixture, change):
    root, config, records, locations, regions = regional_fixture
    if change == "source_row":
        records.loc[0,"source_row"] = 99
    elif change == "raw_json":
        raw = json.loads(records.loc[0,"raw_json"])
        raw["Number_of_plugs"] = "999"
        records.loc[0,"raw_json"] = json.dumps(raw)
    elif change == "missing_record":
        records = records.iloc[:0]
    elif change == "duplicate_record":
        records = pd.concat([records,records],ignore_index=True)
    else:
        records.loc[0,"location_id"] = "another_location"
    with pytest.raises(ValueError, match="Regional"):
        regional_reviews(records,locations,regions,root=root,config=config)


@pytest.mark.parametrize("change", ["missing_original", "missing_manifest", "changed_bytes", "capture_time"])
def test_review_pins_cannot_be_refreshed_silently(regional_fixture, change):
    root, config, *_ = regional_fixture
    filename = config["reviews"][0]["evidence"][-1]["source_file"]
    path = root / filename
    meta = path.with_name(path.name + ".meta.json")
    if change == "missing_original":
        path.unlink()
    elif change == "missing_manifest":
        meta.unlink()
    elif change == "changed_bytes":
        expected = deepcopy(config["sources"])
        path.write_text("Replaced claim",encoding="utf-8")
        rebind(root,config,filename)
        config["sources"] = expected
    else:
        data = json.loads(meta.read_text(encoding="utf-8"))
        data["retrieved_at_utc"] = "2026-09-10T00:00:00+00:00"
        meta.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises((ValueError,FileNotFoundError), match="Regional"):
        run(regional_fixture)


def test_regional_acquisition_passes_every_fixed_hash(regional_fixture,monkeypatch):
    root,config,*_ = regional_fixture
    calls=[]
    def fetch(url,path,offline,expected_sha256):
        calls.append((url,path,offline,expected_sha256))
    monkeypatch.setattr("ev_pipeline.regional.fetch",fetch)
    acquire_regional(True,root=root,config=config)
    assert len(calls)==len(config["sources"])
    assert all(call[2] and len(call[3])==64 for call in calls)


@pytest.fixture
def evie_regional_fixture(regional_fixture):
    root,config,records,locations,_=regional_fixture
    review=config['reviews'][0]
    values=review['expected_source']['raw_values']
    values['Operator']='Evie'
    record_id=identifier('r_', {key:text(value) for key,value in values.items()})
    review['record_id']=record_id
    review['expected_location']['operator_name']='Evie'
    records.loc[0,'record_id']=record_id
    records.loc[0,'raw_json']=json.dumps(values)
    locations.loc[0,'operator_name']='Evie'
    pd.DataFrame([values],columns=FIELDS).to_csv(root/SOURCE_CSV,index=False)
    rebind(root,config,SOURCE_CSV)
    files={
        'operator_page_file':('data/raw/evie.html','https://evie.com.au/find-a-charger/'),
        'operator_script_file':('data/raw/evie.js','https://evie.com.au/locator.js'),
        'operator_source_file':('data/raw/evie.json','https://evie.com.au/wp-admin/admin-ajax.php?action=store_search&lat=-30.99&lng=151.01'),
    }
    site={'id':'fixture-evie-7','store':'Testville Centre','address':'81 Hickory Street','city':'Testville',
          'state':'NSW','zip':'2453','country':'AUS','lat':'-30.99','lng':'151.01'}
    content={
        'operator_page_file':'<script>var wpslSettings = {"ajaxurl":"https://evie.com.au/wp-admin/admin-ajax.php"};</script>'
                             '<script src="https://evie.com.au/locator.js"></script>',
        'operator_script_file':'var query={action:"store_search"}; jQuery.get(wpslSettings.ajaxurl, query, receive);',
        'operator_source_file':json.dumps([site]),
    }
    review['operator_kind']='evie_public_map'
    review['operator_element_id']=site['id']
    review['operator_expected_values']=site
    review['evidence']=[item for item in review['evidence'] if item['source_file'] not in
                        {config['operator_page_file'],config['operator_map_file']}]
    for key,(filename,url) in files.items():
        review[key]=filename
        config['sources'].append({'file':filename,'url':url,'sha256':'','bytes':1,
                                  'retrieved_at_utc':'2026-09-09T00:00:00+00:00'})
        (root/filename).write_text(content[key],encoding='utf-8')
        rebind(root,config,filename)
        review['evidence'].append({'source_file':filename,'role':key,'locator':'Complete synthetic public original'})
    return regional_fixture


def test_evie_uses_its_own_published_site_without_replacing_source_points(evie_regional_fixture):
    _,config,records,locations,_=evie_regional_fixture
    before_records,before_locations=records.copy(deep=True),locations.copy(deep=True)
    audit,evidence=run(evie_regional_fixture)
    assert audit.iloc[0].operator_source_file=='data/raw/evie.json'
    assert audit.iloc[0].operator_element_id=='fixture-evie-7'
    assert audit.iloc[0].coordinate_status=='unresolved'
    assert audit.iloc[0].source_point_sa4_code=='105' and audit.iloc[0].reviewed_sa4_code=='104'
    assert config['operator_map_file'] not in set(evidence.source_file)
    pd.testing.assert_frame_equal(records,before_records)
    pd.testing.assert_frame_equal(locations,before_locations)


@pytest.mark.parametrize('change',['missing','duplicate','id','store','address','city','zip','lat','lng'])
def test_evie_full_selected_identity_cannot_be_changed_by_repinning_response(evie_regional_fixture,change):
    root,config,*_=evie_regional_fixture
    filename=config['reviews'][0]['operator_source_file']
    values=json.loads((root/filename).read_text())
    if change=='missing':values=[]
    elif change=='duplicate':values.append(deepcopy(values[0]))
    else:values[0][change]='unreviewed value'
    (root/filename).write_text(json.dumps(values),encoding='utf-8')
    rebind(root,config,filename)
    with pytest.raises(ValueError,match='Regional Evie'):
        run(evie_regional_fixture)


@pytest.mark.parametrize('change',['unlinked_script','other_endpoint','other_host','other_action','post_only'])
def test_evie_publication_chain_is_checked_beyond_hashes(evie_regional_fixture,change):
    root,config,*_=evie_regional_fixture
    review=config['reviews'][0]
    filename=review['operator_page_file']
    body=(root/filename).read_text()
    if change=='unlinked_script':body=body.replace('https://evie.com.au/locator.js','https://evie.com.au/unrelated.js')
    elif change=='other_endpoint':body=body.replace('/wp-admin/admin-ajax.php','/unrelated.php')
    elif change=='post_only':
        filename=review['operator_script_file']
        body=(root/filename).read_text().replace('jQuery.get','jQuery.post')
    else:
        filename=review['operator_source_file']
        source=next(item for item in config['sources'] if item['file']==filename)
        source['url']=source['url'].replace('evie.com.au','other.example') if change=='other_host' else source['url'].replace('store_search','unrelated_action')
        body=(root/filename).read_text()
    (root/filename).write_text(body,encoding='utf-8')
    rebind(root,config,filename)
    with pytest.raises(ValueError,match='Regional Evie'):
        run(evie_regional_fixture)


def test_evie_wrong_street_does_not_gain_support_from_an_otherwise_matching_town(evie_regional_fixture):
    root,config,*_=evie_regional_fixture
    review=config['reviews'][0]
    review['operator_expected_values']['address']='99 Different Road'
    filename=review['operator_source_file']
    (root/filename).write_text(json.dumps([review['operator_expected_values']]),encoding='utf-8')
    rebind(root,config,filename)
    with pytest.raises(ValueError,match='address/locality semantic guards'):
        run(evie_regional_fixture)


def test_evie_cannot_skip_whole_polygon_operator_point_containment(evie_regional_fixture):
    rewrite_locality(evie_regional_fixture,lambda data:data['features'][0].update({'geometry':mapping(
        Polygon(box(151,-31,151.02,-30.98).exterior.coords,[box(151.009,-30.991,151.011,-30.989).exterior.coords]))}))
    with pytest.raises(ValueError,match='outside the complete locality'):
        run(evie_regional_fixture)


def test_per_review_locality_original_is_used_without_replacing_the_old_snapshot(regional_fixture):
    root,config,*_=regional_fixture
    original_path=root/config['locality_source_file']
    original_bytes=original_path.read_bytes()
    alternate='data/raw/additional_locality.geojson'
    (root/alternate).write_bytes(original_bytes)
    config['sources'].append({'file':alternate,'url':'https://spatial.example/additional','sha256':'','bytes':1,
                              'retrieved_at_utc':'2026-09-09T00:00:00+00:00'})
    rebind(root,config,alternate)
    review=config['reviews'][0]
    review['locality_source_file']=alternate
    for item in review['evidence']:
        if item['role']=='locality_boundary':item['source_file']=alternate
    audit,_=run(regional_fixture)
    assert audit.iloc[0].locality_source_file==alternate
    modified=json.loads((root/alternate).read_text())
    modified['features'][0]['geometry']=mapping(MultiPolygon([box(151,-31,151.02,-30.98),box(147,-32,147.01,-31.99)]))
    (root/alternate).write_text(json.dumps(modified),encoding='utf-8')
    rebind(root,config,alternate)
    with pytest.raises(ValueError,match='complete locality'):
        run(regional_fixture)
    assert original_path.read_bytes()==original_bytes


@pytest.fixture
def regional_database(regional_fixture):
    yield from _regional_database(regional_fixture)


@pytest.fixture
def evie_regional_database(evie_regional_fixture):
    yield from _regional_database(evie_regional_fixture)


def _regional_database(regional_fixture):
    root,config,records,locations,_ = regional_fixture
    audit,evidence = run(regional_fixture)
    con=duckdb.connect(":memory:",config={"extension_directory":str(ROOT/".runtime/duckdb_extensions")})
    con.execute("LOAD spatial")
    snapshots=pd.DataFrame([{**source,"byte_count":source["bytes"]} for source in config["sources"]]).rename(columns={"file":"source_file"})
    con.register("snapshots_input",snapshots)
    con.execute("CREATE TABLE source_snapshot AS SELECT source_file,url,sha256,byte_count,CAST(retrieved_at_utc AS TIMESTAMPTZ) AS retrieved_at_utc FROM snapshots_input")
    con.register("records_input",records)
    con.execute("CREATE TABLE charger_record AS SELECT * FROM records_input")
    con.register("locations_input",locations.assign(operator_id="reviewed-operator"))
    con.execute("CREATE TABLE location AS SELECT * EXCLUDE(operator_name) FROM locations_input")
    con.execute("CREATE TABLE operator AS SELECT 'reviewed-operator' AS operator_id, ? AS operator_name",[locations.iloc[0].operator_name])
    con.register("audit_input",audit)
    con.execute("CREATE TABLE reviewed_region AS SELECT * EXCLUDE(locality_wkt) REPLACE(CAST(review_date AS DATE) AS review_date),ST_GeomFromText(locality_wkt) AS locality_geometry FROM audit_input")
    con.register("evidence_input",evidence)
    con.execute("CREATE TABLE reviewed_region_evidence AS SELECT * FROM evidence_input")
    yield con,root,config
    con.close()


def test_database_validator_reconstructs_the_original_evidence(regional_database):
    con,root,config=regional_database
    assert database_regional_reviews_valid(con,root=root,config=config)


@pytest.mark.parametrize('sql',[
    "UPDATE reviewed_region SET operator_source_file='data/raw/map.kml'",
    "UPDATE reviewed_region SET operator_element_id='another-site'",
    "DELETE FROM reviewed_region_evidence WHERE source_file='data/raw/evie.json'",
    "UPDATE operator SET operator_name='NRMA'",
])
def test_evie_database_reconstruction_checks_real_operator_evidence_and_ledger(evie_regional_database,sql):
    con,root,config=evie_regional_database
    assert database_regional_reviews_valid(con,root=root,config=config)
    con.execute(sql)
    assert not database_regional_reviews_valid(con,root=root,config=config)


@pytest.mark.parametrize("sql", [
    "DELETE FROM reviewed_region",
    "UPDATE reviewed_region SET reviewed_sa4_code='105'",
    "UPDATE reviewed_region SET coordinate_status='resolved'",
    "UPDATE reviewed_region SET reason='Different evidence claim'",
    "UPDATE reviewed_region SET locality_geometry=ST_Buffer(ST_Centroid(locality_geometry),0.001)",
    "DELETE FROM reviewed_region_evidence WHERE role='venue_address'",
    "UPDATE reviewed_region_evidence SET locator='Unreviewed page' WHERE role='venue_address'",
    "UPDATE source_snapshot SET retrieved_at_utc=TIMESTAMPTZ '2026-09-10T00:00:00+00:00'",
    "UPDATE source_snapshot SET byte_count=byte_count+1",
    "UPDATE location SET latitude=-30",
    "UPDATE charger_record SET source_row=99",
])
def test_database_tampering_cannot_validate_its_own_ledger(regional_database,sql):
    con,root,config=regional_database
    con.execute(sql)
    assert not database_regional_reviews_valid(con,root=root,config=config)


def test_actual_eight_regional_reviews_preserve_points_and_detect_new_italy():
    from ev_pipeline.clean import load_clean,spatial_assign
    from ev_pipeline.identity import apply_reviewed_identities
    from ev_pipeline.resolve import resolve_conflicts
    from ev_pipeline.reviewed import apply_reviewed_resolutions
    _,records,issues,_=load_clean()
    records,_=apply_reviewed_identities(records,issues)
    records,_=resolve_conflicts(records,issues)
    records,_=apply_reviewed_resolutions(records,issues)
    locations,regions=spatial_assign(records,issues)
    original_record = records.loc[records.source_row.eq(1711)].iloc[0].copy()
    records,locations=flag_reviewed_geographic_conflicts(records,locations,issues)
    before_records,before_locations=records.copy(deep=True),locations.copy(deep=True)
    audit,evidence=regional_reviews(records,locations,regions)
    assert audit.set_index("source_row").reviewed_sa4_code.to_dict()=={181:"101",380:"105",395:"110",730:"104",823:"110",650:"105",820:"123",1711:"112"}
    assert len(audit)==8 and len(evidence)==66 and audit.coordinate_status.eq("unresolved").all()
    assert locations.address_conflict.sum()==8
    new_italy = records.loc[records.source_row.eq(1711)].iloc[0]
    assert new_italy.address_conflict and not new_italy.original_address_conflict
    assert new_italy.postcode == new_italy.address_postcode == "2472"
    for field in original_record.index.difference(["address_conflict"]):
        assert pd.isna(new_italy[field]) and pd.isna(original_record[field]) or new_italy[field] == original_record[field]
    assert len(records)==1958 and len(locations)==1936
    assert records.loc[records.charger_type.eq("DC"),"location_id"].nunique()==426
    new_issues=[issue for issue in issues if issue['code']=='source_point_outside_reviewed_locality']
    assert len(new_issues)==1 and new_issues[0]['source_row']==1711
    pd.testing.assert_frame_equal(records,before_records)
    pd.testing.assert_frame_equal(locations,before_locations)


@pytest.fixture
def venue_region_fixture(regional_fixture):
    root, config, records, locations, regions = regional_fixture
    review = config["reviews"][0]
    values = review["expected_source"]["raw_values"]
    values.update(Operator="Tesla", PCODE="2453")
    record_id = identifier("r_", {key:text(value) for key,value in values.items()})
    review["record_id"] = record_id
    records.loc[0,"record_id"] = record_id
    records.loc[0,"raw_json"] = json.dumps(values)
    records["address_conflict"] = False
    records["original_address_conflict"] = False
    pd.DataFrame([values],columns=FIELDS).to_csv(root/SOURCE_CSV,index=False)
    for key,value in {"operator_name":"Tesla","postcode":"2453","original_postcode":"2453",
                      "original_address_conflict":False}.items():
        locations.loc[0,key]=value
        review["expected_location"][key]=value
    locations.loc[0,"address_conflict"] = False
    venue_file="data/raw/venue_owner.html"
    config["sources"].append(dict(file=venue_file,url="https://venue.example/",sha256="",bytes=1,
                                  retrieved_at_utc="2026-09-10T00:00:00+00:00"))
    review.update(operator_kind="venue_address_page",operator_name="Tesla",operator_source_file=venue_file,
                  operator_element_id="Testville Museum EV charging area",venue_host="venue.example",
                  council_host="council.nsw.gov.au",council_source_file="data/raw/venue.html",
                  council_record_id="DA2021/0125",council_address="81 Hickory Street, Testville",
                  venue_name="Testville Museum",venue_street_address="81 Hickory Street",
                  venue_required_text=["Tesla Supercharger station at Testville Museum","81 Hickory Street","NSW 2453"],
                  geographic_conflict=dict(minimum_distance_m=1000,maximum_distance_m=1000000))
    next(s for s in config["sources"] if s["file"]=="data/raw/venue.html")["url"]="https://council.nsw.gov.au/decisions"
    (root/venue_file).write_text("<p>Tesla Supercharger station at Testville Museum</p><p>81 Hickory Street NSW 2453</p>",encoding="utf-8")
    (root/"data/raw/venue.html").write_text("<table><tr><td>DA2021/0125</td><td>Testville Museum</td>"
                                         "<td>81 Hickory Street, Testville</td></tr></table>",encoding="utf-8")
    review["evidence"].append(dict(source_file=venue_file,role="venue_charging_statement",locator="Visible venue statement"))
    for filename in [SOURCE_CSV,venue_file,"data/raw/venue.html"]:
        rebind(root,config,filename)
    return root,config,records,locations,regions


def test_equal_postcodes_do_not_hide_evidence_bound_geographic_conflict(venue_region_fixture):
    root,config,records,locations,regions=venue_region_fixture
    original_records,original_locations=records.copy(deep=True),locations.copy(deep=True)
    issues=[]
    updated_records,updated_locations=flag_reviewed_geographic_conflicts(records,locations,issues,root=root,config=config)
    assert updated_locations.iloc[0].address_conflict and not updated_locations.iloc[0].original_address_conflict
    assert updated_records.iloc[0].address_conflict and len(issues)==1
    assert updated_locations.iloc[0].postcode==updated_locations.iloc[0].address_postcode
    pd.testing.assert_frame_equal(updated_records.drop(columns="address_conflict"),records.drop(columns="address_conflict"))
    pd.testing.assert_frame_equal(updated_locations.drop(columns="address_conflict"),locations.drop(columns="address_conflict"))
    pd.testing.assert_frame_equal(records,original_records)
    pd.testing.assert_frame_equal(locations,original_locations)
    audit,_=regional_reviews(updated_records,updated_locations,regions,root=root,config=config)
    assert audit.iloc[0].reviewed_sa4_code=="104" and audit.iloc[0].coordinate_status=="unresolved"


@pytest.mark.parametrize("change",["missing_operator","script_only","different_street","wrong_venue","duplicate_council_row",
                                  "wrong_publisher","too_near_for_guard","nonfinite_distance","changed_raw_record","changed_original_point"])
def test_geographic_review_rejects_incomplete_or_inconsistent_evidence(venue_region_fixture,change):
    root,config,records,locations,_=venue_region_fixture
    review=config["reviews"][0]
    filename=None
    if change in {"missing_operator","script_only"}:
        filename=review["operator_source_file"]
        content=(root/filename).read_text(encoding="utf-8")
        content=content.replace("Tesla Supercharger station at Testville Museum", "Unrelated station") if change=="missing_operator" else "<script>"+content+"</script>"
        (root/filename).write_text(content,encoding="utf-8")
    elif change in {"different_street","wrong_venue","duplicate_council_row"}:
        filename=review["council_source_file"]
        content=(root/filename).read_text(encoding="utf-8")
        if change=="different_street":content=content.replace("81 Hickory","99 Elsewhere")
        elif change=="wrong_venue":content=content.replace("Testville Museum","Another Museum")
        else:content+=content
        (root/filename).write_text(content,encoding="utf-8")
    elif change=="wrong_publisher":
        review["council_host"]="council.example"
    elif change=="too_near_for_guard":
        review["geographic_conflict"]={"minimum_distance_m":1000000,"maximum_distance_m":2000000}
    elif change=="nonfinite_distance":
        review["geographic_conflict"]["minimum_distance_m"]=float("nan")
    elif change=="changed_raw_record":
        records.loc[0,"raw_json"]="{}"
    else:
        locations.loc[0,"original_longitude"]=148
    if filename:rebind(root,config,filename)
    before_records,before_locations=records.copy(deep=True),locations.copy(deep=True)
    issues=[]
    with pytest.raises(ValueError,match="Regional"):
        flag_reviewed_geographic_conflicts(records,locations,issues,root=root,config=config)
    assert issues==[]
    pd.testing.assert_frame_equal(records,before_records)
    pd.testing.assert_frame_equal(locations,before_locations)


@pytest.fixture
def venue_regional_database(venue_region_fixture):
    root,config,records,locations,regions=venue_region_fixture
    issues=[]
    records,locations=flag_reviewed_geographic_conflicts(records,locations,issues,root=root,config=config)
    for con,root,config in _regional_database((root,config,records,locations,regions)):
        con.register("quality_input",pd.DataFrame(issues))
        con.execute("CREATE TABLE quality_issue AS SELECT * FROM quality_input")
        yield con,root,config


@pytest.mark.parametrize("sql",[
    "DELETE FROM quality_issue",
    "UPDATE quality_issue SET detail='Unreviewed statement'",
    "UPDATE location SET address_conflict=False",
    "UPDATE location SET original_address_conflict=True",
    "UPDATE reviewed_region SET reviewed_sa4_code='105'",
    "DELETE FROM reviewed_region_evidence WHERE role='venue_charging_statement'",
])
def test_geographic_conflict_cannot_be_hidden_by_deleting_its_flag_or_audit(venue_regional_database,sql):
    con,root,config=venue_regional_database
    assert database_regional_reviews_valid(con,root=root,config=config)
    con.execute(sql)
    assert not database_regional_reviews_valid(con,root=root,config=config)
