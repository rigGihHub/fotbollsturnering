from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
repo=(ROOT/'cupnavi_api'/'player_admin_repository.py').read_text(encoding='utf-8')
routes=(ROOT/'cupnavi_api'/'competition_admin_routes.py').read_text(encoding='utf-8')
ui=(ROOT/'frontend-next'/'src'/'components'/'roster-admin.tsx').read_text(encoding='utf-8')
ops=(ROOT/'frontend-next'/'src'/'components'/'admin-operations.tsx').read_text(encoding='utf-8')
assert 'player_match_stats' in repo
assert 'kan inte tas bort' in repo
assert "/players'" in routes or '/players\"' in routes
assert 'TRUPPER / SPELARE' in ui
assert 'Spelarna används direkt av målskyttar, assist och kort' in ui
assert '<RosterAdmin token={token} cupId={cupId}/>' in ops
