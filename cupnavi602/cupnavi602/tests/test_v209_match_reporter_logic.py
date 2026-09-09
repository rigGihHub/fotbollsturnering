
from cupnavi_core.match_reporter_logic import build_bulk_result_rows, select_playable_matches


def test_playable_matches_require_both_resolved_teams():
    rows=[
        {"id":1,"home_source":"team:1","away_source":"team:2"},
        {"id":2,"home_source":"winner:10","away_source":"team:2"},
        {"id":3,"home_source":"team:1","away_source":"loser:11"},
    ]
    resolved={"team:1":1,"team:2":2,"winner:10":None,"loser:11":None}
    result=select_playable_matches(rows,resolve_source=lambda source:resolved.get(source))
    assert [row["id"] for row in result]==[1]


def test_bulk_result_projection_preserves_group_vs_playoff_fields():
    matches=[
        {
            "id":1,"scheduled_start":"2026-08-27T10:00:00","pitch_number":1,
            "stage":"Gruppspel","home_source":"team:1","away_source":"team:2",
            "home_score":2,"away_score":1,"home_penalties":4,"away_penalties":3,
            "decided_winner_id":1,
        },
        {
            "id":2,"scheduled_start":"2026-08-27T12:00:00","pitch_number":2,
            "stage":"Final","home_source":"team:1","away_source":"team:2",
            "home_score":1,"away_score":1,"home_penalties":5,"away_penalties":4,
            "decided_winner_id":1,
        },
    ]
    result=build_bulk_result_rows(
        matches,
        source_label=lambda source:{"team:1":"AIK","team:2":"ÖSK"}[source],
        swedish_datetime=lambda value:value,
        team_name_by_id={1:"AIK",2:"ÖSK"},
    )
    assert result[0]["Hemmastraffar"] is None
    assert result[0]["Avgörande vinnare"]=="–"
    assert result[1]["Hemmastraffar"]==5
    assert result[1]["Bortastraffar"]==4
    assert result[1]["Avgörande vinnare"]=="AIK"
