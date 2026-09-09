from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SW=(ROOT/"public_pwa/service-worker.js").read_text(encoding="utf-8")
JS=(ROOT/"public_pwa/app.js").read_text(encoding="utf-8")
E2E=(ROOT/"e2e/test_mobile_pwa.py").read_text(encoding="utf-8")

def test_service_worker_accepts_explicit_public_cache_requests():
    assert 'CACHE_PUBLIC_URLS' in SW
    assert 'CACHE_PUBLIC_URLS_DONE' in SW
    assert 'await cache.put(req,resp.clone())' in SW

def test_pwa_preloads_core_public_endpoints_for_offline_use():
    assert "async function cachePublicUrls" in JS
    assert "publicOfflineUrls" in JS
    assert "/standings" in JS
    assert "/playoffs" in JS
    assert "window.CUPNAVI_OFFLINE_READY" in JS

def test_followed_team_summary_is_part_of_offline_cache():
    assert '/teams/${Number(teamId)}/summary' in JS

def test_e2e_waits_for_explicit_offline_ready_result():
    assert "window.CUPNAVI_OFFLINE_READY" in E2E
    assert 'offline_ready.get("ok") is True' in E2E
    assert 'page.wait_for_selector("#nav:not(.hidden)"' in E2E

def test_service_worker_cache_version_is_current():
    assert 'const CACHE="cupnavi-pwa-v160";' in SW
