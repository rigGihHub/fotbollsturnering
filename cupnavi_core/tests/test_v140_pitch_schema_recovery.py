import sqlite3
from cupnavi_core.migrations import ensure_v19_schema_compat

def test_v19_repairs_existing_pitches_table_missing_address():
    con=sqlite3.connect(":memory:")
    con.execute("CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT,PRIMARY KEY(tournament_id,pitch_number))")
    con.execute("CREATE TABLE schedule_rules(tournament_id INTEGER PRIMARY KEY)")
    con.execute("""CREATE TABLE team_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,
        sender_type TEXT NOT NULL,sender_team_id INTEGER,recipient_type TEXT NOT NULL,
        recipient_team_id INTEGER,created_at TEXT NOT NULL,subject TEXT NOT NULL,
        message TEXT NOT NULL,read_at TEXT)""")
    ensure_v19_schema_compat(con)
    pitch_cols={r[1] for r in con.execute("PRAGMA table_info(pitches)")}
    assert "address" in pitch_cols

def test_app_pitch_definitions_has_runtime_schema_recovery():
    from pathlib import Path
    text=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
    block=text[text.index("def pitch_definitions"):text.index("def ensure_pitch_definitions")]
    assert "ensure_v19_schema_compat(con)" in block
    assert "_clear_render_query_cache()" in block

def test_bootstrap_repairs_v19_even_if_migration_marker_already_exists():
    from pathlib import Path
    text=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
    assert "ensure_v19_schema_compat(con)" in text
