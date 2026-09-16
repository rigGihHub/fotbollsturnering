from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import time
import urllib.request

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend-next"
PORT = int(os.getenv("CUPNAVI_E2E_WEB_PORT", "8972"))
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
        pytest.fail("Next production build missing")
    shutil.copytree(FRONTEND / "public", standalone / "public", dirs_exist_ok=True)
    shutil.copytree(FRONTEND / ".next" / "static", standalone / ".next" / "static", dirs_exist_ok=True)
    process = subprocess.Popen(
        ["node", "server.js"], cwd=standalone,
        env={**os.environ, "PORT": str(PORT), "HOSTNAME": "127.0.0.1"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
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


@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
@pytest.mark.parametrize("viewport", [
    {"width": 1440, "height": 900},
    {"width": 390, "height": 844},
])
def test_next_reporter_login_cross_browser(next_server, browser_name, viewport):
    with sync_playwright() as playwright:
        browser = getattr(playwright, browser_name).launch(headless=True)
        context = browser.new_context(viewport=viewport, has_touch=viewport["width"] < 600)
        page = context.new_page()
        page.goto(f"{BASE}/reporter", wait_until="networkidle")
        assert page.get_by_role("heading", name="Matchrapportör").is_visible()
        assert page.get_by_label("4-siffrig kod").is_visible()
        overflow = page.evaluate(
            "() => Math.max(0, document.documentElement.scrollWidth-document.documentElement.clientWidth)"
        )
        offenders = page.evaluate(
            """() => [...document.querySelectorAll('body *')]
              .map(element => {
                const rect = element.getBoundingClientRect();
                return {tag: element.tagName, classes: element.className,
                        left: Math.round(rect.left), right: Math.round(rect.right)};
              })
              .filter(item => item.left < -4 || item.right > window.innerWidth + 4)
              .slice(0, 10)"""
        )
        assert overflow <= 4, f"Horizontal overflow {overflow}px caused by {offenders}"
        button_box = page.get_by_role("button", name="Öppna matchrapportering").bounding_box()
        assert button_box and button_box["height"] >= 44
        context.close()
        browser.close()
