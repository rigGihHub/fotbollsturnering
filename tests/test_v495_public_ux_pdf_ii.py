from pathlib import Path

VERSION = "2026.09.07-500-MULTI-DOCUMENT-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")
INFO = Path("cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
PDF_SERVICE = Path("cupnavi_core/public_pdf_download.py").read_text(encoding="utf-8")
WORKSPACE = Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")


def test_version_consistency():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in Path("cupnavi_core/version.py").read_text()


def test_pdf_worker_uses_independent_connection_not_streamlit_session_db():
    block = APP[APP.index("def _open_public_pdf_read_connection"):APP.index("def render_public_share_control")]
    assert "_new_cloud_raw_connection()" in block
    assert "st.session_state" not in block
    assert "build_public_pdf_download" in block
    assert "schedule_published=1" in PDF_SERVICE
    assert "%%EOF" in PDF_SERVICE


def test_clock_and_accessibility_are_polished_and_share_precedes_accessibility():
    assert "linear-gradient(145deg,#112d22 0%,#174936 100%)" in APP
    assert ">LIVE<" in APP
    share_pos = APP.index("render_public_share_control(tid, tournament, in_sidebar=True)")
    a11y_pos = APP.index('with st.sidebar.container(key=f"cn_sidebar_a11y_')
    assert share_pos < a11y_pos
    assert "font-size:10px!important" in APP


def test_public_nav_text_is_not_ellipsized():
    assert "text-overflow:clip!important" in STYLE
    assert "white-space:normal!important" in STYLE
    assert "max-width:none!important" in STYLE


def test_cupinfo_uses_consistent_card_grid():
    assert ".cn-info-card-grid,.cn-practical-info-card" in INFO
    assert ".cn-venue-card,.cn-practical-item,.cn-custom-info-card" in INFO
    assert "<div class='cn-info-card-grid'>" in INFO


def test_share_is_not_duplicated_inside_public_fragment():
    assert "render_public_share_control(tournament_id, tournament, in_sidebar=True)" not in WORKSPACE
    assert APP.count("render_public_share_control(tid, tournament, in_sidebar=True)") == 1
