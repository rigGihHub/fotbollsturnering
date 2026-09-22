from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
backend=(ROOT/'cupnavi_api'/'referee_access_routes.py').read_text(encoding='utf-8')
routes=(ROOT/'cupnavi_api'/'competition_admin_routes.py').read_text(encoding='utf-8')
page=(ROOT/'frontend-next'/'src'/'app'/'referee'/'page.tsx').read_text(encoding='utf-8')
client=(ROOT/'frontend-next'/'src'/'components'/'referee-client.tsx').read_text(encoding='utf-8')
admin=(ROOT/'frontend-next'/'src'/'components'/'referee-admin.tsx').read_text(encoding='utf-8')

assert 'referee_portal_credentials' in backend
assert 'PRIMARY KEY(tournament_id, referee_id)' in backend
assert 'role": "referee"' in backend
assert 'scope="referee_login"' in backend
assert '/api/referee/assignments' in backend
assert '@app.put("/api/referee/assignments/matches/{match_id}")' in backend
assert '_require_referee_match(int(identity["tid"]), int(identity["rid"]), match_id)' in backend
assert 'WHERE tournament_id=? AND {match_column}=?' in backend
assert 'register_referee_access_routes(app,admin_identity)' in routes
assert 'RefereeClient' in page
assert '/api/referee/session' in client
assert '/api/referee/assignments/matches/' in client
assert 'role-codes/referees' in admin
assert '/referee?cup=${base}&referee=${r.id}' in admin
