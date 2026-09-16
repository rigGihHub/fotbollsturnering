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
    assert '"/reporter"' in worker


def test_reporter_controls_are_large_and_network_state_is_visible():
    reporter = read("frontend-next/src/components/reporter-client.tsx")
    result_css = read("frontend-next/src/app/reporter-v2665.css")
    event_css = read("frontend-next/src/app/reporter-flow-v2667.css")
    assert "reporter-network" in reporter
    assert '"Online":"Offline"' in reporter
    assert ".reporter-score input{height:64px" in result_css
    assert ".reporter-score button{min-height:62px" in result_css
    assert ".reporter-counter button{width:60px;height:60px" in event_css
    assert "touch-action:manipulation" in event_css


def test_public_first_paint_defers_nonessential_work_and_long_lists():
    page = read("frontend-next/src/app/cup/[publicKey]/page.tsx")
    public_view = read("frontend-next/src/components/PublicCupView.tsx")
    assert "getStandings" not in page
    assert "filteredMatches.slice(0,visibleCount)" in public_view
    assert "IntersectionObserver" in public_view
    assert 'tab!=="table"' in public_view
    assert "Visa fler" in public_view


def test_release_2690_is_synchronized():
    assert '"version": "2.6.90"' in read("frontend-next/package.json")
    assert '"version": "2.6.90"' in read("frontend-next/package-lock.json")
    assert 'APP_VERSION = "2.6.90"' in read("frontend-next/src/app/layout.tsx")
    assert 'cupnavi-next-v2690' in read("frontend-next/public/sw.js")
