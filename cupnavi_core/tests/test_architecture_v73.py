from pathlib import Path


def test_schedule_repository_is_used_by_app():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "from cupnavi_core.schedule_repository import ScheduleRepository" in text
    assert "def schedule_repository():" in text
    assert "repo.group_generation_data(tournament_id)" in text
    assert "repo.scheduling_inputs(tournament_id)" in text
    assert "repo.persist_generated_schedule(" in text


def test_schedule_domain_is_used_by_app():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "build_schedule_window(tournament, rules)" in text
    assert "schedule_source_team_id(source)" in text


def test_generate_schedule_no_longer_contains_raw_schedule_persistence_sql():
    text = Path("app.py").read_text(encoding="utf-8")
    start = text.index("def generate_schedule(")
    end = text.index("def validate_schedule(", start)
    block = text[start:end]
    assert "UPDATE matches SET scheduled_start" not in block
    assert "SELECT * FROM matches WHERE tournament_id" not in block
