"""Only independently identified station-page connector observations enrich a site."""
from copy import deepcopy
from hashlib import sha256
import json

import pandas as pd
import pytest

from ev_pipeline import ampol
from tests.test_matching import frames


URL = 'https://locations.ampol.com.au/en/ampol-foodary-test'


def current_location():
    return dict(externalId='12345', guid='12345678-1234-1234-1234-123456789abc', slug='ampol-foodary-test',
        name='Ampol Foodary Test', status='OPEN', address=dict(street='1 Test Street', number=None,
        fullAddress='1 Test Street,2000,Sydney,Au', locality='Sydney', zipCode='2000', country='Au',
        latitude=-33.86001, longitude=151.20001), services={'EVCharging': [
            dict(externalId='ChargingBay01', contentFacet=dict(title='Charging Bay 01', longContent='CHAdeMO (125kW)')),
            dict(externalId='ChargingBay02', contentFacet=dict(title='Charging Bay 02', longContent='CCS 2 (150kW)')),
            dict(externalId='EVChargingAmpCharge', contentFacet=dict(title='EV Charging (AmpCharge)',
                longContent='EV Charging (AmpCharge) is available at this location'))]})


def page(location):
    return '<script>window.view = {currentLocation: ' + json.dumps(location) + '};</script>'


def parse(location):
    return ampol.parse_page(page(location), source_file='data/raw/ampol/test.html', source_url=URL)


def fixture_source(tmp_path, location=None):
    value = current_location() if location is None else location
    path = tmp_path / 'data/raw/ampol/test.html'
    path.parent.mkdir(parents=True, exist_ok=True)
    body = page(value).encode()
    path.write_bytes(body)
    source = dict(file='data/raw/ampol/test.html', url=URL, bytes=len(body), sha256=sha256(body).hexdigest(),
                  retrieved_at_utc='2026-09-10T02:00:00+00:00')
    metadata = dict(source, method='GET', final_url=URL, status_code=200)
    path.with_name(path.name+'.meta.json').write_text(json.dumps(metadata))
    return dict(schema_version=1, sources=[source]), path


def test_extracts_only_station_ev_service_and_preserves_original_labels():
    source = current_location()
    original = deepcopy(source)
    parsed = parse(source)
    assert parsed['ampol_id'] == '12345' and parsed['has_dc'] is True
    assert parsed['dc_connector_types'] == 'CCS (Type 2); CHAdeMO'
    assert json.loads(parsed['ev_charging_json']) == source['services']['EVCharging']
    assert parsed['address_raw'] == source['address']['fullAddress']
    assert not {'device_count','number_of_plugs','live_status','power_kw'} & set(parsed)
    assert source == original


@pytest.mark.parametrize('which', ['missing_ev', 'generic_ampcharge_only', 'other_network', 'unknown_description'])
def test_no_global_connector_defaults_or_status_fallback(which):
    location = current_location()
    if which == 'missing_ev':
        location['services'] = {'FuelProducts': location['services']['EVCharging']}
    elif which == 'generic_ampcharge_only':
        location['services']['EVCharging'] = location['services']['EVCharging'][-1:]
    elif which == 'other_network':
        location['services']['EVCharging'] = location['services']['EVCharging'][:-1]
    else:
        for item in location['services']['EVCharging'][:-1]:
            item['contentFacet']['longContent'] = 'Fast EV Charging'
    assert parse(location)['has_dc'] is False


def test_single_ccs1_description_is_not_automatically_changed_to_ccs2():
    location = current_location()
    location['services']['EVCharging'] = [location['services']['EVCharging'][-1],
        dict(externalId='ChargingBay03', contentFacet=dict(title='Charging Bay 03', longContent='CCS1 (50 kW)'))]
    parsed = parse(location)
    assert parsed['has_dc'] is True and parsed['dc_connector_types'] == 'CCS (Type 1)'


