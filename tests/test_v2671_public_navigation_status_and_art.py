from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_today_tab_and_matchday_panel_are_removed():
    view = (ROOT / "frontend-next/src/components/PublicCupView.tsx").read_text()

    assert 'type Tab="matches"|"table"|"stats"|"playoff"|"info"' in view
    assert 'useState<Tab>("matches")' in view
    assert '["matchday","Idag"]' not in view
    assert 'tab==="matchday"' not in view


def test_preview_warning_depends_on_actual_publication_status():
    preview = (ROOT / "frontend-next/src/components/public-cup-preview.tsx").read_text()

    assert "!data.cup.tournament.is_published" in preview
    assert "CUPEN ÄR INTE PUBLICERAD" not in preview
    assert "FÖRHANDSGRANSKNING · UTKAST" in preview


def test_public_background_uses_smooth_sports_art():
    view = (ROOT / "frontend-next/src/components/PublicCupView.tsx").read_text()
    css = (ROOT / "frontend-next/src/app/public-atmosphere-v2671.css").read_text()

    for item in ("ball", "cone", "whistle", "boot"):
        assert f"sport-art--{item}" in view
        assert f".sport-art--{item}" in css
    assert "body:has(.page-shell--matchday)" in css
