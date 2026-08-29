from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core/admin_role_codes_view.py").read_text(encoding="utf-8")


def test_v297_role_code_presentation_is_extracted():
    assert "from cupnavi_core.admin_role_codes_view import render_role_code_card" in APP
    assert "def render_role_code_card(" in VIEW
    assert '"Generera 4-siffrig kod"' in VIEW
    assert '"Regenerera ny kod"' in VIEW
    assert '"Ja, regenerera"' in VIEW
    assert '"Avbryt"' in VIEW


def test_v297_sensitive_credential_write_stays_in_app_layer():
    block = APP[APP.index("def _rotate_admin_role_code"):APP.index("code_col1, code_col2 = st.columns(2)")]
    assert "generate_short_numeric_code(4)" in block
    assert "new_code_hash(new_code)" in block
    assert "with db() as con:" in block
    assert "con.commit()" in block
    assert "INSERT INTO {table_name}" in block
    assert "UPDATE {table_name}" in block


def test_v297_view_receives_write_callback_instead_of_database_access():
    assert "rotate_code: Callable[[str], str]" in VIEW
    assert "rotate_code(table_name)" in VIEW
    assert "with db()" not in VIEW
    assert ".execute(" not in VIEW


def test_v297_both_tournament_roles_keep_peer_cards():
    domare = APP[APP.index('if admin_page == "Domare":'):APP.index('with st.form("new_referee"')]
    assert '"Matchrapportör"' in domare
    assert '"match_reporter_credentials"' in domare
    assert '"Domare"' in domare
    assert '"referee_credentials"' in domare
    assert "code_col1, code_col2 = st.columns(2)" in domare