def test_reversed_numeric_street_address_is_reordered_without_losing_original():
    location = current_location()
    location['address'].update(street='Central Coast Hwy, 69-71', fullAddress='Central Coast Hwy, 69-71,2250,Gosford West,Au')
    parsed = parse(location)
    assert parsed['address'].startswith('69-71 Central Coast Hwy,')
    assert parsed['address_raw'].startswith('Central Coast Hwy, 69-71,')


@pytest.mark.parametrize('number,street', [('481','487 Princes Hwy'), ('70','Central Coast Hwy, 69-71')])
def test_inconsistent_address_components_require_review(number, street):
    location = current_location()
    location['address'].update(number=number, street=street)
    with pytest.raises(ValueError, match='Ampol street'):
        parse(location)


@pytest.mark.parametrize('field,value', [('latitude',True), ('latitude',float('nan')), ('longitude',float('inf')),
                                       ('latitude',-91), ('country','NZ'), ('zipCode',''), ('fullAddress',None)])
def test_missing_or_invalid_station_geography_fails(field, value):
    location = current_location()
    location['address'][field] = value
    with pytest.raises(ValueError):
        parse(location)


def test_page_identity_and_multiple_location_objects_cannot_be_ignored():
    location = current_location()
    with pytest.raises(ValueError, match='exactly one'):
        ampol.parse_page(page(location)+page(location), source_file='fixture', source_url=URL)
    with pytest.raises(ValueError, match='slug disagree'):
        ampol.parse_page(page(location), source_file='fixture', source_url=URL+'-other')
    location['externalId'] = 12345
    with pytest.raises(ValueError, match='numeric string'):
        parse(location)


@pytest.mark.parametrize('field,value', [('sha256','0'*64), ('bytes',1), ('url','https://example.com/station'),
                                       ('method','POST'), ('final_url',URL+'-other'), ('status_code',403),
                                       ('retrieved_at_utc','2026-09-10T03:00:00+00:00')])
def test_manifest_changes_cannot_produce_valid_station_observations(tmp_path, field, value):
    config, path = fixture_source(tmp_path)
    meta = path.with_name(path.name+'.meta.json')
    content = json.loads(meta.read_text())
    content[field] = value
    meta.write_text(json.dumps(content))
    with pytest.raises(ValueError, match='provenance changed'):
        ampol.load_ampol_sites(root=tmp_path, config=config)


def test_changed_body_and_missing_timezone_are_rejected(tmp_path):
    config, path = fixture_source(tmp_path)
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError, match='provenance changed'):
        ampol.load_ampol_sites(root=tmp_path, config=config)
    config, path = fixture_source(tmp_path)
    config['sources'][0]['retrieved_at_utc'] = '2026-09-10T02:00:00'
    meta = path.with_name(path.name+'.meta.json')
    content = json.loads(meta.read_text()); content['retrieved_at_utc'] = config['sources'][0]['retrieved_at_utc']
    meta.write_text(json.dumps(content))
    with pytest.raises(ValueError, match='timezone'):
        ampol.load_ampol_sites(root=tmp_path, config=config)


def test_matching_retains_original_thresholds_conflicts_and_site_source(tmp_path):
    config, _ = fixture_source(tmp_path)
    locations, records, _ = frames()
    locations.loc[0,'operator_name'] = 'Ampol AmpCharge'
    sites, matches, audit, attributes = ampol.ampol_augment(locations, records, root=tmp_path, config=config)
    assert len(matches) == len(attributes) == 1
    assert matches.iloc[0].ampol_id == '12345'
    attr = attributes.iloc[0]
    assert attr.value == 'CCS (Type 2); CHAdeMO' and attr.scope == 'site'
    assert attr.source_file == 'data/raw/ampol/test.html' and attr.method == ampol.METHOD
    assert attr[['ocm_id','osm_id','jolt_id','ocm_operator_id']].isna().all()
    locations.loc[0,'address'] = '10 Test Street, Sydney, 2000'
    _, matches, audit, attributes = ampol.ampol_augment(locations, records, root=tmp_path, config=config)
    assert matches.empty and attributes.empty
    assert audit.iloc[0].extended_address_conflict == 'house_number_conflict'


