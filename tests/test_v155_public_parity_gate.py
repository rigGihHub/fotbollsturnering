from pathlib import Path
from cupnavi_core.public_parity import compare_public_payloads

ROOT=Path(__file__).resolve().parents[1]

def sample():
    tournament={"points_win":3,"points_draw":1,"points_loss":0,"table_tiebreak":"Målskillnad först"}
    teams=[{"id":1,"name":"A","group_id":1},{"id":2,"name":"B","group_id":1}]
    groups=[{"id":1,"name":"G"}]
    matches=[{"id":1,"stage":"Gruppspel","group_id":1,"bracket_id":None,"home_source":"team:1","away_source":"team:2",
              "scheduled_start":"2026-08-24T10:00:00","pitch_number":1,"home_score":2,"away_score":1,
              "home_penalties":None,"away_penalties":None}]
    return tournament,teams,groups,matches

def test_parity_passes_for_identical_public_payloads():
    t,teams,groups,matches=sample()
    r=compare_public_payloads(tournament=t,teams=teams,groups=groups,
        legacy_matches=matches,api_matches=[dict(x) for x in matches],legacy_brackets=[],api_brackets=[])
    assert r.ok
    assert all(r.checks.values())

def test_parity_fails_on_match_difference():
    t,teams,groups,matches=sample()
    changed=[dict(matches[0])]; changed[0]["home_score"]=3
    r=compare_public_payloads(tournament=t,teams=teams,groups=groups,
        legacy_matches=matches,api_matches=changed,legacy_brackets=[],api_brackets=[])
    assert not r.ok
    assert not r.checks["matches"]

def test_ci_runs_public_parity_gate():
    workflow=(ROOT/".github/workflows/v139-quality.yml").read_text()
    assert "check_public_parity.py" in workflow
    assert "create_parity_fixture.py" in workflow

def test_parity_script_is_read_only():
    script=(ROOT/"scripts/check_public_parity.py").read_text()
    assert "UPDATE " not in script
    assert "INSERT " not in script
    assert "DELETE " not in script

def test_parity_docs_include_real_turso_path():
    doc=(ROOT/"PUBLIC_PARITY_V155.md").read_text()
    assert "TURSO_DATABASE_URL" in doc
    assert "CUPNAVI_PARITY_CUP" in doc
