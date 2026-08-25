from __future__ import annotations
from pathlib import Path
import os, subprocess, sys, time, urllib.request
import pytest
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PORT=8980
BASE=f"http://127.0.0.1:{PORT}"

def wait_url(url, timeout=45):
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=2) as resp:
                if resp.status==200:return
        except Exception:
            time.sleep(.4)
    raise RuntimeError(f"Timed out waiting for {url}")

@pytest.fixture(scope="module")
def streamlit_server():
    env=os.environ.copy()
    proc=subprocess.Popen(
        [sys.executable,"-m","streamlit","run","app.py","--server.headless=true",
         f"--server.port={PORT}","--server.address=127.0.0.1"],
        cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
    )
    try:
        wait_url(BASE)
        yield
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill()

@pytest.mark.parametrize("browser_name",["chromium","firefox","webkit"])
@pytest.mark.parametrize("viewport",[
    {"width":1440,"height":900},
    {"width":390,"height":844},
])
def test_streamlit_public_shell(streamlit_server,browser_name,viewport):
    with sync_playwright() as p:
        browser=getattr(p,browser_name).launch(headless=True)
        ctx=browser.new_context(viewport=viewport,has_touch=viewport["width"]<600)
        page=ctx.new_page()
        page.goto(BASE,wait_until="domcontentloaded")

        # Streamlit can temporarily keep <body> hidden while its frontend
        # bootstraps. Waiting for body visibility makes the browser smoke test
        # fail even though the app itself is healthy. Wait for the body to be
        # attached, then for Streamlit's app root to become visible.
        page.wait_for_selector("body",state="attached",timeout=20000)
        page.wait_for_selector(
            '[data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp',
            state="visible",
            timeout=30000,
        )

        # Give Streamlit one short render cycle after the shell becomes visible.
        page.wait_for_timeout(750)
        body=page.locator("body").inner_text()
        assert "This app has encountered an error" not in body
        assert "Traceback" not in body

        # Smoke-test the Streamlit shell itself, not exact product copy.
        # The visible app root above proves that Streamlit rendered. Exact labels
        # are covered by product/regression tests and may legitimately change.
        app_root=page.locator(
            '[data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp'
        ).first
        assert app_root.is_visible()

        overflow=page.evaluate(
            "() => Math.max(0, document.documentElement.scrollWidth-document.documentElement.clientWidth)"
        )
        assert overflow <= 4
        ctx.close()
        browser.close()
