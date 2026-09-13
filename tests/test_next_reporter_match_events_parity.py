from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
routes=(ROOT/'cupnavi_api'/'role_access_routes.py').read_text(encoding='utf-8')
reporter=(ROOT/'frontend-next'/'src'/'components'/'reporter-client.tsx').read_text(encoding='utf-8')
events=(ROOT/'frontend-next'/'src'/'components'/'reporter-match-events.tsx').read_text(encoding='utf-8')

assert '/api/reporter/reporting/events' in routes
assert '/api/reporter/reporting/matches/{match_id}/events' in routes
assert '/api/reporter/reporting/matches/{match_id}/events/{player_id}' in routes
assert 'update_player_match_events' in routes
assert 'ReporterMatchEvents' in reporter
assert 'målskyttar, assist och kort' in reporter.lower()
assert '/api/reporter/reporting/events' in events
assert '/api/reporter/reporting/matches/${detail.match.id}/events/${player.id}' in events
assert 'Målskyttar, assist & kort' in events
assert 'registered_goals' in events
assert 'expected:previous' in events
