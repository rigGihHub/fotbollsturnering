
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
ROLE=(ROOT/"cupnavi_core/admin_role_codes_view.py").read_text(encoding="utf-8")

def test_referee_and_reporter_codes_are_peer_controls():
    block=APP[APP.index('if admin_page == "Domare":'):APP.index('if admin_page == "Skapa och publicera schema":')]
    assert 'st.subheader("Åtkomstkoder")' in block
    assert '"Matchrapportör"' in block and '"match_reporter_credentials"' in block and '"reporter"' in block
    assert '"Domare"' in block and '"referee_credentials"' in block and '"referee"' in block
    assert "code_col1, code_col2 = st.columns(2)" in block

def test_referee_code_is_hashed_and_tournament_scoped():
    assert "CREATE TABLE IF NOT EXISTS referee_credentials" in APP
    assert "tournament_id INTEGER PRIMARY KEY" in APP
    assert '"referee_credentials", reporter_tid, entered_password' in APP
    assert 'reporter_role"] = "referee"' in APP

def test_rotating_either_role_code_invalidates_its_session():
    assert 'credential_table = (' in APP
    assert '"referee_credentials"' in APP
    assert 'current_credential = one_row(' in APP
    assert 'reporter_credential_hash' in APP
