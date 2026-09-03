from pathlib import Path


def test_v412_main_publication_card_renders_after_control_header():
    source = Path("app.py").read_text(encoding="utf-8")
    control_page = source.index('if admin_page == "Kontroller":')
    header = source.index('Planeringsflöde · Kvalitetskontroll', control_page)
    main_call = source.index('show_main_control=True', control_page)
    assert header < main_call


def test_v412_global_publication_call_is_sidebar_only():
    source = Path("app.py").read_text(encoding="utf-8")
    global_call = source.index('show_main_control=False')
    control_page = source.index('if admin_page == "Kontroller":')
    assert global_call < control_page
    assert 'show_sidebar_control=True' in source[global_call:control_page]


def test_v412_control_page_reuses_publication_snapshot():
    source = Path("app.py").read_text(encoding="utf-8")
    block = source[source.index('if admin_page == "Kontroller":'):]
    assert 'control_rules = sidebar_rules' in block
    assert 'control_scheduled = int(sidebar_scheduled or 0)' in block
    before_deep = block.split('_show_deep_controls = st.toggle', 1)[0]
    assert 'SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL' not in before_deep


def test_v412_publication_view_can_render_main_without_sidebar():
    source = Path("cupnavi_core/admin_publication_view.py").read_text(encoding="utf-8")
    assert 'show_sidebar_control: bool = True' in source
    assert 'if show_sidebar_control:' in source


def test_v412_version():
    assert Path("VERSION.txt").read_text().strip() == "2026.09.03-427-TRAVEL-RULES-FLOW"
