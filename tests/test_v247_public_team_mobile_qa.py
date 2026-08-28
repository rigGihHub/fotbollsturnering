
from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_mobile_tabs_scroll_and_keep_touch_target():
    assert '[data-baseweb="tab-list"]{' in APP
    assert 'overflow-x:auto!important;' in APP
    assert '[data-baseweb="tab"]{' in APP
    assert 'min-height:44px!important;' in APP

def test_team_portal_first_tab_is_task_oriented():
    block=APP[APP.index("def render_team_portal"):APP.index("def ", APP.index("def render_team_portal")+10)]
    assert 'st.tabs(["Lag & matcher", "Trupp", "Matchtrupper", message_tab_label])' in block
    assert 'Checka in laget, bekräfta matchställ och se kommande matcher.' in block
    assert 'st.subheader("Lagstatus")' not in block

def test_team_portal_login_state_is_compact():
    block=APP[APP.index("def render_team_portal"):APP.index("def ", APP.index("def render_team_portal")+10)]
    assert 'top1.caption("Inloggad i lagportalen")' in block
    assert 'top1.success(f"Inloggad:' not in block

def test_normal_team_states_are_not_alerts():
    block=APP[APP.index("def render_team_portal"):APP.index("def ", APP.index("def render_team_portal")+10)]
    assert 'c1.caption("Lagincheckning används inte i den här turneringen.")' in block
    assert 'c2.caption("👕 Matchställ är ännu inte bekräftade.")' in block

def test_public_mobile_metrics_use_two_columns():
    assert '.public-metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;' in APP
    assert '.public-metric .value{font-size:22px!important}' in APP
