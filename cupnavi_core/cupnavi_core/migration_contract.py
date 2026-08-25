"""Release-time database contract checks."""
from __future__ import annotations

REQUIRED_TABLE_COLUMNS = {
    "pitches": {"tournament_id","pitch_number","name","address"},
    "app_errors": {"error_id","created_at","app_version","context","error_type"},
    "organizations": {"id","name","created_at"},
}

def validate_schema_contract(con):
    failures=[]
    for table, required in REQUIRED_TABLE_COLUMNS.items():
        cols={r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
        missing=required-cols
        if missing:
            failures.append(f"{table}: missing {','.join(sorted(missing))}")
    return failures
