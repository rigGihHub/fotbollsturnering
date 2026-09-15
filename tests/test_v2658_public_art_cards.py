from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_match_card_uses_the_correct_home_and_away_kits():
    source = (ROOT / "frontend-next/src/components/MatchCard.tsx").read_text()
    assert 'isAway?team?.secondary_color:team?.primary_color' in source
    assert 'isAway?team?.away_color_2:team?.home_color_2' in source
    assert 'isAway?team?.away_pattern:team?.home_pattern' in source


def test_public_art_card_shows_crest_and_outlined_svg_shirt():
    card = (ROOT / "frontend-next/src/components/MatchCard.tsx").read_text()
    kit = (ROOT / "frontend-next/src/components/TeamKit.tsx").read_text()
    layout = (ROOT / "frontend-next/src/app/layout.tsx").read_text()
    assert 'className="team-crest"' in card
    assert '<svg' in kit and 'stroke="#101f2a"' in kit
    assert 'public-masterpiece-v2658.css' in layout


def test_cover_exposes_useful_tournament_facts():
    source = (ROOT / "frontend-next/src/components/CupCover.tsx").read_text()
    assert 'teamCount' in source and 'matchCount' in source and 'groupCount' in source
