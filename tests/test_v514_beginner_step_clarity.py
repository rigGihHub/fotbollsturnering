from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
FLOW=(ROOT/'cupnavi_core'/'planning_flow_nav.py').read_text(encoding='utf-8')
PUB=(ROOT/'cupnavi_core'/'admin_publication_view.py').read_text(encoding='utf-8')
VER=(ROOT/'cupnavi_core'/'version.py').read_text(encoding='utf-8')

def test_one_seven_step_flow_everywhere():
    assert 'FLOW_STEPS = ["Cupinfo", "Lag", "Grupper", "Planer & tider", "Schema", "Kontroll", "Publicera"]' in FLOW
    assert 'FLOW_STEPS = ["Grundsetup"' not in FLOW
    assert 'Steg 2 av 7 · Lag' in APP
    assert 'Steg 3 av 7 · Grupper' in APP
    assert 'Steg 5 av 7 · Schema' in APP
    assert 'Steg 6 av 7 · Kontroll' in APP

def test_sidebar_checklist_matches_journey_order():
    positions=[PUB.index(x) for x in [
        '("Cupinfo", cupinfo_ready',
        '("Lag", teams_ready',
        '("Grupper", groups_ready',
        '("Planer & tider", pitches_ready',
        '("Schema", schedule_ready',
        '("Kontroll", control_ready',
    ]]
    assert positions == sorted(positions)

def test_beginner_copy_distinguishes_required_from_optional():
    assert 'Måste vara klart före publicering' in APP
    assert 'Tröjfärger, kontaktpersoner och andra detaljer kan vänta.' in APP
    assert 'Rött måste lösas före publicering. Gult är råd' in APP

def test_publish_is_step_seven():
    assert 'Steg 7 av 7 · Publicera' in PUB

def test_version():
    assert '2026.09.07-525-OPTIONAL-REFEREE-SETUP' in VER
    assert '2026.09.07-525-OPTIONAL-REFEREE-SETUP' in APP


def test_groups_do_not_skip_pitch_step():
    assert 'Nästa steg: Planer & tider' in APP
    assert 'Fortsätt till Planer & tider →' in APP
    assert 'args=("Cupinställningar",)' in APP

def test_schedule_back_button_follows_same_journey():
    schedule=(ROOT/'cupnavi_core'/'schedule_workspace_view.py').read_text(encoding='utf-8')
    assert 'Steg 5 av 7' in schedule
    assert '← Till Planer & tider' in schedule
    assert 'Föregående steg: Planer & tider' in schedule
