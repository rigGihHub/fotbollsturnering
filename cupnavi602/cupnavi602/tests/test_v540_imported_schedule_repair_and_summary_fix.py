import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_schedule_ui_surfaces_locked_error_repair_path():
    source = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
    assert "Reparera och bygg om schemat" in source
    assert "_repairing_locked_schedule" in source
    assert "replace_locked=_repairing_locked_schedule" in source
    assert "foto/PDF-import" in source


def test_repository_unlocks_only_unplayed_matches_atomically_on_explicit_rebuild():
    from cupnavi_core.schedule_repository import ScheduleRepository

    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY, is_published INTEGER, schedule_dirty INTEGER);
        CREATE TABLE matches(
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER,
            scheduled_start TEXT,
            pitch_number INTEGER,
            referee_id INTEGER,
            schedule_locked INTEGER DEFAULT 0,
            schedule_published INTEGER DEFAULT 0,
            home_score INTEGER,
            away_score INTEGER
        );
        INSERT INTO tournaments VALUES(1,1,1);
        INSERT INTO matches VALUES(10,1,'2026-09-08T09:00',1,3,1,1,NULL,NULL);
        INSERT INTO matches VALUES(11,1,'2026-09-08T10:00',1,3,1,1,2,1);
        """
    )

    class _Ctx:
        def __enter__(self): return con
        def __exit__(self, exc_type, exc, tb): return False

    repo = ScheduleRepository(lambda *_: [], lambda: _Ctx())
    repo.persist_generated_schedule(
        tournament_id=1,
        schedule_updates=[("2026-09-08T11:00", 2, None, 10)],
        unresolved=0,
        preserve_existing=False,
        replace_locked=True,
    )

    unplayed = con.execute("SELECT * FROM matches WHERE id=10").fetchone()
    played = con.execute("SELECT * FROM matches WHERE id=11").fetchone()
    assert unplayed["schedule_locked"] == 0
    assert unplayed["scheduled_start"] == "2026-09-08T11:00"
    assert unplayed["pitch_number"] == 2
    assert unplayed["schedule_published"] == 0
    # Played result is never unlocked/reset by the repair transaction.
    assert played["schedule_locked"] == 1
    assert played["scheduled_start"] == "2026-09-08T10:00"


def test_public_summary_is_single_continuous_html_block():
    from cupnavi_core.public_match_overview import build_summary_html

    rendered = build_summary_html(
        team_count=8,
        played_count=14,
        total_matches=16,
        total_score=65,
        score_label="mål",
        tr=lambda value: {"av": "av"}.get(value, value),
        highlights_html="",
    )
    assert "\n" not in rendered
    assert rendered.startswith("<div class='cn-public-summary-row'>")
    assert rendered.endswith("</div>")
    assert rendered.count("<div") == rendered.count("</div>")
