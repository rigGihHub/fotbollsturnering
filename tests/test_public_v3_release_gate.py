from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VIEW=(ROOT/"frontend-next/src/components/PublicCupView.tsx").read_text(encoding="utf-8")
MATCH=(ROOT/"frontend-next/src/components/MatchCard.tsx").read_text(encoding="utf-8")
STANDINGS=(ROOT/"frontend-next/src/components/TextTvStandings.tsx").read_text(encoding="utf-8")
CSS=(ROOT/"frontend-next/src/app/public-atmosphere-v2671.css").read_text(encoding="utf-8")
REPO=(ROOT/"cupnavi_api/repository.py").read_text(encoding="utf-8")

def test_public_matches_default_to_all():
    assert 'useState<MatchView>("all")' in VIEW
    assert '>Alla <b>{orderedMatches.length}</b>' in VIEW

def test_public_kit_visibility_is_independent():
    assert "showPublicKits" in VIEW and "showPublicAwayKits" in VIEW and "showPublicLogos" in VIEW
    assert "showAwayKits={showPublicAwayKits}" in VIEW
    assert "usableLogo" in MATCH and "onError={()=>setLogoFailed(true)}" in MATCH

def test_standings_have_no_legacy_330_label_and_support_playoff_mapping():
    assert "TEXT-TV 330" not in VIEW.split('{tab==="table"')[1].split('{tab==="stats"')[0]
    assert "positionDestinations" in STANDINGS
    assert "playoffPositionMap" in VIEW
    assert "texttv__legend" in CSS

def test_cupinfo_inherits_rules_setup_and_playoffs():
    for token in ("points_win","table_tiebreak","minimum_team_rest_minutes","pitch_break_minutes","avoid_consecutive_matches"):
        assert token in VIEW
    assert "public-pitch-list" in VIEW
    assert "cup.brackets.map" in VIEW
    for token in ("halves","minutes_per_half","playoff_format","show_public_away_kits"):
        assert token in REPO

def test_mobile_public_view_guards_long_team_names_and_table_width():
    assert "white-space:normal!important" in CSS
    assert ".page-shell--public-v3 .texttv table{min-width:620px!important}" in CSS
    assert "grid-template-columns:minmax(0,1fr) 48px minmax(0,1fr)" in CSS

def test_finished_scores_are_visually_prominent():
    assert ".public-match-card--done .public-match-card__score strong" in CSS
    assert "font-size:22px!important" in CSS