def test_external_site_reuse_is_not_resolved_by_choosing_one_source_row(tmp_path):
    config, _ = fixture_source(tmp_path)
    locations, records, _ = frames()
    locations.loc[0,'operator_name'] = 'Ampol AmpCharge'
    second = locations.copy(); second.loc[0,'location_id'] = 'l2'
    locations = pd.concat([locations,second], ignore_index=True)
    records = pd.concat([records,pd.DataFrame([dict(location_id='l2',charger_type='DC')])], ignore_index=True)
    _, matches, audit, attributes = ampol.ampol_augment(locations, records, root=tmp_path, config=config)
    assert matches.empty and attributes.empty
    assert set(audit.decision) == {'external_poi_reused_review'}


def test_non_ev_station_keeps_schema_without_enrichment(tmp_path):
    location = current_location(); location['services'].pop('EVCharging')
    config, _ = fixture_source(tmp_path, location)
    locations, records, _ = frames(); locations.loc[0,'operator_name'] = 'Ampol AmpCharge'
    sites, matches, audit, attributes = ampol.ampol_augment(locations, records, root=tmp_path, config=config)
    assert len(sites) == 1 and not sites.iloc[0].has_dc
    assert matches.empty and audit.empty and attributes.empty
    assert list(attributes.columns) == ampol.ATTRIBUTE_COLUMNS


def test_approved_originals_include_a_non_ev_control_and_complete_connector_text():
    sites = ampol.load_ampol_sites()
    control = sites.loc[sites.ampol_id.eq('20956')].iloc[0]
    assert not control.has_dc and pd.isna(control.dc_connector_types)
    for number in ['28569','22582']:
        row = sites.loc[sites.ampol_id.eq(number)].iloc[0]
        assert row.has_dc and row.dc_connector_types == 'CCS (Type 2); CHAdeMO'
        assert {item['contentFacet']['longContent'] for item in json.loads(row.ev_charging_json)} >= {
            'CHAdeMO (125kW)', 'CCS 2 (150kW)'}


def test_acquire_restores_body_using_exact_hash_without_replacing_capture_metadata(tmp_path, monkeypatch):
    config, path = fixture_source(tmp_path)
    body = path.read_bytes(); metadata = path.with_name(path.name+'.meta.json').read_bytes()
    path.unlink()
    calls = []
    def frozen_fetch(url, destination, offline, expected_sha256):
        calls.append((url, destination, offline, expected_sha256))
        destination.write_bytes(body)
    monkeypatch.setattr(ampol, 'fetch', frozen_fetch)
    sites = ampol.acquire_ampol(root=tmp_path, config=config)
    assert len(sites) == 1 and calls == [(URL,path,False,sha256(body).hexdigest())]
    assert path.with_name(path.name+'.meta.json').read_bytes() == metadata


def test_acquire_refuses_missing_manifest_before_any_download(tmp_path, monkeypatch):
    config, path = fixture_source(tmp_path)
    path.unlink(); path.with_name(path.name+'.meta.json').unlink()
    calls = []
    monkeypatch.setattr(ampol, 'fetch', lambda *args, **kwargs: calls.append(args))
    with pytest.raises(FileNotFoundError, match='restore the supplied snapshot'):
        ampol.acquire_ampol(root=tmp_path, config=config)
    assert not calls


def test_acquire_refuses_changed_capture_metadata_before_any_download(tmp_path, monkeypatch):
    config, path = fixture_source(tmp_path)
    path.unlink(); meta = path.with_name(path.name+'.meta.json')
    value = json.loads(meta.read_text()); value['retrieved_at_utc'] = '2026-09-11T02:00:00+00:00'
    meta.write_text(json.dumps(value))
    calls = []
    monkeypatch.setattr(ampol, 'fetch', lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match='provenance changed'):
        ampol.acquire_ampol(root=tmp_path, config=config)
    assert not calls


