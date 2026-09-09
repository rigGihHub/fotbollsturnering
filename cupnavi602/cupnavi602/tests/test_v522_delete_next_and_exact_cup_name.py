from pathlib import Path

from cupnavi_core.public_shell_view import build_public_hero_html

ROOT = Path(__file__).resolve().parents[1]


def test_public_hero_preserves_exact_cup_name_case():
    tournament = {"name": "Slottskampen", "location": "Örebro"}
    html = build_public_hero_html(
        tournament,
        lifecycle_status="published",
        cup_date_label=lambda _t: "27 augusti 2026",
        row_value=lambda row, key, default=None: row.get(key, default),
        translate=lambda text: text,
    )
    assert "Slottskampen" in html
    assert "SLOTTSKAMPEN" not in html


def test_pdf_program_does_not_force_tournament_name_to_uppercase():
    source = (ROOT / "cupnavi_core" / "pdf_export.py").read_text(encoding="utf-8")
    assert "tournament_name.upper()" not in source


def test_public_hero_css_explicitly_disables_name_case_transformation():
    source = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
    assert ".cup-hero .title" in source
    assert "text-transform:none !important" in source


def test_trash_and_delete_clear_stale_widget_selection_state():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'st.session_state.pop("trashed_tournament_target_v502", None)' in source
    assert '"active_tournament_selector", "main_active_tournament_selector"' in source
    assert 'st.session_state["active_tournament_selector"] = _remaining_ids[0]' in source
