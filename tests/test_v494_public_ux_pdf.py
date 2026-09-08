from pathlib import Path

VERSION = "2026.09.07-525-OPTIONAL-REFEREE-SETUP"
APP = Path("app.py").read_text(encoding="utf-8")
FILTERS = Path("cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")
MATCHES = Path("cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
CARDS = Path("cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")
WORKSPACE = Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
STATS = Path("cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
INFO = Path("cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def test_release_version_is_consistent():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in Path("cupnavi_core/version.py").read_text()


def test_weather_and_match_events_are_default_on_when_available():
    weather_block = FILTERS[FILTERS.index('"🌦️ " + tr("Visa väderprognos")'):]
    assert "value=True" in weather_block[:250]
    assert '"⚽ Målskyttar och kort"' in FILTERS
    event_block = FILTERS[FILTERS.index('"⚽ Målskyttar och kort"') - 180:]
    assert "value=True" in event_block[:500]
    assert '"enable_scorer_leaderboard"' in MATCHES
    assert '"enable_card_statistics"' in MATCHES


def test_weather_toggle_never_renders_as_silent_blank():
    assert 'weather_status = "Prognos visas för kommande matcher inom 16 dagar."' in CARDS
    assert 'if not weather_text:' in CARDS


def test_pdf_and_information_screen_live_under_share_control():
    share_start = APP.index("def render_public_share_control")
    share_end = APP.index("@st.cache_data(show_spinner=False)", share_start)
    share = APP[share_start:share_end]
    assert '"Skapa och ladda ned PDF"' in share
    assert 'data=lambda: _build_public_cup_program_pdf_bytes' in share
    assert 'on_click="ignore"' in share
    assert '"🖥 Informationsskärm"' in share
    assert "cn-screen-link" not in WORKSPACE


def test_pdf_builder_validates_pdf_signature_and_is_lazy():
    assert 'def _build_public_cup_program_pdf_bytes' in APP
    PDF_SERVICE = Path("cupnavi_core/public_pdf_download.py").read_text(encoding="utf-8")
    assert 'schedule_published=1' in PDF_SERVICE
    assert 'data.startswith(b"%PDF")' in PDF_SERVICE
    public_block = APP[APP.index('if view_mode == "Turneringsvy":'):APP.index('# SNABB ADMINNAVIGERING')]
    assert 'with st.expander("🖨️ Skriv ut / PDF"' not in public_block


def test_all_public_group_tables_are_open_by_default():
    assert 'st.caption(f"{len(groups)} grupper · alla tabeller visas")' in STATS
    assert "expanded=True" in STATS


def test_cupinfo_and_sidebar_have_explicit_visual_hierarchy():
    assert ".cn-info-guide-head{background:#173a56!important" in INFO
    assert ".cn-venue-copy strong,.cn-venue-copy small,.cn-venue-copy span,.cn-practical-item small,.cn-practical-item strong{display:block!important" in INFO
    assert "compact Text-TV control rail" in STYLE
    assert 'border-left:5px solid #1fa55b!important' in STYLE
