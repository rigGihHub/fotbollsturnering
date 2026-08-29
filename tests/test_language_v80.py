from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_language_selector_exists():
    text = app_text()
    assert 'language_options = {"sv": "Svenska", "en": "English"}' in text
    assert 'key="language_selector"' in text

def test_translation_layer_has_fallback():
    text = app_text()
    assert "def tr(value):" in text
    assert 'TRANSLATIONS["en"].get(value)' in text

def test_public_navigation_is_translated():
    nav_text = Path('cupnavi_core/public_navigation_view.py').read_text(encoding='utf-8')
    assert 'translate(desktop_label)' in nav_text
    assert 'translate(mobile_label)' in nav_text
    assert 'translate=tr' in app_text()
    from cupnavi_core.public_view_logic import public_navigation_specs
    assert [item[2] for item in public_navigation_specs()[:4]] == [
        "Cupinfo","Schema & resultat","Tabeller","Slutspel"
    ]

def test_admin_nav_labels_are_translated():
    text = app_text()
    assert '("Adminöversikt", tr("Översikt"))' in text
    assert '("Besöksstatistik", tr("Besök"))' in text

def test_reporter_tabs_are_translated():
    text = Path("cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")
    assert 'deps.translate("Matchhändelser")' in text
    assert 'deps.translate("Domarcentral")' in text
    assert 'deps.translate("Offlineutkast")' in text
    assert 'translate=tr' in app_text()
