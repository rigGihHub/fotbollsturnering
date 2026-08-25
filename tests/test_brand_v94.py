from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_brand_logo_asset_is_packaged():
    logo = Path("assets/cupnavi_logo.png")
    assert logo.exists()
    assert logo.stat().st_size > 1000


def test_logo_is_rendered_as_persistent_global_brand():
    text = app_text()
    assert "def render_persistent_brand():" in text
    assert "position:fixed;" in text
    assert "cn-persistent-brand" in text
    assert "render_persistent_brand()" in text
    assert 'CUPNAVI_LOGO_FILE = Path(__file__).with_name("assets") / "cupnavi_logo.png"' in text


def test_global_shell_is_multisport_neutral():
    text = app_text()
    assert 'st.set_page_config(page_title="CupNavi", page_icon="🏆", layout="wide")' in text
    assert "st.sidebar.title(f\"🏆 {tr(\'Turneringar\')}\")" in text
    assert 'st.title("🏆 CupNavi")' in text
    assert '(nav1, "Matcher", "🗓️", tr("Spelschema & resultat"))' in text
