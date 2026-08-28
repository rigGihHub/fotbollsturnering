
from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_mobile_admin_columns_can_wrap():
    assert 'flex-wrap:wrap!important;' in APP
    assert 'flex:1 1 220px!important;' in APP
    assert 'flex:1 1 100%!important;' in APP

def test_mobile_flow_status_wraps_instead_of_overflowing():
    assert '.cn-flow-status{' in APP
    assert '.cn-flow-pill{' in APP
    assert 'white-space:normal!important;' in APP

def test_creation_explains_next_step_without_new_form_step():
    assert 'Efter Skapa guidar CupNavi dig genom tävlingsklasser, kapacitet och regler.' in APP

def test_team_count_is_normal_status_not_alert():
    start=APP.index('if admin_page == "Lag":')
    block=APP[start:start+12000]
    assert 'st.caption(f"{status_icon} {registered_team_count} av {max_teams}' in block

def test_schedule_primary_action_is_short_and_mobile_friendly():
    block=APP[APP.index('if admin_page == "Skapa och publicera schema":'):APP.index('if admin_page == "Matcher och resultat":')]
    assert '"Uppdatera återstående schema"' in block
    assert '"Skapa hela spelschemat"' in block
    assert '"Spelade matcher lämnas oförändrade."' in block
