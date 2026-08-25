from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_brand_shell_is_centered_and_integrated():
    text = app_text()
    assert "def render_persistent_brand():" in text
    assert "left:50%;" in text
    assert "transform:translateX(-50%);" in text
    assert 'class="cn-persistent-brand"' in text
    assert "padding-top:4.85rem" in text


def test_logo_asset_present_for_v95():
    logo = Path("assets/cupnavi_logo.png")
    assert logo.exists()
    assert logo.stat().st_size > 5000
