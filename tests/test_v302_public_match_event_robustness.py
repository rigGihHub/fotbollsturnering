from cupnavi_core.public_presentation_view import public_match_events_html


def test_public_events_tolerate_null_names_from_persisted_rows():
    rendered = public_match_events_html(
        1,
        match_row={"home_source": "TEAM:1", "away_source": "TEAM:2"},
        rows=[{"player_name": None, "is_protected": 0, "team_id": 1, "team_name": None, "goals": 1, "red_cards": 0}],
        team_names={1: None, 2: None},
        all_rows=lambda *_: [], one_row=lambda *_: None,
        row_value=lambda row, key, default=None: row.get(key, default),
        resolve_source=lambda source: int(source.split(":")[-1]), tr=lambda text: text,
    )
    assert "Matchhändelser" in rendered
    assert "⚽" in rendered
