from pathlib import Path
import sqlite3

from cupnavi_core.migrations import ensure_v33_schema_compat, LATEST_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE_VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_release_files_are_synchronized():
    assert VERSION == "2026.09.08-554-TOURNAMENT-TENANT-ISOLATION"
    assert VERSION in APP
    assert VERSION in CORE_VERSION
    assert LATEST_SCHEMA_VERSION >= 33


def test_v33_creates_account_and_membership_schema():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY)")
    ensure_v33_schema_compat(con)
    account_cols = {row[1] for row in con.execute("PRAGMA table_info(organizer_accounts)")}
    member_cols = {row[1] for row in con.execute("PRAGMA table_info(tournament_members)")}
    assert {"id", "email", "password_salt", "password_hash", "disabled_at"} <= account_cols
    assert {"tournament_id", "organizer_account_id", "role"} <= member_cols


def test_admin_list_is_membership_scoped_for_organizers():
    assert "JOIN tournament_members tm ON tm.tournament_id=t.id" in APP
    assert "tm.organizer_account_id=?" in APP
    assert "_cupnavi_shell_cache_admin_tournaments_account_" in APP


def test_every_selected_admin_tournament_has_server_side_guard():
    assert 'if view_mode == "Admin" and not can_administer_tournament(int(tid)):' in APP
    assert 'Du har inte behörighet till den här turneringen.' in APP
    assert "SELECT 1 AS ok FROM tournament_members WHERE tournament_id=? AND organizer_account_id=?" in APP


def test_new_cups_and_copies_are_owned_by_current_account():
    assert 'grant_current_account_tournament_access(new_tournament_id, "owner")' in APP
    assert 'grant_current_account_tournament_access(new_id, "owner")' in APP
    assert 'grant_current_account_tournament_access(restored_tid, "owner")' in APP


def test_passwords_are_scrypt_hashed_and_superadmin_is_separate():
    assert "hashlib.scrypt(" in APP
    assert "password_salt" in APP and "password_hash" in APP
    assert "CupNavi driftadmin" in APP
    assert "Dela inte detta lösenord med arrangörer" in APP


def test_previous_v553_admin_flow_and_smart_import_survive():
    assert '("Domare", "Domare")' in APP
    assert 'if admin_page == "Övrigt":' in APP
    assert 'Vad vill du lyfta in i CupNavi?' in APP


def test_successful_account_and_superadmin_login_rerun_after_credentials():
    assert 'st.session_state["organizer_account_id"] = int(account["id"])' in APP
    assert 'st.session_state["admin_authenticated"] = True' in APP
    assert APP.count('st.rerun()') > 10
