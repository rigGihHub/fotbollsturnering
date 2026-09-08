from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')
VERSION = Path('VERSION.txt').read_text(encoding='utf-8').strip()


def test_v524_version():
    assert VERSION == '2026.09.07-525-OPTIONAL-REFEREE-SETUP'


def test_primary_flow_snapshot_contains_pitches_before_it_is_read():
    start = APP.index('f"_cupnavi_admin_cache_flow_primary_{int(tid)}"')
    end = APP.index('_flow_total = int(_flow_counts["matches_n"] or 0)', start)
    block = APP[start:end]
    assert 'AS pitches_n' in block
    assert '(tid,tid,tid,tid,tid,tid,tid)' in block


def test_beginner_routing_can_still_route_missing_pitch_to_setup():
    assert 'elif int(_flow_counts["pitches_n"] or 0) == 0:' in APP
    assert '_recommended_page, _recommended_label = "Adminöversikt", "Lägg till planer och tider"' in APP
