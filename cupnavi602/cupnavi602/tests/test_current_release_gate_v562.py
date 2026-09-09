from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v562_version_files_are_synchronized():
    assert VERSION == "2026.09.08-562-MY-CUPS-DASHBOARD"
    assert 'APP_BUILD_VERSION = "2026.09.08-562-MY-CUPS-DASHBOARD"' in APP
    assert 'APP_VERSION = "2026.09.08-562-MY-CUPS-DASHBOARD"' in CORE


def test_membership_snapshot_exposes_current_users_role():
    assert "tm.role AS access_role" in APP
    assert "'driftadmin' AS access_role" in APP
    assert "JOIN tournament_members tm ON tm.tournament_id=t.id" in APP
    assert "tm.organizer_account_id=?" in APP


def test_admin_login_lands_on_my_cups_dashboard():
    assert 'class="cn-create-title">Mina cuper</div>' in APP
    assert "Du ser bara cuper som du har behörighet till i vald miljö." in APP
    assert 'st.markdown("### Senaste cuper")' in APP
    assert '"Ägare", "admin": "Lokal admin", "driftadmin": "Driftadmin"' in APP


def test_environment_remains_server_side_scope_for_my_cups():
    assert 'environment = str(st.session_state.get("admin_environment", "test") or "test")' in APP
    assert "COALESCE(t.environment_type,'production')=?" in APP
    assert '"🧪 Testmiljö" if _env == "test" else "🟢 Skarp miljö"' in APP
    assert "byt miljö i vänsterflanken" in APP.lower()


def test_open_from_dashboard_goes_directly_into_selected_cup():
    anchor = '''def _open_admin_entry_tournament(tournament_id):'''
    block = APP.split(anchor, 1)[1].split("# v562:", 1)[0]
    assert 'st.session_state["admin_entry_mode"] = "manage"' in block
    assert 'st.session_state["preferred_tournament_id"] = tournament_id' in block
    assert 'st.session_state["active_tournament_selector"] = tournament_id' in block
    assert 'st.session_state["admin_manage_tournament_confirmed"] = True' in block


def test_dashboard_keeps_create_and_full_list_paths():
    assert '"＋ Skapa ny cup"' in APP
    assert '"Visa som lista"' in APP
    assert 'args=("create",)' in APP
    assert 'args=("manage",)' in APP
