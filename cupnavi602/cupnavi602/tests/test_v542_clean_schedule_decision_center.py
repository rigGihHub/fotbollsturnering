from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / 'cupnavi_core' / 'schedule_workspace_view.py').read_text()
VERSION = (ROOT / 'VERSION.txt').read_text().strip()


def test_version_and_clean_status_hierarchy():
    assert VERSION == '2026.09.08-542-CLEAN-SCHEDULE-DECISION-CENTER'
    assert 'st.markdown("### Val som måste göras")' in VIEW
    assert '_status_cols[2].metric("Blockerande fel", len(schedule_errors))' in VIEW
    assert '_status_cols[3].metric("Varningar", len(schedule_warnings))' in VIEW
    assert 'Förkontroll ·' not in VIEW


def test_blocking_errors_are_visible_individually():
    assert 'st.markdown(f"### ⛔ Blockerande schemafel ({len(schedule_errors)})")' in VIEW
    assert 'for idx, issue in enumerate(schedule_errors, 1):' in VIEW
    assert 'st.error(f"{idx}. {issue}")' in VIEW


def test_regeneration_choice_is_next_to_primary_action():
    assert 'st.markdown("### Nästa steg")' in VIEW
    assert 'Ja, CupNavi får ersätta befintliga ospelade schematider' in VIEW
    assert '_schedule_action_disabled = not _confirm_regenerate' in VIEW
    assert 'Inget ändras innan du trycker på knappen.' in VIEW