def test_acquire_does_not_accept_a_restored_different_body(tmp_path, monkeypatch):
    config, path = fixture_source(tmp_path)
    body = path.read_bytes(); path.unlink()
    monkeypatch.setattr(ampol, 'fetch', lambda url, destination, **kwargs: destination.write_bytes(body+b' '))
    with pytest.raises(ValueError, match='provenance changed'):
        ampol.acquire_ampol(root=tmp_path, config=config)


def test_offline_acquire_neither_overwrites_cached_bytes_nor_downloads_missing_body(tmp_path):
    config, path = fixture_source(tmp_path)
    before = path.read_bytes()
    assert len(ampol.acquire_ampol(True, root=tmp_path, config=config)) == 1
    assert path.read_bytes() == before
    path.unlink()
    with pytest.raises(FileNotFoundError, match='Offline input missing'):
        ampol.acquire_ampol(True, root=tmp_path, config=config)


def test_acquire_validates_path_and_domain_before_fetch(tmp_path, monkeypatch):
    config, _ = fixture_source(tmp_path)
    config['sources'][0]['file'] = 'data/raw/ampol/../../../escape.html'
    calls = []
    monkeypatch.setattr(ampol, 'fetch', lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match='source path'):
        ampol.acquire_ampol(root=tmp_path, config=config)
    assert not calls


@pytest.mark.parametrize('full,reason,postal', [
    ('999 Test Street,2000,Sydney,Au', 'house_number_conflict', False),
    ('Test Street, 999,2000,Sydney,Au', 'house_number_conflict', False),
    ('1 Test Road,2000,Sydney,Au', 'street_type_conflict', False),
    ('1 Test Street,2001,Sydney,Au', '', True),
    ('1 Test Street, Sydney NSW 2001', '', True),
])
def test_full_ampol_address_cannot_hide_a_conflict(monkeypatch, full, reason, postal):
    locations, records, _ = frames()
    locations.loc[0, 'operator_name'] = 'Ampol AmpCharge'
    source = current_location()
    source['address']['fullAddress'] = full
    site = parse(source)
    monkeypatch.setattr(ampol, 'load_ampol_sites', lambda **kwargs: pd.DataFrame([site]))
    sites, matches, audit, attributes = ampol.ampol_augment(locations, records)
    assert matches.empty and attributes.empty
    assert audit.iloc[0].decision == 'rejected_evidence'
    assert audit.iloc[0].extended_address_conflict == reason
    assert bool(audit.iloc[0].postcode_conflict) is postal
    assert sites.iloc[0].address_raw == full


@pytest.mark.parametrize('full', [
    '1 Test Street,2000,Sydney,Au', 'Test Street, 1,2000,Sydney,Au',
    '1 Test Street, Sydney NSW 2000', '1 Test Street, Sydney, 2000, Australia',
    'Test Street,2000,Sydney,Au', 'Ampol Foodary Test',
])
def test_compatible_or_unparsed_full_address_keeps_valid_ampol_match(monkeypatch, full):
    locations, records, _ = frames()
    locations.loc[0, 'operator_name'] = 'Ampol AmpCharge'
    source = current_location()
    source['address']['fullAddress'] = full
    monkeypatch.setattr(ampol, 'load_ampol_sites', lambda **kwargs: pd.DataFrame([parse(source)]))
    _, matches, audit, attributes = ampol.ampol_augment(locations, records)
    assert len(matches) == len(attributes) == 1
    assert not audit.iloc[0].postcode_conflict


def test_four_digit_ampol_house_number_is_not_a_postcode(monkeypatch):
    locations, records, _ = frames()
    locations.loc[0, ['operator_name', 'address']] = ['Ampol AmpCharge', '1250 Test St, Sydney NSW 2000']
    source = current_location()
    source['address'].update(street='1250 Test Street', fullAddress='1250 Test Street,2000,Sydney,Au')
    monkeypatch.setattr(ampol, 'load_ampol_sites', lambda **kwargs: pd.DataFrame([parse(source)]))
    _, matches, audit, _ = ampol.ampol_augment(locations, records)
    assert len(matches) == 1 and not audit.iloc[0].postcode_conflict
