from pathlib import Path

from cupnavi_core.about import feature_catalog, about_intro


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_about_page_is_catalog_driven():
    text = app_text()
    assert "def render_about_page():" in text
    assert "feature_catalog(language)" in text
    assert len(feature_catalog("sv")) >= 8
    assert about_intro("en")["title"] == "About CupNavi"


def test_public_only_mode_excludes_privileged_modes():
    text = app_text()
    assert 'public_app_mode = str(st.query_params.get("public_only", "")).lower()' in text
    assert '["Turneringsvy", "Om"]' in text
    assert 'if public_app_mode:' in text


def test_about_catalog_is_bilingual_and_has_unique_ids():
    sv = feature_catalog("sv")
    en = feature_catalog("en")
    assert [item["id"] for item in sv] == [item["id"] for item in en]
    assert len({item["id"] for item in sv}) == len(sv)
    assert all(item["title"] and item["description"] for item in sv + en)
