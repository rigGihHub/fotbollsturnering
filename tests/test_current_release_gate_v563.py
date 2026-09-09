from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE_VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_release_files_are_synchronized():
    assert VERSION == "2026.09.08-563-INVITATION-LINKS"
    assert VERSION in APP
    assert VERSION in CORE_VERSION


def test_v34_creates_secure_invitation_schema(tmp_path):
    from cupnavi_core.migrations import ensure_v34_schema_compat
    con = sqlite3.connect(tmp_path / "invite.db")
    con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY)")
    con.execute("CREATE TABLE organizer_accounts(id INTEGER PRIMARY KEY)")
    ensure_v34_schema_compat(con)
    cols = {row[1] for row in con.execute("PRAGMA table_info(tournament_admin_invitations)")}
    assert {"tournament_id", "email", "token_hash", "expires_at", "accepted_at", "revoked_at"} <= cols


def test_invitation_uses_hash_expiry_and_email_binding():
    assert 'secrets.token_urlsafe(32)' in APP
    assert 'hashlib.sha256(str(token).encode("utf-8")).hexdigest()' in APP
    assert 'expires_at' in APP
    assert '_normalize_account_email(account["email"]) != _normalize_account_email(invite["email"])' in APP
    assert 'accepted_at IS NULL AND revoked_at IS NULL' in APP


def test_invitation_link_opens_admin_and_can_create_profile():
    assert '_direct_admin_invite' in APP
    assert 'st.session_state["view_mode"] = "Admin"' in APP
    assert 'Skapa profil och acceptera' in APP
    assert 'Logga in och acceptera' in APP
    assert 'Acceptera och öppna cupen' in APP


def test_owner_can_create_track_and_revoke_pending_invites():
    assert 'Bjud in lokal administratör' in APP
    assert 'Skapa inbjudningslänk' in APP
    assert 'Väntande inbjudningar' in APP
    assert 'Återkalla vald inbjudan' in APP
    assert 'UPDATE tournament_admin_invitations SET revoked_at=' in APP


def test_acceptance_grants_only_invited_tournament_admin_membership():
    assert 'INSERT INTO tournament_members(tournament_id,organizer_account_id,role)' in APP
    assert '(int(invite["tournament_id"]), int(account_id), "admin")' in APP
    assert "CASE WHEN tournament_members.role='owner' THEN 'owner' ELSE excluded.role END" in APP
