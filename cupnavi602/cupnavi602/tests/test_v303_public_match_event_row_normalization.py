from cupnavi_core.public_match_repository import fetch_public_match_events
from cupnavi_core.public_presentation_view import public_match_events_html


class _Cursor:
    def __init__(self, rows):
        self._rows = rows
    def fetchall(self):
        return self._rows


class _Con:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
    def execute(self, sql, params):
        self.calls.append((sql, params))
        return _Cursor(self.rows)


def _row_value(row, key, default=None):
    try:
        value = row[key]
    except (TypeError, KeyError, IndexError):
        value = default
    return default if value is None else value


def test_repository_normalizes_positional_libsql_event_rows_to_named_dicts():
    con = _Con([
        (11, "Anna", 0, 1, "Hemmalag", 1, 0),
        (11, "Bo", 1, 2, "Bortalag", 0, 1),
    ])
    grouped = fetch_public_match_events(con, [11])
    assert grouped[11][0] == {
        "match_id": 11,
        "player_name": "Anna",
        "is_protected": 0,
        "team_id": 1,
        "team_name": "Hemmalag",
        "goals": 1,
        "red_cards": 0,
    }
    assert grouped[11][1]["is_protected"] == 1


def test_normalized_cloud_rows_render_public_match_events_without_typeerror():
    con = _Con([(11, "Anna", 0, 1, "Hemmalag", 1, 0)])
    rows = fetch_public_match_events(con, [11])[11]
    rendered = public_match_events_html(
        11,
        match_row={"home_source": "TEAM:1", "away_source": "TEAM:2"},
        rows=rows,
        team_names={1: "Hemmalag", 2: "Bortalag"},
        all_rows=lambda *_: [],
        one_row=lambda *_: None,
        row_value=_row_value,
        resolve_source=lambda source: int(source.split(":")[-1]),
        tr=lambda text: text,
    )
    assert "Matchhändelser" in rendered
    assert "Anna" in rendered
    assert "⚽" in rendered
