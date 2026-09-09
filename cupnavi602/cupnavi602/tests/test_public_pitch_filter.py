from pathlib import Path

def test_public_schedule_has_pitch_filter():
    text = Path("cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")
    assert '"En plan"' in text
    assert '"Välj plan"' in text
    assert 'key=f"{key_prefix}_pitch_{tournament_id}"' in text

def test_pitch_filter_matches_pitch_number():
    from cupnavi_core.public_match_filter_logic import filter_matches
    rows=[
        {"pitch_number":1,"home_source":"team:1","away_source":"team:2"},
        {"pitch_number":2,"home_source":"team:3","away_source":"team:4"},
    ]
    result=filter_matches(rows,mode="pitch",selected=2,source_team_id=lambda source:int(source.split(":")[1]))
    assert result == [rows[1]]

def test_pitch_filter_keeps_next_match_overview_single_source():
    matcher = Path('cupnavi_core/public_matches_view.py').read_text(encoding='utf-8')
    feed = Path('cupnavi_core/public_match_feed_logic.py').read_text(encoding='utf-8')
    assert 'class="cn-next-match"' not in matcher
    assert "Cupen just nu" in feed
