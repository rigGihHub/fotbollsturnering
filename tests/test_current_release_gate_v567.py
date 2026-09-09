from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / 'cupnavi_core' / 'schedule_workspace_view.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_v567_version():
    assert VERSION == '2026.09.08-567-SCHEDULE-CHOICE-NOVICE-UX'


def test_schema_starts_with_explicit_user_intent():
    assert 'Vad vill du göra med schemat?' in VIEW
    assert 'CupNavi skapar schemat åt mig' in VIEW
    assert 'Jag har redan ett schema' in VIEW


def test_existing_schedule_defaults_to_safe_non_destructive_path():
    block = VIEW.split('if scheduled_total > 0:', 1)[1]
    assert '"Behåll och granska befintligt schema"' in block
    assert '"Ändra enstaka matcher"' in block
    assert '"Bygg om återstående schema"' in block
    assert '_current_intent = _intent_options[0]' in VIEW


def test_regeneration_requires_explicit_path_and_confirmation():
    assert '_schedule_intent == "Bygg om återstående schema"' in VIEW
    assert 'Ja, CupNavi får ersätta befintliga ospelade schematider' in VIEW
    assert 'Spelade matcher och resultat är alltid skyddade.' in VIEW


def test_import_and_manual_editor_are_progressively_disclosed():
    assert 'scheduled_total == 0 and _schedule_intent == "Jag har redan ett schema"' in VIEW
    assert 'scheduled_total > 0 and _schedule_intent == "Ändra enstaka matcher"' in VIEW
    assert 'st.session_state[_schedule_intent_key] = "Ändra enstaka matcher"' in VIEW


def test_schema_back_navigation_uses_real_pitches_page():
    marker = 'v514_schedule_back_to_pitches_'
    block = VIEW.split(marker, 1)[1].split(')', 3)[0]
    assert 'Planer & tider' in block
