from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SW=(ROOT/"public_pwa/service-worker.js").read_text(encoding="utf-8")
E2E=(ROOT/"e2e/test_mobile_pwa.py").read_text(encoding="utf-8")

def test_service_worker_has_navigation_fallback_for_query_urls():
    assert 'if(req.mode==="navigate")' in SW
    assert 'caches.match("./index.html")' in SW
    assert 'caches.match("./")' in SW

def test_mobile_e2e_waits_for_offline_cache_readiness():
    assert "window.CUPNAVI_OFFLINE_READY" in E2E
    assert "context.set_offline(True)" in E2E
    assert 'page.locator("#nav").is_visible()' in E2E
