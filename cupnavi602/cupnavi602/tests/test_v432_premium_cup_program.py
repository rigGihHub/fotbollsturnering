from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from cupnavi_core.pdf_export import build_cup_program_pdf


def _sample_program():
    tournament = {
        "name": "Slottkampen",
        "location": "Örebro",
        "start_date": "2026-10-24",
        "end_date": "2026-10-24",
        "table_tiebreak": "Målskillnad först",
        "playoff_tie_rule": "Straffar direkt",
        "public_information": "Samling 30 minuter före första match.",
    }
    teams = [
        {"id": 1, "name": "Örebro SK", "group_id": 10, "primary_color": "#111111"},
        {"id": 2, "name": "Hammarby", "group_id": 10, "primary_color": "#138A45"},
        {"id": 3, "name": "AIK", "group_id": 11, "primary_color": "#E7C233"},
        {"id": 4, "name": "Karlstad", "group_id": 11, "primary_color": "#B91C1C"},
    ]
    groups = [{"id": 10, "name": "Grupp A"}, {"id": 11, "name": "Grupp B"}]
    matches = [
        {"id": 1, "group_id": 10, "stage": "Gruppspel", "scheduled_start": "2026-10-24T08:30", "pitch_number": 1,
         "home_source": "team:1", "away_source": "team:2", "home_score": None, "away_score": None,
         "home_penalties": None, "away_penalties": None, "referee_id": None},
        {"id": 2, "group_id": 11, "stage": "Gruppspel", "scheduled_start": "2026-10-24T09:10", "pitch_number": 1,
         "home_source": "team:3", "away_source": "team:4", "home_score": None, "away_score": None,
         "home_penalties": None, "away_penalties": None, "referee_id": None},
        {"id": 3, "group_id": None, "stage": "Semifinal 1", "scheduled_start": "2026-10-24T17:15", "pitch_number": 1,
         "home_source": "1:a grupp A", "away_source": "2:a grupp B", "home_score": None, "away_score": None,
         "home_penalties": None, "away_penalties": None, "referee_id": None},
        {"id": 4, "group_id": None, "stage": "Semifinal 2", "scheduled_start": "2026-10-24T17:15", "pitch_number": 2,
         "home_source": "1:a grupp B", "away_source": "2:a grupp A", "home_score": None, "away_score": None,
         "home_penalties": None, "away_penalties": None, "referee_id": None},
        {"id": 5, "group_id": None, "stage": "Final", "scheduled_start": "2026-10-24T19:05", "pitch_number": 1,
         "home_source": "Vinnare semi 1", "away_source": "Vinnare semi 2", "home_score": None, "away_score": None,
         "home_penalties": None, "away_penalties": None, "referee_id": None},
    ]
    labels = {
        "team:1": "Örebro SK", "team:2": "Hammarby", "team:3": "AIK", "team:4": "Karlstad",
        "1:a grupp A": "1:a grupp A", "2:a grupp B": "2:a grupp B", "1:a grupp B": "1:a grupp B",
        "2:a grupp A": "2:a grupp A", "Vinnare semi 1": "Vinnare semi 1", "Vinnare semi 2": "Vinnare semi 2",
    }
    ids = {"team:1": 1, "team:2": 2, "team:3": 3, "team:4": 4}
    rules = {"halves": 1, "minutes_per_half": 35, "minimum_team_rest_minutes": 45, "synchronized_pitch_times": 0,
             "consider_pitch_travel": 1, "pitch_travel_buffer_minutes": 10}
    pitches = [{"pitch_number": 1, "name": "Sörbyvallen", "address": "Örebro"}, {"pitch_number": 2, "name": "Ekäng", "address": "Örebro"}]
    return build_cup_program_pdf(tournament, matches, teams, groups, [], labels, ids, rules=rules, pitches=pitches)


def test_premium_cup_program_is_valid_and_contains_program_sections():
    data = _sample_program()
    assert data.startswith(b"%PDF")
    reader = PdfReader(BytesIO(data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "OFFICIELLT CUPPROGRAM" in text
    assert "GRUPPER" in text
    assert "GRUPPSPEL" in text
    assert "SLUTSPEL" in text
    assert "VÄGEN TILL FINALEN" in text
    assert "TABELLER" in text
    assert "ATT TÄNKA PÅ" in text
    assert "Sörbyvallen" in text


def test_schedule_ui_exposes_premium_program_as_primary_export():
    source = Path("cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")
    assert '"Skapa professionellt cupprogram"' in source
    assert '"Ladda ner cupprogram som PDF"' in source
    assert 'type="primary"' in source
    assert "build_cup_program_pdf" in source
