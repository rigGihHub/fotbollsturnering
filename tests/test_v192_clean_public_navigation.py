from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_tournament_view_collapses_role_navigation():
    assert 'st.session_state["role_nav_expanded"] = False' in APP
    assert 'if current_mode == "Turneringsvy" and not role_nav_expanded:' in APP
    compact = APP[APP.index('if current_mode == "Turneringsvy" and not role_nav_expanded:'):APP.index('    else:\n        # Efter att Admin öppnats')]
    assert 'st.columns(2)' in compact
    assert 'args=("Turneringsvy",)' in compact
    assert 'args=("Admin",)' in compact
    assert 'Lagportal' not in compact
    assert 'Matchrapportör' not in compact
    assert 'args=("Om",)' not in compact

def test_admin_expands_role_navigation():
    assert 'if mode == "Admin":' in APP
    assert 'st.session_state["role_nav_expanded"] = True' in APP
    expanded = APP[APP.index('# Efter att Admin öppnats visas rollväxlarna'):APP.index('view_mode = st.session_state["view_mode"]')]
    assert 'st.columns(5)' in expanded
    assert '"Lagportal"' in expanded
    assert 'tr("Matchrapportör")' in expanded
    assert 'tr("Admin")' in expanded
    assert 'tr("Om")' in expanded
