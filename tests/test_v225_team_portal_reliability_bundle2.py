
import ast
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP_PATH=ROOT/"app.py"


class LocalDbFactory:
    def __init__(self,path): self.path=path
    def __call__(self):
        con=sqlite3.connect(self.path)
        con.row_factory=sqlite3.Row
        return con


def _row_value(row,key,default=None):
    try: value=row[key]
    except Exception: value=default
    return default if value is None and default is not None else value


def _team_value(row,key,default=None):
    return _row_value(row,key,default)


def _load(path,email_counter=None):
    source=APP_PATH.read_text(encoding="utf-8")
    tree=ast.parse(source)
    names={
        "_team_checkin_snapshot",
        "_set_team_checkin_if_unchanged",
        "_team_kit_snapshot",
        "_confirm_team_kit_if_unchanged",
        "_send_team_message",
    }
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==names
    module=ast.Module(body=nodes,type_ignores=[])
    ast.fix_missing_locations(module)

    def one_row(sql,params=()):
        con=sqlite3.connect(path); con.row_factory=sqlite3.Row
        row=con.execute(sql,params).fetchone(); con.close()
        return row

    def run(sql,params=()):
        con=sqlite3.connect(path); con.row_factory=sqlite3.Row
        cur=con.execute(sql,params); con.commit()
        rid=cur.lastrowid
        con.close()
        return rid

    counter=email_counter if email_counter is not None else {"n":0}
    def send_notification_email(*args,**kwargs):
        counter["n"] += 1
        return True,None

    ns={
        "sqlite3":sqlite3,
        "db":LocalDbFactory(path),
        "_row_value":_row_value,
        "_team_value":_team_value,
        "_clear_render_query_cache":lambda:None,
        "datetime":__import__("datetime").datetime,
        "one_row":one_row,
        "run":run,
        "send_notification_email":send_notification_email,
    }
    exec(compile(module,str(APP_PATH),"exec"),ns)
    return ns


def _create(path):
    con=sqlite3.connect(path)
    con.execute("""CREATE TABLE teams(
        id INTEGER PRIMARY KEY,tournament_id INTEGER NOT NULL,name TEXT,
        checked_in INTEGER DEFAULT 0,checked_in_at TEXT,checked_in_by TEXT,
        kit_confirmed_at TEXT,primary_color TEXT,secondary_color TEXT,
        home_pattern TEXT,home_color_2 TEXT,away_pattern TEXT,away_color_2 TEXT,
        responsible_name TEXT,responsible_email TEXT
    )""")
    con.execute("""CREATE TABLE team_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,
        sender_type TEXT NOT NULL,sender_team_id INTEGER,recipient_type TEXT NOT NULL,
        recipient_team_id INTEGER,created_at TEXT NOT NULL,subject TEXT NOT NULL,
        message TEXT NOT NULL,read_at TEXT,email_status TEXT,email_error TEXT,
        request_token TEXT
    )""")
    con.execute("CREATE UNIQUE INDEX idx_team_messages_request_token ON team_messages(tournament_id,request_token)")
    con.executemany(
        """INSERT INTO teams VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (10,7,"Lag A",0,None,None,None,"#111111","#eeeeee","Helfärgad","#ffffff","Helfärgad","#111827","Ada","a@example.com"),
            (11,7,"Lag B",0,None,None,None,"#222222","#dddddd","Helfärgad","#ffffff","Helfärgad","#111827","Bo","b@example.com"),
            (12,8,"Other Cup",0,None,None,None,"#333333","#cccccc","Helfärgad","#ffffff","Helfärgad","#111827","Cia","c@example.com"),
        ],
    )
    con.commit(); con.close()


def test_stale_checkin_transition_is_rejected(tmp_path):
    path=tmp_path/"checkin.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM teams WHERE id=10").fetchone(); con.close()
    snap=h["_team_checkin_snapshot"](row)

    assert h["_set_team_checkin_if_unchanged"](10,snap,checked_in=True,checked_in_by="A")== (True,None)
    assert h["_set_team_checkin_if_unchanged"](10,snap,checked_in=True,checked_in_by="B")== (False,"conflict")


def test_kit_confirmation_rejects_changed_kit(tmp_path):
    path=tmp_path/"kit.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM teams WHERE id=10").fetchone()
    snap=h["_team_kit_snapshot"](row)
    con.execute("UPDATE teams SET primary_color='#999999' WHERE id=10")
    con.commit(); con.close()

    assert h["_confirm_team_kit_if_unchanged"](10,snap)==(False,"conflict")


def test_message_request_token_is_idempotent_and_email_sent_once(tmp_path):
    path=tmp_path/"msg.sqlite"; _create(path)
    counter={"n":0}
    h=_load(path,counter)
    send=h["_send_team_message"]

    first=send(
        7,"team","Hej","Test",sender_team_id=10,
        recipient_type="team",recipient_team_id=11,request_token="token-1"
    )
    second=send(
        7,"team","Hej","Test",sender_team_id=10,
        recipient_type="team",recipient_team_id=11,request_token="token-1"
    )
    assert first==second
    assert counter["n"]==1

    con=sqlite3.connect(path)
    assert con.execute("SELECT COUNT(*) FROM team_messages").fetchone()[0]==1
    con.close()


def test_message_rejects_foreign_team_and_self_message(tmp_path):
    path=tmp_path/"ownership.sqlite"; _create(path)
    h=_load(path)
    send=h["_send_team_message"]

    try:
        send(7,"team","X","Y",sender_team_id=12,recipient_type="organizer",request_token="a")
    except ValueError as exc:
        assert "inte turneringen" in str(exc)
    else:
        raise AssertionError("foreign sender accepted")

    try:
        send(7,"team","X","Y",sender_team_id=10,recipient_type="team",recipient_team_id=10,request_token="b")
    except ValueError as exc:
        assert "sig självt" in str(exc)
    else:
        raise AssertionError("self-message accepted")


def test_request_token_cannot_be_reused_for_different_payload(tmp_path):
    path=tmp_path/"token_payload.sqlite"; _create(path)
    h=_load(path)
    send=h["_send_team_message"]

    send(7,"team","A","B",sender_team_id=10,recipient_type="team",recipient_team_id=11,request_token="same")
    try:
        send(7,"team","Changed","B",sender_team_id=10,recipient_type="team",recipient_team_id=11,request_token="same")
    except ValueError as exc:
        assert "inte längre giltig" in str(exc)
    else:
        raise AssertionError("token reuse with changed payload accepted")
