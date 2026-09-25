from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_reporter_has_persistent_safe_offline_queue():
    queue = read("frontend-next/src/lib/reporter-offline.ts")
    reporter = read("frontend-next/src/components/reporter-client.tsx")
    events = read("frontend-next/src/components/reporter-match-events.tsx")
    worker = read("frontend-next/public/sw.js")
    assert "cupnavi_reporter_queue_v1" in queue
    assert "localStorage.setItem(QUEUE_KEY" in queue
    assert 'state:"queued"|"uncertain"|"conflict"' in queue
    assert "const unchanged=" in reporter
    assert "stäms av mot servern" in reporter
    assert "sameEventValues(current,mutation.payload.expected)" in events
    assert 'item.state!=="conflict"' in queue
    assert 'item.state!=="conflict"' in events
    assert '"/reporter"' in worker


def test_referee_has_persistent_safe_offline_queue():
    queue = read("frontend-next/src/lib/referee-offline.ts")
    referee = read("frontend-next/src/components/referee-client.tsx")
    assert "cupnavi_referee_queue_v1" in queue
    assert "localStorage.setItem(QUEUE_KEY" in queue
    assert 'state:"queued"|"uncertain"|"conflict"' in queue
    assert "const unchanged=" in referee
    assert "stäms av mot servern" in referee
    assert "Ett offline-resultat krockar med ett nyare serverresultat" in referee
    assert "Sparad domarvy visas medan CupNavi återansluter" in referee
    assert 'item.state!=="conflict"' in referee


def test_reporter_controls_are_large_and_network_state_is_visible():
    reporter = read("frontend-next/src/components/reporter-client.tsx")
    result_css = read("frontend-next/src/app/reporter-v2665.css")
    event_css = read("frontend-next/src/app/reporter-flow-v2667.css")
    assert "reporter-network" in reporter
    assert '"Alla ändringar är synkroniserade":"Inmatningar sparas på mobilen"' in reporter
    assert 'conflicts>0?"Åtgärd krävs"' in reporter
    assert ".reporter-score input{height:64px" in result_css
    assert ".reporter-score button{min-height:62px" in result_css
    assert ".reporter-counter button{width:60px;height:60px" in event_css
    assert "touch-action:manipulation" in event_css


def test_reporter_warms_api_on_visit_and_defers_authenticated_event_ui():
    page = read("frontend-next/src/app/reporter/page.tsx")
    reporter = read("frontend-next/src/components/reporter-client.tsx")
    wake_guard = read("frontend-next/src/components/api-wake-guard.tsx")
    assert "<ApiWakeGuard/>" in page
    assert 'dynamic(()=>import("./reporter-match-events"))' in reporter
    assert 'fetch(`${CLIENT_API_BASE}/health`' in wake_guard
    assert "MAX_WAIT_MS = 75000" in wake_guard


def test_public_first_paint_defers_nonessential_work_and_long_lists():
    page = read("frontend-next/src/app/cup/[publicKey]/page.tsx")
    public_view = read("frontend-next/src/components/PublicCupView.tsx")
    assert "getStandings" not in page
    assert "filteredMatches.slice(0,visibleCount)" in public_view
    assert "IntersectionObserver" in public_view
    assert 'tab!=="table"' in public_view
    assert "Visa fler" in public_view


def test_public_mobile_staff_links_cannot_cover_cup_name():
    css = read("frontend-next/src/app/design-system.css")
    mobile = css.split("@media(max-width:760px)", 1)[1]
    assert ".cn-public .cn-staff-nav {position:static" in mobile
    assert "position:absolute;z-index:3;top:13px;right:14px" not in mobile


def test_public_live_polling_backs_off_after_rate_limits_and_server_errors():
    api = read("frontend-next/src/lib/api.ts")
    public_view = read("frontend-next/src/components/PublicCupView.tsx")
    assert "retryAfterMs(response)" in api
    assert "public readonly retryAfterMs?:number" in api
    assert "MIN_REFRESH_BACKOFF_MS=30000" in public_view
    assert "MAX_REFRESH_BACKOFF_MS=120000" in public_view
    assert "nextAllowedRefreshRef.current" in public_view
    assert "publicRefreshBackoffMs.current?publicRefreshBackoffMs.current*2:MIN_REFRESH_BACKOFF_MS" in public_view
    assert "return cooldownMs?Math.max(cooldownMs,baseDelay):baseDelay" in public_view


def test_release_version_is_synchronized_and_ci_uses_maintained_gate():
    import json
    package=json.loads(read("frontend-next/package.json"))
    lock=json.loads(read("frontend-next/package-lock.json"))
    version=package["version"]
    assert lock["version"] == version
    assert lock["packages"][""]["version"] == version
    assert f'APP_VERSION = "{version}"' in read("frontend-next/src/lib/version.ts")
    assert 'import { APP_VERSION } from "@/lib/version"' in read("frontend-next/src/app/layout.tsx")
    workflow = read(".github/workflows/v139-quality.yml")
    assert "python scripts/run_maintained_release_gate.py" in workflow
    assert "python scripts/run_current_release_gate.py" not in workflow


def test_browser_workflows_target_next_not_legacy_streamlit_or_public_pwa():
    mobile = read("e2e/test_mobile_pwa.py")
    matrix = read(".github/workflows/cross-browser.yml")
    assert 'standalone / "server.js"' in mobile
    assert "cupnavi_reporter_queue_v1" in mobile
    assert "public_pwa" not in mobile
    assert "test_streamlit_browser_smoke.py" not in matrix
    assert "npm run build --prefix frontend-next" in matrix
