from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
repo=(ROOT/'cupnavi_api'/'result_correction_repository.py').read_text(encoding='utf-8')
routes=(ROOT/'cupnavi_api'/'publish_reporting_routes.py').read_text(encoding='utf-8')
ui=(ROOT/'frontend-next'/'src'/'components'/'publish-reporting-admin.tsx').read_text(encoding='utf-8')
assert 'transitive_downstream_match_ids' in repo
assert 'dependency_impact' in repo
assert 'build_dependency_guidance' in repo
assert 'recovery_eligibility' in repo
assert "reporting/matches/{match_id}/impact" in routes
assert 'hela kedjeeffekten' in ui
assert 'Kontrollera & spara' in ui
assert 'impact.blocked' in ui
assert 'impact.outcome_changes' in ui
