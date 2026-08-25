from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_pwa_runtime_config_is_loaded_before_app():
    html=(ROOT/"public_pwa/index.html").read_text()
    assert html.index("config.js") < html.index("app.js")

def test_service_worker_caches_runtime_config():
    sw=(ROOT/"public_pwa/service-worker.js").read_text()
    assert "./config.js" in sw

def test_mobile_e2e_covers_android_iphone_and_offline():
    e2e=(ROOT/"e2e/test_mobile_pwa.py").read_text()
    assert 'p.devices["Pixel 7"]' in e2e
    assert 'p.devices["iPhone 14"]' in e2e
    assert "context.set_offline(True)" in e2e

def test_https_staging_check_requires_https_and_pwa_assets():
    script=(ROOT/"scripts/check_https_staging.py").read_text()
    assert 'parsed.scheme!="https"' in script
    assert "/manifest.webmanifest" in script
    assert "/service-worker.js" in script
    assert "security headers" in script.lower()

def test_browser_workflow_installs_chromium():
    workflow=(ROOT/".github/workflows/mobile-pwa-e2e.yml").read_text()
    assert "playwright install --with-deps chromium" in workflow
