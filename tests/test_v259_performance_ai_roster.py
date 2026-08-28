import json
from pathlib import Path

from cupnavi_core.ai_roster_import import (
    ALLOWED_POSITIONS,
    extract_roster_from_image,
    normalize_extracted_players,
)

APP = Path(__file__).resolve().parents[1] / "app.py"
SOURCE = APP.read_text(encoding="utf-8")


def test_ai_roster_normalization_deduplicates_without_inventing_values():
    rows = normalize_extracted_players([
        {"name": "  Ada   Andersson ", "player_number": 7, "birth_year": 2013, "position": "forward"},
        {"name": "ada andersson", "player_number": 8, "birth_year": 2014, "position": "Målvakt"},
        {"name": "Bo Berg", "player_number": "bad", "birth_year": None, "position": ""},
        {"name": "", "player_number": 3, "birth_year": 2012, "position": "back"},
    ])
    assert rows == [
        {"name": "Ada Andersson", "player_number": 7, "birth_year": 2013, "position": "Anfallare"},
        {"name": "Bo Berg", "player_number": None, "birth_year": None, "position": "Ej angiven"},
    ]


def test_ai_roster_request_uses_image_input_and_structured_schema():
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            payload = {
                "output": [{
                    "type": "message",
                    "content": [{
                        "type": "output_text",
                        "text": json.dumps({"players": [{
                            "name": "Kim Karlsson",
                            "player_number": 11,
                            "birth_year": None,
                            "position": "Mittfältare",
                        }]})
                    }],
                }]
            }
            return json.dumps(payload).encode("utf-8")

    def fake_opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    rows = extract_roster_from_image(
        b"not-a-real-image-but-valid-for-request-test",
        "image/png",
        "secret-key",
        model="gpt-5.6-luna",
        opener=fake_opener,
    )
    assert rows[0]["name"] == "Kim Karlsson"
    assert captured["url"].endswith("/v1/responses")
    assert captured["body"]["store"] is False
    content = captured["body"]["input"][0]["content"]
    assert any(item["type"] == "input_image" for item in content)
    assert captured["body"]["text"]["format"]["type"] == "json_schema"
    position_schema = captured["body"]["text"]["format"]["schema"]["properties"]["players"]["items"]["properties"]["position"]
    assert position_schema["enum"] == ALLOWED_POSITIONS


def test_roster_page_loads_match_rosters_lazily_and_filters_in_sql():
    start = SOURCE.index('if admin_page == "Trupper":')
    end = SOURCE.index('\n\nif admin_page == "Domare":', start)
    block = SOURCE[start:end]
    assert 'st.toggle(\n            "Visa matchtrupper – admin"' in block
    assert 'AND (home_source=? OR away_source=?)' in block
    assert 'if team_id in _match_team_ids(row)' not in block


def test_expensive_secondary_tools_are_lazy():
    assert '_show_change_impact = st.toggle("Kontrollera konsekvens före större ändring"' in SOURCE
    assert '_show_deep_controls = st.toggle("Fördjupad kontroll"' in SOURCE
    assert '_show_technical_health = st.toggle("Teknisk hälsa och backup"' in SOURCE


def test_global_search_uses_one_union_query():
    start = SOURCE.index('if len(global_query) >= 2:')
    end = SOURCE.index('\n\n\nadmin_page = st.session_state[admin_page_key]', start)
    block = SOURCE[start:end]
    assert 'WITH\n               team_hits AS' in block
    assert 'UNION ALL SELECT * FROM player_hits' in block
    assert block.count('all_rows(') == 1


def test_ai_import_is_review_before_write_and_batches_insert():
    start = SOURCE.index('with st.expander("✨ AI-import från foto eller skärmdump"')
    end = SOURCE.index('_focus_kind = st.session_state.get', start)
    block = SOURCE[start:end]
    assert 'st.data_editor(' in block
    assert 'already' not in block.lower()  # Swedish UI; no hidden implicit auto-write copy.
    assert 'run_many(' in block
    assert 'INSERT INTO players' in block
    assert 'Läs av med AI' in block
