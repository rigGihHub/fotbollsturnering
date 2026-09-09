from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_staging_compose_has_api_and_caddy():
    compose=(ROOT/"docker-compose.staging.yml").read_text()
    assert "api:" in compose
    assert "web:" in compose
    assert "caddy:2.8-alpine" in compose
    assert "TURSO_DATABASE_URL" in compose

def test_caddy_serves_pwa_and_reverse_proxies_api():
    caddy=(ROOT/"staging/Caddyfile").read_text()
    assert "reverse_proxy @api api:8001" in caddy
    assert "root * /srv/public_pwa" in caddy
    assert "service-worker.js" in caddy

def test_http_parity_is_real_http_not_direct_function_only():
    script=(ROOT/"scripts/check_http_public_parity.py").read_text()
    assert "urllib.request.urlopen" in script
    assert "/api/public/cups/" in script
    assert "/standings" in script
    assert "/playoffs" in script
    assert "/summary" in script

def test_ci_runs_http_parity_and_pwa_contract():
    workflow=(ROOT/".github/workflows/v139-quality.yml").read_text()
    assert "run_http_parity_ci.py" in workflow
    assert "check_pwa_installability.py" in workflow

def test_pwa_installability_checker_exists():
    assert (ROOT/"scripts/check_pwa_installability.py").exists()

def test_staging_env_example_does_not_contain_real_secret():
    env=(ROOT/"staging/.env.staging.example").read_text()
    assert "replace-me" in env
    assert "TURSO_AUTH_TOKEN=" in env
