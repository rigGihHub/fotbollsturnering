"""Review-first match pairing builder for matchcamps."""
from __future__ import annotations

import hashlib
import json

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one


def _source(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    tournament = one("SELECT arrangement_type FROM tournaments WHERE id=?", (int(tournament_id),))
    if not tournament:
        return None
    if str(tournament.get("arrangement_type") or "tournament") != "matchcamp":
        raise ValueError("Matchbyggaren kan bara användas för arrangemangstypen Matchcamp")
    teams = all_rows("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name,id", (int(tournament_id),))
    existing = one("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=?", (int(tournament_id),)) or {}
    return teams, int(existing.get("n") or 0)


def _fingerprint(teams: list[dict], matches_per_team: int) -> str:
    raw = json.dumps({"teams":[[int(t["id"]),str(t["name"])] for t in teams],"target":matches_per_team}, ensure_ascii=False, separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _round_robin(teams: list[dict]) -> list[list[tuple[dict,dict]]]:
    rotating = list(teams)
    if len(rotating) % 2:
        rotating.append({"id":None,"name":"VILA"})
    rounds=[]
    for _ in range(len(rotating)-1):
        pairs=[]
        for index in range(len(rotating)//2):
            left,right=rotating[index],rotating[-1-index]
            if left["id"] is not None and right["id"] is not None:
                pairs.append((left,right))
        rounds.append(pairs)
        rotating=[rotating[0],rotating[-1],*rotating[1:-1]]
    return rounds


def matchcamp_pairing_proposal(account_id: int, tournament_id: int, matches_per_team: int):
    source=_source(account_id,tournament_id)
    if source is None:return None
    teams,existing_count=source
    if existing_count:
        raise ValueError("Cupen innehåller redan matcher. Matchbyggaren skriver aldrig över ett befintligt matchprogram")
    if len(teams)<2:raise ValueError("Minst två lag krävs för att skapa matcher")
    target=int(matches_per_team)
    if target<1 or target>min(12,len(teams)-1):
        raise ValueError(f"Matcher per lag måste vara mellan 1 och {min(12,len(teams)-1)}")
    rounds=_round_robin(teams)
    chosen=[pair for round_pairs in rounds[:target] for pair in round_pairs]
    counts={int(team["id"]):0 for team in teams}
    pairs=[]
    for number,(home,away) in enumerate(chosen,1):
        counts[int(home["id"])]+=1;counts[int(away["id"])]+=1
        pairs.append({"match_no":number,"home_team_id":int(home["id"]),"home_name":str(home["name"]),"away_team_id":int(away["id"]),"away_name":str(away["name"])})
    values=list(counts.values())
    return {"writes_database":False,"fingerprint":_fingerprint(teams,target),"matches_per_team":target,"team_count":len(teams),"match_count":len(pairs),"minimum_matches":min(values),"maximum_matches":max(values),"balanced":min(values)==max(values),"pairs":pairs}


def apply_matchcamp_pairing(account_id: int, tournament_id: int, matches_per_team: int, fingerprint: str):
    proposal=matchcamp_pairing_proposal(account_id,tournament_id,matches_per_team)
    if proposal is None:return None
    if proposal["fingerprint"]!=str(fingerprint):raise ValueError("Förslaget är inaktuellt eftersom lagen har ändrats. Skapa ett nytt förslag")
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        existing=con.execute("SELECT COUNT(*) FROM matches WHERE tournament_id=?",(int(tournament_id),)).fetchone()[0]
        if int(existing):
            con.rollback();raise ValueError("Matcher har lagts till sedan förslaget skapades. Ingenting sparades")
        con.executemany("""INSERT INTO matches(tournament_id,stage,round_no,match_no,home_source,away_source,schedule_published,schedule_locked)
                           VALUES(?,'Matchcamp',1,?,?,?,0,0)""",[(int(tournament_id),p["match_no"],f"team:{p['home_team_id']}",f"team:{p['away_team_id']}") for p in proposal["pairs"]])
        con.execute("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",(int(tournament_id),))
        con.commit()
    return {"created":True,"created_count":proposal["match_count"]}
