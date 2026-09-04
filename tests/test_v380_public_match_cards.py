from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CARD=(ROOT/"cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_release_version():
    assert VERSION=="2026.09.04-449-MOBILE-PLAYOFF-ACTION"

def test_match_card_prioritizes_time_pitch_and_status():
    assert 'class="cn-match-time"' in CARD
    assert 'class="cn-match-place"' in CARD
    assert 'class="cn-match-status"' in CARD
    assert 'time_label = match_start_dt.strftime("%H:%M")' in CARD
    assert "pitch_text = public_pitch_label(match_row)" in CARD

def test_upcoming_match_gets_relative_time_without_new_data_source():
    assert 'relative_text = f"om {minutes_until} min"' in CARD
    assert 'relative_text = f"om {minutes_until // 60} h {minutes_until % 60:02d} min"' in CARD
    assert "match_start_dt - now" in CARD

def test_card_uses_real_match_number_when_available():
    assert 'match_number = row_value(match_row, "match_no", number) or number' in CARD

def test_team_names_remain_primary_and_secondary_details_remain_secondary():
    assert 'class="cn-match-teams"' in CARD
    assert 'class="public-team-name"' in CARD
    assert '<small class="kit-label">Hemmalag</small>' in CARD
    assert '<div class="public-match-secondary">{weather_html}{referee_html}</div>' in CARD

def test_live_upcoming_and_finished_have_distinct_visual_states():
    assert '"is-live" if explicit_status in {MATCH_LIVE, MATCH_HALFTIME}' in CARD
    assert ".public-match-card.is-live{" in STYLE
    assert ".public-match-card.is-upcoming::before" in STYLE
    assert ".public-match-card.is-finished{" in STYLE

def test_mobile_card_density_is_explicit():
    assert "@media(max-width:680px)" in STYLE
    assert ".public-match-card{padding:11px 10px 10px 13px!important" in STYLE
