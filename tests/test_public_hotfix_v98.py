from pathlib import Path

from cupnavi_core.experience import playoff_preview


def test_playoff_preview_accepts_calculate_table_tuple_rows():
    tables = {
        "Grupp A": [
            (11, {"Lag": "ÖSK", "P": 6}),
            (12, {"Lag": "AIK", "P": 3}),
        ]
    }
    lines = playoff_preview(tables, "A-slutspel")
    assert lines == ["1:a Grupp A: ÖSK", "2:a Grupp A: AIK"]


def test_playoff_preview_still_accepts_plain_mapping_rows():
    tables = {"Grupp B": [{"Lag": "Sirius"}, {"Lag": "Hammarby"}]}
    lines = playoff_preview(tables, "A-slutspel")
    assert lines == ["1:a Grupp B: Sirius", "2:a Grupp B: Hammarby"]


def test_min_cup_has_all_teams_option_and_can_clear_team_query():
    app = Path("app.py").read_text(encoding="utf-8")
    view = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
    assert '"Alla lag": "All teams"' in app
    assert 'format_func=lambda team_id: tr("Alla lag") if team_id == all_teams_value' in view
    assert "if favorite_team_id is None and requested_team_id is not None:" in view
    assert 'del st.query_params["team"]' in view
    assert 'tr("Visa alla lag")' in view
