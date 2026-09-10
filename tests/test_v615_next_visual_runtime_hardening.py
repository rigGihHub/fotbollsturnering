from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_pwa_not_registered_in_dev():
    pwa = (ROOT / "frontend-next/src/components/PwaBoot.tsx").read_text()
    assert 'process.env.NODE_ENV !== "production"' in pwa
    assert "getRegistrations" in pwa
    assert 'register("/sw.js")' in pwa

def test_theme_color_uses_viewport_export():
    layout = (ROOT / "frontend-next/src/app/layout.tsx").read_text()
    assert "export const viewport" in layout
    metadata_block = layout.split("export const viewport", 1)[0]
    assert "themeColor" not in metadata_block

def test_matchday_hero_search_is_not_limited_to_first_18():
    view = (ROOT / "frontend-next/src/components/PublicCupView.tsx").read_text()
    assert "const orderedMatches" in view
    assert "const nextAny=orderedMatches.find" in view

def test_home_is_public_product_entry_not_dev_instruction():
    home = (ROOT / "frontend-next/src/app/page.tsx").read_text()
    assert "Cupdagen. Samlad." in home
    assert "/cup/din-public-key" not in home
