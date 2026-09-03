from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core"/"style_system.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_version():
    assert VERSION=="2026.09.03-423-PUBLIC-INFO-COLD-START"
    assert VERSION in APP

def test_empty_cup_gets_beginner_first_run():
    assert "first_run_new_cup = bool(" in APP
    assert "är skapad!" in APP
    assert "Du behöver inte kunna hur en cup ska planeras" in APP
    assert 'class="cn-first-run-steps"' in APP
    assert "1 · Lägg till lag" in APP
    assert "5 · Publicera" in APP
    assert '"Lägg till första laget →"' in APP

def test_empty_cup_hides_premature_system_noise():
    assert "if not _first_run_new_cup:" in APP
    assert "render_admin_publication_controls(" in APP
    assert "if attention and not first_run_new_cup:" in APP
    assert "show_overview_advanced = False if first_run_new_cup else st.toggle(" in APP

def test_dirty_warning_only_means_existing_schedule_is_stale():
    assert "if current_schedule_dirty and current_schedule_scheduled:" in APP

def test_calendar_popover_has_explicit_light_surfaces():
    assert '[data-baseweb="calendar"] header' in STYLE
    assert '[data-baseweb="calendar"] [role="presentation"]' in STYLE
    assert '[data-baseweb="calendar"] [data-baseweb="button"]' in STYLE
    assert 'background:#ffffff !important;' in STYLE
