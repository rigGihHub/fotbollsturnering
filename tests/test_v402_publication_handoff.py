from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "admin_publication_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v402_version_consistency():
    expected = "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert VERSION == expected
    assert expected in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert f'APP_BUILD_VERSION = "{expected}"' in APP


def test_main_publication_control_only_renders_on_control_page():
    assert 'show_main_control: bool = False' in VIEW
    assert 'if not show_main_control:' in VIEW
    assert 'show_main_control=(admin_page == "Kontroller")' in APP


def test_publication_is_explicit_final_step():
    assert 'Steg 6 av 6 · Publicera' in VIEW
    assert 'Publicera cupen' in VIEW
    assert 'blir cupen synlig för deltagare och publik' in VIEW


def test_sidebar_publish_control_remains_available():
    assert 'st.sidebar.subheader("Publicering")' in VIEW
    assert 'publish_from_any_admin_page_' in VIEW
