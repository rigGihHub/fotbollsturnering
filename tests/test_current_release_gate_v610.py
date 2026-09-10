from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VER = "2026.09.10-610-SIGNATURE-MATCHDAY-LAYER"


def test_version_sync():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VER
    assert VER in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert VER in (ROOT / "app.py").read_text(encoding="utf-8")


def test_signature_matchday_css_exists():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    for token in ["Signature Matchday Layer", ".public-match-card.is-live", ".cn-playoff-mobile-match", ".cn-screen-card", ".texttv-kicker:before"]:
        assert token in app


def test_match_card_uses_theme_shell():
    code = (ROOT / "cupnavi_core" / "public_match_cards.py").read_text(encoding="utf-8")
    assert 'data-match-no="MATCH ' in code
    assert 'style="border:1px solid #d1d5db' not in code


def test_kit_marker_is_shirt_silhouette():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert ".cn-match-kit" in app
    assert "clip-path:polygon" in app


def test_readability_and_motion_contracts():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "--cn610-ink:#102630" in app
    assert "--cn610-tvtext:#F4FFF8" in app
    assert "prefers-reduced-motion:reduce" in app
