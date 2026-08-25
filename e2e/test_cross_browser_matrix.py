from __future__ import annotations
from pathlib import Path
import os, subprocess, sys, time, urllib.request, shutil
import pytest
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=Path(os.getenv("CUPNAVI_PARITY_FIXTURE","/tmp/cupnavi-cross-browser.db"))
API_PORT=int(os.getenv("CUPNAVI_E2E_API_PORT","8971"))
WEB_PORT=int(os.getenv("CUPNAVI_E2E_WEB_PORT","8972"))
API_BASE=f"http://127.0.0.1:{API_PORT}"
WEB_BASE=f"http://127.0.0.1:{WEB_PORT}"

def wait_url(url, timeout=30):
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=2) as resp:
                if resp.status==200:return
        except Exception:
            time.sleep(.25)
    raise RuntimeError(f"Timed out waiting for {url}")

@pytest.fixture(scope="module")
def servers():
    env=os.environ.copy()
    env["CUPNAVI_API_SQLITE_PATH"]=str(FIXTURE)
    subprocess.run(
        [sys.executable,"scripts/create_parity_fixture.py"],
        cwd=ROOT,env={**env,"CUPNAVI_PARITY_FIXTURE":str(FIXTURE)},check=True,
    )
    config=ROOT/"public_pwa/config.js"
    original=config.read_text(encoding="utf-8")
    config.write_text(f'window.CUPNAVI_API_BASE = "{API_BASE}";\n',encoding="utf-8")
    api=subprocess.Popen(
        [sys.executable,"-m","uvicorn","cupnavi_api.main:app","--host","127.0.0.1","--port",str(API_PORT)],
        cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
    )
    web=subprocess.Popen(
        [sys.executable,"-m","http.server",str(WEB_PORT),"-d","public_pwa"],
        cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
    )
    try:
        wait_url(f"{API_BASE}/health")
        wait_url(f"{WEB_BASE}/index.html")
        yield
    finally:
        for proc in (api,web):
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:proc.kill()
        config.write_text(original,encoding="utf-8")

def exercise(page):
    page.goto(f"{WEB_BASE}/?cup=parity-cup",wait_until="networkidle")
    page.wait_for_selector("#teamSelect:not(.hidden)")
    assert "Parity Cup" in page.locator("#cupName").inner_text()

    for page_name in ("matches","table","playoff","info"):
        button=page.locator(f'nav button[data-page="{page_name}"]')
        assert button.is_visible()
        button.click()
        page.wait_for_timeout(150)

    overflow=page.evaluate("() => document.documentElement.scrollWidth-document.documentElement.clientWidth")
    assert overflow <= 2, f"Horizontal overflow {overflow}px"

    page.locator("#teamSelect").select_option("1")
    page.locator('nav button[data-page="matches"]').click()
    page.wait_for_timeout(200)
    assert "Mitt lag" in page.locator("#view").inner_text()

@pytest.mark.parametrize("browser_name",["chromium","firefox","webkit"])
@pytest.mark.parametrize("viewport",[
    {"width":1440,"height":900},
    {"width":1366,"height":768},
    {"width":412,"height":915},
    {"width":390,"height":844},
])
def test_cross_browser_core(servers,browser_name,viewport):
    with sync_playwright() as p:
        browser=getattr(p,browser_name).launch(headless=True)
        context=browser.new_context(viewport=viewport,has_touch=viewport["width"]<600)
        page=context.new_page()
        exercise(page)
        context.close()
        browser.close()
