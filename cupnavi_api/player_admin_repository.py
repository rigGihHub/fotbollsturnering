"""Organizer-scoped player/roster administration for the Next admin."""
from __future__ import annotations

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one


def admin_rosters(account_id:int,tournament_id:int):
    if not _has_tournament_access(account_id,tournament_id):
        return None
    teams=all_rows(
        "SELECT id,name,age_class FROM teams WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )
    players=all_rows(
        """SELECT p.id,p.team_id,p.name,p.player_number
           FROM players p JOIN teams t ON t.id=p.team_id
           WHERE t.tournament_id=?
           ORDER BY t.name,CASE WHEN p.player_number IS NULL THEN 1 ELSE 0 END,p.player_number,p.name,p.id""",
        (int(tournament_id),),
    )
    by_team={int(team['id']):[] for team in teams}
    for player in players:
        by_team.setdefault(int(player['team_id']),[]).append(player)
    return {'teams':[{**team,'players':by_team.get(int(team['id']),[])} for team in teams]}


def _team_in_cup(tournament_id:int,team_id:int):
    return one("SELECT id,name FROM teams WHERE id=? AND tournament_id=?",(int(team_id),int(tournament_id)))


def create_player(account_id:int,tournament_id:int,team_id:int,values:dict):
    if not _has_tournament_access(account_id,tournament_id):
        return None
    if not _team_in_cup(tournament_id,team_id):
        return None
    name=str(values.get('name') or '').strip()
    if not name:
        raise ValueError('Spelarnamn krävs')
    raw_number=values.get('player_number')
    number=None if raw_number in (None,'') else int(raw_number)
    if number is not None and (number<0 or number>999):
        raise ValueError('Tröjnummer måste vara mellan 0 och 999')
    with connect() as con:
        cur=con.execute("INSERT INTO players(team_id,name,player_number) VALUES(?,?,?)",(int(team_id),name,number))
        player_id=int(cur.lastrowid)
        commit=getattr(con,'commit',None)
        if callable(commit): commit()
    return one("SELECT id,team_id,name,player_number FROM players WHERE id=?",(player_id,))


def update_player(account_id:int,tournament_id:int,team_id:int,player_id:int,values:dict):
    if not _has_tournament_access(account_id,tournament_id):
        return None
    if not _team_in_cup(tournament_id,team_id):
        return None
    current=one("SELECT id,team_id,name,player_number FROM players WHERE id=? AND team_id=?",(int(player_id),int(team_id)))
    if not current:return None
    name=str(values.get('name',current.get('name')) or '').strip()
    if not name:raise ValueError('Spelarnamn krävs')
    raw_number=values.get('player_number',current.get('player_number'))
    number=None if raw_number in (None,'') else int(raw_number)
    if number is not None and (number<0 or number>999):raise ValueError('Tröjnummer måste vara mellan 0 och 999')
    with connect() as con:
        con.execute("UPDATE players SET name=?,player_number=? WHERE id=? AND team_id=?",(name,number,int(player_id),int(team_id)))
        commit=getattr(con,'commit',None)
        if callable(commit): commit()
    return one("SELECT id,team_id,name,player_number FROM players WHERE id=?",(int(player_id),))


def delete_player(account_id:int,tournament_id:int,team_id:int,player_id:int):
    if not _has_tournament_access(account_id,tournament_id):return None
    if not _team_in_cup(tournament_id,team_id):return None
    current=one("SELECT id,team_id,name,player_number FROM players WHERE id=? AND team_id=?",(int(player_id),int(team_id)))
    if not current:return None
    used=one("SELECT COUNT(*) AS n FROM player_match_stats WHERE player_id=?",(int(player_id),))
    if used and int(used.get('n') or 0)>0:
        raise ValueError('Spelaren har registrerade matchhändelser och kan inte tas bort. Behåll spelaren för historiken.')
    with connect() as con:
        con.execute("DELETE FROM players WHERE id=? AND team_id=?",(int(player_id),int(team_id)))
        commit=getattr(con,'commit',None)
        if callable(commit): commit()
    return current
