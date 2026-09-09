from pathlib import Path
from cupnavi_core.public_match_filter_logic import filter_matches, sort_public_matches

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")

def _source_team_id(source):
    return int(source.split(":")[1])

def test_team_filter_is_pure_and_correct():
    rows=[
        {"id":1,"home_source":"team:1","away_source":"team:2","group_id":10,"pitch_number":1,"scheduled_start":"2026-08-26T10:00:00"},
        {"id":2,"home_source":"team:3","away_source":"team:4","group_id":20,"pitch_number":2,"scheduled_start":"2026-08-26T09:00:00"},
    ]
    assert filter_matches(rows,mode="team",selected=3,source_team_id=_source_team_id)==[rows[1]]

def test_sort_is_stable_by_time_pitch_id():
    rows=[
        {"id":2,"scheduled_start":"2026-08-26T10:00:00","pitch_number":2},
        {"id":1,"scheduled_start":"2026-08-26T09:00:00","pitch_number":1},
    ]
    assert [r["id"] for r in sort_public_matches(rows)]==[1,2]

def test_optional_admin_textareas_are_conditional_and_preserve_saved_values():
    block=APP[APP.index("if edited_medical:"):APP.index('st.markdown("#### Poängregler och tabell")')]
    assert "if edited_medical:" in block
    assert "if edited_lost_found:" in block
    assert "if edited_accessibility_info:" in block
    assert 'edited_medical_info = _row_value(tournament, "medical_info", "") or ""' in block
    assert 'edited_lost_found_info = _row_value(tournament, "lost_found_info", "") or ""' in block
    assert 'edited_accessibility_text = _row_value(tournament, "accessibility_info", "") or ""' in block
