from pathlib import Path

VERSION = "2026.09.07-524-PRIMARY-FLOW-PITCH-COUNT-FIX"
APP = Path("app.py").read_text(encoding="utf-8")
FOLLOW = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def test_version_is_v466():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_multiple_favorites_are_supported():
    assert 'st.multiselect(' in FOLLOW
    assert '"Mina favoritlag"' in FOLLOW
    assert '_favorites_key = f"public_favorite_teams_{tournament_id}"' in FOLLOW
    assert 'st.query_params["teams"]' in FOLLOW


def test_favorites_can_span_classes():
    assert 'row_value(row, "age_class", "")' in FOLLOW
    assert 'f"{name} · {age_class}" if age_class else name' in FOLLOW


def test_multi_favorite_overview_reuses_loaded_matches():
    assert 'build_favorite_team_snapshot(' in FOLLOW
    assert 'published_matches,' in FOLLOW
    assert '.cn-multi-favorite-card' in STYLE


def test_public_pdf_is_lazy_and_uses_existing_engine():
    share_block = APP[APP.index('def render_public_share_control'):APP.index('@st.cache_data(show_spinner=False)', APP.index('def render_public_share_control'))]
    assert '"Skapa och ladda ned PDF"' in share_block
    assert 'data=lambda: _build_public_cup_program_pdf_bytes' in share_block
    assert 'on_click="ignore"' in share_block
    assert 'from cupnavi_core.pdf_export import build_cup_program_pdf' in Path('cupnavi_core/public_pdf_download.py').read_text(encoding='utf-8')
    pdf_service = Path('cupnavi_core/public_pdf_download.py').read_text(encoding='utf-8')
    assert 'data.startswith(b"%PDF")' in pdf_service


def test_public_pdf_only_uses_published_scheduled_matches():
    assert 'schedule_published=1' in APP
