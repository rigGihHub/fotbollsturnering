from __future__ import annotations
from pathlib import Path
import sys, os, json, urllib.request, urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from cupnavi_api.repository import public_snapshot
from cupnavi_core.public_competition import calculate_group_table, team_competition_summary

BASE=os.getenv("CUPNAVI_HTTP_BASE_URL","http://127.0.0.1:8001").rstrip("/")
CUP=os.getenv("CUPNAVI_PARITY_CUP","").strip()

def get_json(path):
    req=urllib.request.Request(BASE+path,headers={"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=10) as resp:
        if resp.status!=200:
            raise RuntimeError(f"HTTP {resp.status} for {path}")
        return json.loads(resp.read().decode("utf-8"))

def fail(message):
    print("FAIL:",message)
    return 3

def main():
    if not CUP:
        print("SKIP: CUPNAVI_PARITY_CUP is not set.")
        return 0

    direct=public_snapshot(CUP)
    if not direct:
        return fail(f"direct published cup not found: {CUP}")

    health=get_json("/health")
    if not health.get("ok"):
        return fail("API health is not OK")

    cup_payload=get_json(f"/api/public/cups/{CUP}")
    api_matches=cup_payload.get("matches",[])
    if direct["matches"]!=api_matches:
        return fail("published matches differ between direct repository and HTTP API")

    standings=get_json(f"/api/public/cups/{CUP}/standings")
    expected_groups=[]
    for group in direct["groups"]:
        gid=int(group["id"])
        teams=[t for t in direct["teams"] if int(t.get("group_id") or 0)==gid]
        matches=[m for m in direct["matches"] if int(m.get("group_id") or 0)==gid and m.get("stage")=="Gruppspel"]
        rows=calculate_group_table(
            teams,matches,
            points_win=int(direct["tournament"].get("points_win") or 0),
            points_draw=int(direct["tournament"].get("points_draw") or 0),
            points_loss=int(direct["tournament"].get("points_loss") or 0),
            table_tiebreak=str(direct["tournament"].get("table_tiebreak") or "Målskillnad först"),
        )
        expected_groups.append({"group":group,"rows":rows})
    if standings.get("groups")!=expected_groups:
        return fail("standings differ between direct calculation and HTTP API")

    playoffs=get_json(f"/api/public/cups/{CUP}/playoffs")
    if playoffs.get("brackets")!=direct["brackets"]:
        return fail("playoffs differ between direct repository and HTTP API")

    for team in direct["teams"]:
        team_id=int(team["id"])
        summary=get_json(f"/api/public/cups/{CUP}/teams/{team_id}/summary")
        if int(summary["team"]["id"])!=team_id:
            return fail(f"wrong team returned for {team_id}")

    print(json.dumps({
        "ok":True,
        "base_url":BASE,
        "cup":CUP,
        "checks":{
            "health":True,
            "matches":True,
            "standings":True,
            "playoffs":True,
            "team_summaries":True,
        },
    },ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
