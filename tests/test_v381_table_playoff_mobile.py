from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRESENTATION=(ROOT/"cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_release_version():
    assert VERSION=="2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"

def test_group_table_uses_light_product_ui():
    assert ".texttv-wrap{{overflow-x:auto;border:1px solid #dbe4de" in PRESENTATION
    assert ".texttv-table{{width:100%;border-collapse:collapse;font-family:inherit;color:#172033}}" in PRESENTATION
    assert "background:#07111f" not in PRESENTATION

def test_mobile_table_keeps_only_decision_relevant_columns():
    assert ".texttv-table th:nth-child(4),.texttv-table td:nth-child(4)" in PRESENTATION
    assert ".texttv-table th:nth-child(8),.texttv-table td:nth-child(8)" in PRESENTATION
    assert ".texttv-table th:nth-child(9),.texttv-table td:nth-child(9){{width:34px}}" in PRESENTATION
    assert ".texttv-table th:nth-child(10),.texttv-table td:nth-child(10){{width:34px;font-weight:900}}" in PRESENTATION
    assert "content:'Vidare'" in PRESENTATION

def test_playoff_has_mobile_round_cards_without_extra_query():
    assert "mobile_rounds = []" in PRESENTATION
    assert "cn-playoff-mobile-round" in PRESENTATION
    assert "cn-playoff-mobile-match" in PRESENTATION
    assert "for stage_name, stage_matches in main_stages:" in PRESENTATION
    # Bracket data still comes from the single existing bracket query.
    assert PRESENTATION.count('SELECT * FROM matches WHERE bracket_id=? ORDER BY round_no,match_no') == 1

def test_mobile_hides_wide_canvas_but_desktop_tree_remains():
    assert ".classic-bracket-scroll {{display:none}}" in PRESENTATION
    assert ".cn-playoff-mobile {{display:block}}" in PRESENTATION
    assert '<div class="classic-bracket">' in PRESENTATION
    assert "stage_centers" in PRESENTATION
