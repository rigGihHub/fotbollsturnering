from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sqlite3, sys
from cupnavi_core.migrations import ensure_v19_schema_compat, ensure_v20_schema_compat
from cupnavi_core.migration_contract import validate_schema_contract
con=sqlite3.connect(":memory:")
con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY)")
con.execute("CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT,PRIMARY KEY(tournament_id,pitch_number))")
con.execute("CREATE TABLE schedule_rules(tournament_id INTEGER PRIMARY KEY)")
con.execute("""CREATE TABLE team_messages(id INTEGER PRIMARY KEY,tournament_id INTEGER,sender_type TEXT,
 sender_team_id INTEGER,recipient_type TEXT,recipient_team_id INTEGER,created_at TEXT,subject TEXT,message TEXT,read_at TEXT)""")
ensure_v19_schema_compat(con); ensure_v20_schema_compat(con)
failures=validate_schema_contract(con)
if failures:
    print("\n".join(failures)); sys.exit(1)
print("schema contract: OK")
