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
        page.wait_for_selector("body",timeout=20000)
        page.wait_for_timeout(2500)
        body=page.locator("body").inner_text()
        assert "This app has encountered an error" not in body
        assert "CupNavi" in body or "Turneringar" in body
        overflow=page.evaluate("() => document.documentElement.scrollWidth-document.documentElement.clientWidth")
        assert overflow <= 4
        ctx.close()
        browser.close()
