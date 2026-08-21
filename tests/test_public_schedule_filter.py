from cupnavi_core.ui_logic import filter_group_rows, sort_schedule_rows

def test_group_filter_only_returns_selected_group():
    rows = [
        {"id": 1, "group_id": 10},
        {"id": 2, "group_id": 20},
        {"id": 3, "group_id": 10},
    ]
    assert [row["id"] for row in filter_group_rows(rows, 10)] == [1, 3]

def test_schedule_sort_is_date_time_then_pitch():
    rows = [
        {"id": 3, "scheduled_start": "2026-08-22T10:00:00", "pitch_number": 2},
        {"id": 2, "scheduled_start": "2026-08-22T09:00:00", "pitch_number": 2},
        {"id": 1, "scheduled_start": "2026-08-22T09:00:00", "pitch_number": 1},
    ]
    assert [row["id"] for row in sort_schedule_rows(rows)] == [1, 2, 3]
