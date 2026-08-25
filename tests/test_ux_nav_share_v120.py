from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_share_expands_in_place_without_navigation():
    text = app_text()
    assert "cn_share_visible_" in text
    assert "cn-share-panel-anchor" in text
    assert 'cn_share_button_' in text
    assert "popover='auto'" not in text
    assert "popovertarget=" not in text
    assert "share=1#cn-share-section" not in text
    assert "share_requested =" not in text


def test_admin_uses_two_level_navigation():
    text = app_text()
    assert "admin_group_key = f\"admin_group_{tid}\"" in text
    assert "group_cols = st.columns(len(group_names))" in text
    assert "Partners & erbjudanden" in text
    assert "Tabell & statistik" in text
    assert '["Sponsorer", "Erbjudanden"]' in text
    assert '["Tabeller", "Topplistor"]' in text
