from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import time
import urllib.request

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Route, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend-next"
PORT = int(os.getenv("CUPNAVI_E2E_WEB_PORT", "8872"))
BASE = f"http://127.0.0.1:{PORT}"


def wait_url(url: str, timeout: int = 30) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError(f"Timed out waiting for {url}")


@pytest.fixture(scope="module")
def next_server():
    standalone = FRONTEND / ".next" / "standalone"
    if not (standalone / "server.js").exists():
        pytest.fail("Next production build missing; run npm run build in frontend-next first")
    shutil.copytree(FRONTEND / "public", standalone / "public", dirs_exist_ok=True)
    shutil.copytree(FRONTEND / ".next" / "static", standalone / ".next" / "static", dirs_exist_ok=True)
    process = subprocess.Popen(
        ["node", "server.js"],
        cwd=standalone,
        env={**os.environ, "PORT": str(PORT), "HOSTNAME": "127.0.0.1"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_url(f"{BASE}/reporter")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


MATCH = {
    "id": 10,
    "stage": "Gruppspel",
    "home_team": "Parity FC",
    "away_team": "Test United",
    "home_score": None,
    "away_score": None,
    "home_penalties": None,
    "away_penalties": None,
    "status": "scheduled",
    "scheduled_start": "2026-09-16T12:00",
}


def mock_reporter_api(route: Route) -> None:
    url = route.request.url
    if url.endswith("/api/reporter/session"):
        route.fulfill(json={"cup": {"id": 1, "name": "Parity Cup", "public_slug": "parity-cup"}})
    elif url.endswith("/api/reporter/reporting/events"):
        route.fulfill(json={"matches": []})
    elif url.endswith("/api/reporter/reporting"):
        route.fulfill(json={"matches": [MATCH]})
    else:
        route.fulfill(status=404, json={"detail": "not mocked"})


def test_android_and_iphone_keep_reporter_result_offline(next_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for device_name in ("Pixel 7", "iPhone 14"):
            context = browser.new_context(**playwright.devices[device_name], service_workers="allow")
            context.add_init_script(
                "localStorage.setItem('cupnavi_reporter_session_v1','e2e-token')"
            )
            page = context.new_page()
            page.route("https://cupnavi-api.onrender.com/api/reporter/**", mock_reporter_api)
            page.goto(f"{BASE}/reporter?cup=parity-cup", wait_until="networkidle")
            page.get_by_text("Parity FC", exact=True).first.wait_for()
            assert page.locator(".reporter-network").get_by_text("Online", exact=True).is_visible()

            page.evaluate("() => navigator.serviceWorker.ready.then(() => true)")
            page.reload(wait_until="networkidle")
            page.get_by_text("Parity FC", exact=True).first.wait_for()

            context.set_offline(True)
            page.get_by_label("Mål för Parity FC").fill("2")
            page.get_by_label("Mål för Test United").fill("1")
            page.get_by_role("button", name="Spara resultat").click()
            assert page.locator(".reporter-network").get_by_text("Offline", exact=True).is_visible()
            assert page.get_by_text("Väntar på nät", exact=True).is_visible()
            queued = page.evaluate(
                "() => JSON.parse(localStorage.getItem('cupnavi_reporter_queue_v1') || '[]')"
            )
            assert queued[0]["payload"]["home_score"] == 2
            assert queued[0]["payload"]["away_score"] == 1

            page.reload(wait_until="domcontentloaded")
            page.get_by_text("Parity FC", exact=True).first.wait_for(timeout=10_000)
            assert page.get_by_text("Väntar på nät", exact=True).is_visible()
            context.close()
        browser.close()
