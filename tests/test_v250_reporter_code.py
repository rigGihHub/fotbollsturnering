
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
TEAM=(ROOT/"cupnavi_core/team_portal.py").read_text(encoding="utf-8")

def test_secure_short_numeric_code_generator_exists():
    assert "def generate_short_numeric_code(length=4):" in TEAM
    assert 'secrets.choice("0123456789")' in TEAM

def test_reporter_credentials_are_per_tournament_and_hashed():
    assert "CREATE TABLE IF NOT EXISTS match_reporter_credentials" in APP
    assert "tournament_id INTEGER PRIMARY KEY" in APP
    assert "code_salt TEXT NOT NULL" in APP
    assert "code_hash TEXT NOT NULL" in APP
    assert "new_code_hash(new_code)" in APP

def test_admin_can_generate_four_digit_reporter_code_under_referees():
    block=APP[APP.index('if admin_page == "Domare":'):APP.index('if admin_page == "Skapa och publicera schema":')]
    assert 'st.subheader("Åtkomstkoder")' in block
    assert 'render_role_code_card("Matchrapportör", "match_reporter_credentials", "reporter")' in block
    assert '"Generera 4-siffrig kod"' in block
    assert "generate_short_numeric_code(4)" in block
    assert "Kopiera eller dela koden nu." in block

def test_reporter_login_uses_tournament_and_code():
    block=APP[APP.index("def require_match_reporter_access():"):APP.index("class CloudConnection:")]
    assert 'st.selectbox(' in block
    assert '"Turnering"' in block
    assert '"Kod"' in block
    assert 'placeholder="4 siffror"' in block
    assert '_verify_tournament_role_code(\n            "match_reporter_credentials"' in block
    assert 'reporter_auth_scope"] = "tournament"' in block

def test_rotating_code_invalidates_existing_reporter_session():
    block=APP[APP.index("def require_match_reporter_access():"):APP.index("class CloudConnection:")]
    assert 'current_credential = one_row(' in block
    assert 'reporter_credential_hash' in block
    assert "hmac.compare_digest(" in block

def test_tournament_scoped_reporter_sees_only_its_tournament():
    assert 'st.session_state.get("reporter_auth_scope") == "tournament"' in APP
    assert '_tournament_access_sql += " AND id=?"' in APP
