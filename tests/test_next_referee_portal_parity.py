from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
backend=(ROOT/'cupnavi_api'/'referee_access_routes.py').read_text(encoding='utf-8')
routes=(ROOT/'cupnavi_api'/'competition_admin_routes.py').read_text(encoding='utf-8')
page=(ROOT/'frontend-next'/'src'/'app'/'referee'/'page.tsx').read_text(encoding='utf-8')
ops=(ROOT/'frontend-next'/'src'/'components'/'admin-operations.tsx').read_text(encoding='utf-8')

assert 'referee_portal_credentials' in backend
assert 'PRIMARY KEY(tournament_id, referee_id)' in backend
assert 'role": "referee"' in backend
assert 'scope="referee_login"' in backend
assert '/api/referee/assignments' in backend
assert 'WHERE tournament_id=? AND {match_column}=?' in backend
assert 'register_referee_access_routes(app,admin_identity)' in routes
assert 'redirect(cup?`/reporter?cup=' in page
assert 'RefereeRoleCodeAdmin' not in ops
assert 'En gemensam rapportörskod' in ops
