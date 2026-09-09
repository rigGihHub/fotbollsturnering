from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_integrated_share_popover_replaces_old_messenger_deeplink():
    text = app_text()
    start = text.index("def render_public_share_control(")
    end = text.index("@st.cache_data(show_spinner=False)", start)
    block = text[start:end]
    assert 'with st.popover("Dela"' in block
    assert "WhatsApp" in block
    assert "mailto:?subject=" in block
    assert "sms:?&body=" in block
    assert "fb-messenger://share/" not in text
    assert "navigator.share" not in text

def test_global_translation_hooks_cover_common_streamlit_ui():
    text = app_text()
    assert "def _install_streamlit_translation_hooks():" in text
    assert "DeltaGenerator.data_editor = data_editor_wrapper" in text
    assert 'for method_name in ("selectbox", "radio")' in text
    assert "EN_PHRASES" in text

def test_centered_tables_translate_headers():
    text = app_text()
    assert "display_dataframe = _translate_dataframe_for_display(dataframe)" in text

def test_analytics_skips_database_between_samples():
    text = app_text()
    start = text.index("def track_public_visit(")
    end = text.index("def qr_png_bytes", start)
    block = text[start:end]
    assert "if not count_view:" in block
    # v1.192+: analytics uses one atomic UPSERT; throttling must happen before any write.
    assert "ON CONFLICT(tournament_id,session_token) DO UPDATE" in block
    assert block.index("if not count_view:") < block.index("run(")

def test_public_view_batches_team_and_event_data():
    text = app_text()
    block = Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
    matches_view = Path("cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
    repository = Path("cupnavi_core/public_match_repository.py").read_text(encoding="utf-8")
    assert "public_team_by_id" in block
    assert "public_events_by_match" in matches_view
    # v1.277 keeps event loading scoped to visible played matches and moves SQL
    # behind the read-only public repository boundary.
    assert "visible_played_match_ids" in matches_view
    assert "WHERE s.match_id IN ({placeholders})" in repository
    assert 'if public_page == "Matcher":' in block
