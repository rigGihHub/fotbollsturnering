from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def public_block():
    text = app_text()
    start = text.index("def render_public_view(")
    end = text.index("def render_match_reporter_view(", start)
    return text[start:end]


def test_three_large_public_navigation_buttons_exist():
    block = public_block()
    assert '(nav1, "Matcher", "🗓️"' in block
    assert '(nav2, "Statistik", "🏆"' in block
    assert '(nav3, "Info", "ℹ️"' in block
    assert 'type="primary" if active else "secondary"' in block


def test_matches_merge_schedule_and_results_and_keep_filters():
    block = public_block()
    assert 'if public_page == "Matcher":' in block
    assert '[tr("Alla"), tr("Kommande"), tr("Spelade")]' in block
    assert 'row_show_results = match_is_played if show_results is None' in block
    assert '[tr("Alla matcher"), tr("En grupp"), tr("Ett lag"), tr("En plan")]' in block


def test_info_rules_derive_from_all_requested_saved_settings():
    text = app_text()
    for required in (
        'rules["halves"]',
        'rules["minutes_per_half"]',
        'rules["halftime_minutes"]',
        'rules["pitch_break_minutes"]',
        'rules["minimum_team_rest_minutes"]',
        'rules["avoid_consecutive_matches"]',
        'rules["consecutive_match_break_minutes"]',
        'rules["pitch_count"]',
        'tournament["points_win"]',
        'tournament["points_draw"]',
        'tournament["points_loss"]',
        'tournament["table_tiebreak"]',
        'tournament["playoff_format"]',
        'tournament["bronze_match"]',
        'tournament["playoff_tie_rule"]',
        'tournament["extra_time_minutes"]',
    ):
        assert required in text


def test_statistics_include_goal_assist_cards_and_playoffs():
    block = public_block()
    assert 'st.subheader(tr("Skytteliga"))' in block
    assert 'st.subheader(tr("Assistliga"))' in block
    assert 'st.subheader(tr("Kortstatistik"))' in block
    assert '"Gula": int(r["yellow_cards"] or 0)' in block
    assert '"Röda": int(r["red_cards"] or 0)' in block
    assert 'if stats_section == tr("Slutspel"):' in block


def test_info_page_keeps_custom_and_practical_content():
    block = public_block()
    assert 'if tournament["public_information"]:' in block
    assert 'Information från arrangören' in block
    assert 'tournament["arena_address"]' in block
    assert 'tournament["kiosk_information"]' in block
    assert 'tournament["organizer_phone"]' in block
    assert 'tournament["feedback_email"]' in block
    assert 'tournament["instagram_url"]' in block
    assert 'SELECT * FROM functionaries' in block
    assert 'SELECT * FROM offers' in block
    assert 'SELECT * FROM sponsors' in block
    assert 'logo_data_uri' in block
    assert 'Rapportera problem eller lämna synpunkt' in block


def test_admin_field_is_clear_about_public_info_page():
    text = app_text()
    assert '"Egen information på publika infosidan"' in text
    assert '"Visas under Info efter de automatiskt skapade cupreglerna."' in text
