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

def test_public_tabs_are_translated():
    text = app_text()
    assert 'tr("Spelschema")' in text
    assert 'tr("Resultat")' in text
    assert 'tr("Tabeller")' in text

def test_admin_nav_labels_are_translated():
    text = app_text()
    assert '("Adminöversikt", tr("Översikt"))' in text
    assert '("Besöksstatistik", tr("Besök"))' in text

def test_reporter_tabs_are_translated():
    text = app_text()
    assert 'st.tabs([tr("Resultat"), tr("Matchhändelser")])' in text
