from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
routes=(ROOT/'cupnavi_api'/'role_access_routes.py').read_text(encoding='utf-8')
competition=(ROOT/'cupnavi_api'/'competition_admin_routes.py').read_text(encoding='utf-8')
admin=(ROOT/'frontend-next'/'src'/'components'/'role-code-admin.tsx').read_text(encoding='utf-8')
reporter=(ROOT/'frontend-next'/'src'/'components'/'reporter-client.tsx').read_text(encoding='utf-8')
page=(ROOT/'frontend-next'/'src'/'app'/'reporter'/'page.tsx').read_text(encoding='utf-8')
assert 'generate_short_numeric_code(4)' in routes
assert 'new_code_hash' in routes and 'verify_access_code' in routes
assert 'consume_rate_limit' in routes
assert 'rotated_at' in routes and 'Reporter session expired or invalid' in routes
assert 'register_role_access_routes(app,admin_identity)' in competition
assert 'Den ger bara åtkomst till resultat och matchhändelser' in admin
assert '/api/reporter/reporting/matches/' in reporter
assert 'Cupinställningar är inte åtkomliga här' in reporter
assert 'ReporterClient' in page
