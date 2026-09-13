from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
backend=(ROOT/'cupnavi_api'/'team_access_routes.py').read_text(encoding='utf-8')
routes=(ROOT/'cupnavi_api'/'competition_admin_routes.py').read_text(encoding='utf-8')
admin=(ROOT/'frontend-next'/'src'/'components'/'team-role-code-admin.tsx').read_text(encoding='utf-8')
portal=(ROOT/'frontend-next'/'src'/'components'/'team-client.tsx').read_text(encoding='utf-8')
page=(ROOT/'frontend-next'/'src'/'app'/'team'/'page.tsx').read_text(encoding='utf-8')
ops=(ROOT/'frontend-next'/'src'/'components'/'admin-operations.tsx').read_text(encoding='utf-8')

assert 'team_portal_credentials' in backend
assert 'PRIMARY KEY(tournament_id, team_id)' in backend
assert '"role": "team"' in backend
assert 'scope="team_login"' in backend
assert '/api/team/portal' in backend
assert 'home.team_id != int(team_id) and away.team_id != int(team_id)' in backend
assert 'SELECT id,name,player_number FROM players WHERE team_id=?' in backend
assert 'register_team_access_routes(app,admin_identity)' in routes
assert 'Varje lag får en egen 4-siffrig kod' in admin
assert '/team?cup=' in admin
assert 'bara det egna laget' in portal
assert 'TeamClient' in page
assert '<TeamRoleCodeAdmin token={token} cupId={cupId}' in ops
