from pathlib import Path
import sqlite3, os, sys

path=Path(os.environ.get("CUPNAVI_PARITY_FIXTURE","/tmp/cupnavi-parity.db"))
if path.exists(): path.unlink()
con=sqlite3.connect(path)
con.executescript("""
CREATE TABLE tournaments(
 id INTEGER PRIMARY KEY,name TEXT,public_slug TEXT,sport TEXT,start_date TEXT,end_date TEXT,
 organizer TEXT,arena_address TEXT,kiosk_available INTEGER,kiosk_information TEXT,public_information TEXT,
 organizer_phone TEXT,feedback_email TEXT,instagram_url TEXT,playoff_format TEXT,bronze_match INTEGER,
 points_win INTEGER,points_draw INTEGER,points_loss INTEGER,table_tiebreak TEXT,show_scorer_stats INTEGER,
 show_assist_stats INTEGER,show_card_stats INTEGER,show_fairness INTEGER,enable_team_checkin INTEGER,is_published INTEGER
);
CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,age_class TEXT);
CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,group_id INTEGER,age_class TEXT,primary_color TEXT,secondary_color TEXT);
CREATE TABLE matches(
 id INTEGER PRIMARY KEY,tournament_id INTEGER,stage TEXT,group_id INTEGER,bracket_id INTEGER,round_no INTEGER,
 match_no INTEGER,home_source TEXT,away_source TEXT,scheduled_start TEXT,pitch_number INTEGER,home_score INTEGER,
 away_score INTEGER,home_penalties INTEGER,away_penalties INTEGER,decided_winner_id INTEGER,schedule_published INTEGER
);
CREATE TABLE brackets(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,size INTEGER,bronze_match INTEGER);
CREATE TABLE venue_points(id INTEGER PRIMARY KEY,tournament_id INTEGER,kind TEXT,label TEXT,detail TEXT,url TEXT);
CREATE TABLE notifications(id INTEGER PRIMARY KEY,tournament_id INTEGER,team_id INTEGER,created_at TEXT,title TEXT,message TEXT);
""")
con.execute("""INSERT INTO tournaments VALUES(
 1,'Parity Cup','parity-cup','Fotboll','2026-08-24','2026-08-24','CupNavi','Arena 1',1,'Kiosk öppen',
 'Välkommen','0700000000','cup@example.com','','A- och B-slutspel',0,3,1,0,'Målskillnad först',1,1,1,0,1,1)""")
con.executemany("INSERT INTO groups VALUES(?,?,?,?)",[(1,1,'Grupp A','P14'),(2,1,'Grupp B','P14')])
teams=[
 (1,1,'A1',1,'P14','#111111','#ffffff'),(2,1,'A2',1,'P14','#222222','#ffffff'),
 (3,1,'B1',2,'P14','#333333','#ffffff'),(4,1,'B2',2,'P14','#444444','#ffffff'),
]
con.executemany("INSERT INTO teams VALUES(?,?,?,?,?,?,?)",teams)
matches=[
 (1,1,'Gruppspel',1,None,1,1,'team:1','team:2','2026-08-24T09:00:00',1,2,1,None,None,None,1),
 (2,1,'Gruppspel',2,None,1,1,'team:3','team:4','2026-08-24T09:30:00',2,0,0,None,None,None,1),
 (3,1,'Semifinal',None,1,1,1,'team:1','team:4','2026-08-24T12:00:00',1,None,None,None,None,None,1),
 (4,1,'Semifinal',None,1,1,2,'team:3','team:2','2026-08-24T12:00:00',2,None,None,None,None,None,1),
]
con.executemany("INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",matches)
con.execute("INSERT INTO brackets VALUES(1,1,'A-slutspel',4,0)")
con.execute("INSERT INTO venue_points VALUES(1,1,'Plan','Plan 1','Huvudplan','https://example.com')")
con.commit(); con.close()
print(path)
