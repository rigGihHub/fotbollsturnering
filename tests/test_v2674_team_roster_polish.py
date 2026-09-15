from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend-next/src/app/admin-teams-v2674.css").read_text(encoding="utf-8")
FLOW = (ROOT / "frontend-next/src/components/admin-step-flow.tsx").read_text(encoding="utf-8")

def test_broken_logos_fall_back_to_team_initials():
    assert "function TeamLogo" in UI
    assert "onError={()=>setFailed(true)}" in UI
    assert 'team.name.slice(0,2).toLocaleUpperCase("sv")' in UI

def test_roster_uses_outlined_svg_kits_and_separate_metadata():
    start = UI.index('className="admin-team-list admin-team-roster"')
    roster = UI[start:UI.index("{teams.length>0&&", start)]
    assert roster.count("<TeamKit") == 2
    assert 'className="admin-team-identity"' in roster
    assert "admin-team-kits .team-kit" in CSS
    assert "admin-team-identity small" in CSS

def test_team_step_instruction_is_short_and_asset_complete():
    assert "Sök sedan matchställ eller klubbmärke." in FLOW
