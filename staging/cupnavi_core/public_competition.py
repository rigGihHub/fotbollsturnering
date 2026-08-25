"""Pure public competition calculations shared by Streamlit and the public API."""
from __future__ import annotations
from datetime import datetime

def source_team_id(source):
    text=str(source or "")
    if not text.startswith("team:"):
        return None
    try:
        return int(text.split(":",1)[1])
    except (TypeError,ValueError):
        return None

def calculate_group_table(teams, matches, *, points_win=3, points_draw=1, points_loss=0,
                          table_tiebreak="Målskillnad först"):
    """Return ordered rows with CupNavi's existing table/tiebreak semantics."""
    stats={
        int(t["id"]):{"Lag":t["name"],"S":0,"V":0,"O":0,"F":0,"GM":0,"IM":0,"MS":0,"P":0}
        for t in teams
    }
    completed=[]
    for m in matches:
        if m.get("home_score") is None or m.get("away_score") is None:
            continue
        h=source_team_id(m.get("home_source")); a=source_team_id(m.get("away_source"))
        if h not in stats or a not in stats:
            continue
        hs,aas=int(m["home_score"]),int(m["away_score"])
        completed.append((h,a,hs,aas))
        stats[h]["S"]+=1; stats[a]["S"]+=1
        stats[h]["GM"]+=hs; stats[h]["IM"]+=aas
        stats[a]["GM"]+=aas; stats[a]["IM"]+=hs
        if hs>aas:
            stats[h]["V"]+=1; stats[a]["F"]+=1
            stats[h]["P"]+=int(points_win); stats[a]["P"]+=int(points_loss)
        elif hs<aas:
            stats[a]["V"]+=1; stats[h]["F"]+=1
            stats[a]["P"]+=int(points_win); stats[h]["P"]+=int(points_loss)
        else:
            stats[h]["O"]+=1; stats[a]["O"]+=1
            stats[h]["P"]+=int(points_draw); stats[a]["P"]+=int(points_draw)
    for row in stats.values():
        row["MS"]=row["GM"]-row["IM"]

    point_groups={}
    for team_id,data in stats.items():
        point_groups.setdefault(data["P"],[]).append(team_id)

    ordered=[]
    for points in sorted(point_groups,reverse=True):
        tied=list(point_groups[points])
        if len(tied)>1 and table_tiebreak=="Inbördes möten först":
            h2h={tid:{"P":0,"MS":0,"GM":0} for tid in tied}
            tied_set=set(tied)
            for h,a,hs,aas in completed:
                if h not in tied_set or a not in tied_set:
                    continue
                h2h[h]["GM"]+=hs; h2h[h]["MS"]+=hs-aas
                h2h[a]["GM"]+=aas; h2h[a]["MS"]+=aas-hs
                if hs>aas:
                    h2h[h]["P"]+=int(points_win); h2h[a]["P"]+=int(points_loss)
                elif hs<aas:
                    h2h[a]["P"]+=int(points_win); h2h[h]["P"]+=int(points_loss)
                else:
                    h2h[h]["P"]+=int(points_draw); h2h[a]["P"]+=int(points_draw)
            tied.sort(key=lambda tid:(
                -h2h[tid]["P"],-h2h[tid]["MS"],-h2h[tid]["GM"],
                -stats[tid]["MS"],-stats[tid]["GM"],stats[tid]["Lag"].lower()
            ))
        else:
            tied.sort(key=lambda tid:(-stats[tid]["MS"],-stats[tid]["GM"],stats[tid]["Lag"].lower()))
        ordered.extend(tied)
    return [{"position":i,"team_id":tid,**stats[tid]} for i,tid in enumerate(ordered,1)]

def team_competition_summary(team_id, matches, standings_by_group, team_group_id=None, now=None):
    now=now or datetime.now()
    team_id=int(team_id)
    relevant=[
        m for m in matches
        if team_id in (source_team_id(m.get("home_source")),source_team_id(m.get("away_source")))
    ]
    def dt(m):
        try:
            return datetime.fromisoformat(str(m.get("scheduled_start")))
        except (TypeError,ValueError):
            return None
    relevant.sort(key=lambda m:(dt(m) is None,dt(m) or datetime.max))
    next_match=next((m for m in relevant if m.get("home_score") is None and m.get("away_score") is None and dt(m) and dt(m)>=now),None)
    latest=next((m for m in reversed(relevant) if m.get("home_score") is not None and m.get("away_score") is not None),None)
    position=None
    if team_group_id is not None:
        for row in standings_by_group.get(int(team_group_id),[]):
            if int(row["team_id"])==team_id:
                position=int(row["position"]); break
    playoff=next((m for m in relevant if m.get("stage")!="Gruppspel" and m.get("home_score") is None and m.get("away_score") is None),None)
    return {
        "team_id":team_id,
        "matches":len(relevant),
        "played":sum(1 for m in relevant if m.get("home_score") is not None and m.get("away_score") is not None),
        "next_match":next_match,
        "latest_result":latest,
        "group_position":position,
        "next_playoff_match":playoff,
    }
