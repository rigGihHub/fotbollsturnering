from pathlib import Path


def test_v413_team_portal_session_binds_to_credential_hash():
    source = Path("cupnavi_core/team_portal_view.py").read_text(encoding="utf-8")
    assert '"credential_hash": str(credential["code_hash"])' in source
    assert 'current_credential = fetch_portal_credential' in source
    assert 'st.session_state.pop("participant_portal_auth", None)' in source
    assert 'Lagkoden har ändrats. Logga in med den nya koden.' in source


def test_v413_version():
    assert Path("VERSION.txt").read_text().strip() == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"
