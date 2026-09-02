from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def public_block():
    return Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")


def test_public_competition_navigation_exists_and_has_active_state():
    from cupnavi_core.public_view_logic import public_navigation_specs
    block = public_block()
    nav = Path('cupnavi_core/public_navigation_view.py').read_text(encoding='utf-8')
    assert len(public_navigation_specs()) == 5
    assert [item[0] for item in public_navigation_specs()] == ["Matcher","Mitt lag","Tabeller","Slutspel","Info"]
    assert 'active_class = "active" if current_page == page_value else ""' in nav
    assert "role='button'" in nav
    assert 'st.segmented_control(' in block


def test_matches_merge_schedule_and_results_and_keep_filters():
    block = public_block()
    matches_view = Path('cupnavi_core/public_matches_view.py').read_text(encoding='utf-8')
    assert 'if public_page == "Matcher":' in block
    assert '[tr("Alla"), tr("Kommande"), tr("Spelade")]' in matches_view
    match_cards = Path("cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")
    assert 'row_show_results = match_is_played if show_results is None' in match_cards
    filter_view = Path("cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")
    for option in ['tr("Alla matcher")', 'tr("En grupp")', 'tr("Ett lag")', 'tr("En plan")']:
        assert option in filter_view


def test_info_rules_derive_from_all_requested_saved_settings():
    text = Path("cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")
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
    block = Path("cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
    assert 'st.subheader(tr("Skytteliga"))' in block
    assert 'st.subheader(tr("Assistliga"))' in block
    assert 'st.subheader(tr("Kortstatistik"))' in block
    assert '"yellow_cards": int(r["yellow_cards"] or 0)' in block
    assert '"red_cards": int(r["red_cards"] or 0)' in block
    assert '"Gula": r["yellow_cards"]' in block
    assert '"Röda": r["red_cards"]' in block
    assert 'if stats_section == tr("Slutspel"):' in block


def test_info_page_keeps_custom_and_practical_content():
    block = Path("cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
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
