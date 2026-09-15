from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TABLE=(ROOT/"frontend-next/src/components/TextTvStandings.tsx").read_text()
COVER=(ROOT/"frontend-next/src/components/CupCover.tsx").read_text()
SHARE=(ROOT/"frontend-next/src/components/CupShareButton.tsx").read_text()
CSS=(ROOT/"frontend-next/src/app/public-texttv-v2675.css").read_text()
KIT=(ROOT/"cupnavi_core/ai_kit_suggestion.py").read_text()

def test_standings_copy_classic_text_tv_hierarchy():
    assert "texttv--standings" in TABLE
    assert 'index<2?"is-leading"' in TABLE
    for color in ("#001cf5", "#00ff39", "#fff200", "#00e7ff"):
        assert color in CSS
    assert '"Courier New"' in CSS

def test_share_action_is_visible_inside_cup_cover():
    assert "<CupShareButton" in COVER
    assert "navigator.share" in SHARE
    assert "navigator.clipboard.writeText" in SHARE
    assert "cup-cover__share" in CSS

def test_social_media_is_bounded_supporting_evidence_for_kits():
    assert "Instagram- och Facebook-inlägg" in KIT
    assert "två aktuella bilder" in KIT
    assert "kräver inloggning är inte bevis" in KIT
