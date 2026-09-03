from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_version():
    assert VERSION=="2026.09.03-414-PITCH-TIMING-MODE"
    assert VERSION in APP

def test_setup_uses_beginner_language():
    assert '### 1. Vilka ska spela?' in SETUP
    assert 'P2014 betyder pojkar födda 2014' in SETUP
    assert '### 2. Vad har ni tillgång till?' in SETUP
    assert 'Du behöver inte kunna cupregler i förväg.' in SETUP

def test_guided_recommendation_reuses_existing_engine():
    assert 'st.markdown("### CupNavis förslag")' in SETUP
    assert '_guided_format_rec = recommend_tournament_format(' in SETUP
    assert 'sport_setup_recommendation' in SETUP
    assert 'Varför rekommenderar CupNavi detta?' in SETUP

def test_guided_accept_is_explicit_and_safe():
    assert '"Använd CupNavis förslag"' in SETUP
    assert 'recommended_group_count=?,recommended_group_size=?,recommended_playoff_size=?' in SETUP
    assert 'Den skapar inte grupper, matcher eller schema.' in SETUP

def test_capacity_warning_is_explained():
    assert 'Förslaget ryms inte bekvämt i nuvarande plantid.' in SETUP
    assert '_guided_format_rec["fits_capacity"]' in SETUP

def test_fast_track_language_is_calmer():
    assert '#### Redo att lägga till lag' in SETUP
    assert '"Fortsätt → Lägg till lag"' in SETUP
    assert '"Visa och ändra alla regler & format"' in SETUP
