from __future__ import annotations
from pathlib import Path
import os, subprocess, sys, time, urllib.request, json, shutil
import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=Path(os.getenv("CUPNAVI_PARITY_FIXTURE","/tmp/cupnavi-mobile-e2e.db"))
API_PORT=int(os.getenv("CUPNAVI_E2E_API_PORT","8871"))
WEB_PORT=int(os.getenv("CUPNAVI_E2E_WEB_PORT","8872"))
API_BASE=f"http://127.0.0.1:{API_PORT}"
WEB_BASE=f"http://127.0.0.1:{WEB_PORT}"

def wait_url(url, timeout=20):
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=2) as resp:
                if resp.status==200:
                    return
        except Exception:
            time.sleep(.3)
    raise RuntimeError(f"Timed out waiting for {url}")

@pytest.fixture(scope="module")
def servers():
    env=os.environ.copy()
    env["CUPNAVI_API_SQLITE_PATH"]=str(FIXTURE)
    subprocess.run([sys.executable,"scripts/create_parity_fixture.py"],cwd=ROOT,env={**env,"CUPNAVI_PARITY_FIXTURE":str(FIXTURE)},check=True)

    # Inject API base for static PWA test origin.
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
            try: proc.wait(timeout=4)
            except subprocess.TimeoutExpired: proc.kill()
        config.write_text(original,encoding="utf-8")

def _run_device(browser, device, servers):
    context=browser.new_context(**device)
    page=context.new_page()
    page.goto(f"{WEB_BASE}/?cup=parity-cup",wait_until="networkidle")
    page.wait_for_selector("#teamSelect:not(.hidden)")
    assert "Parity Cup" in page.locator("#cupName").inner_text()

    # Core mobile navigation must all be reachable.
    for page_name in ("matches","table","playoff","info"):
        page.locator(f'nav button[data-page="{page_name}"]').click()
        page.wait_for_timeout(200)
        assert page.locator(f'nav button[data-page="{page_name}"]').get_attribute("class") is not None

    # Follow a team and verify Min cup context.
    page.locator("#teamSelect").select_option("1")
    page.locator('nav button[data-page="matches"]').click()
    page.wait_for_timeout(300)
    assert "Mitt lag" in page.locator("#view").inner_text()

    # Offline app-shell should survive after one online load.
    context.set_offline(True)
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    assert page.locator("body").is_visible()
    context.close()

def test_android_and_iphone_mobile_pwa(servers):
    with sync_playwright() as p:
        system_chromium=shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        browser=p.chromium.launch(headless=True, executable_path=system_chromium) if system_chromium else p.chromium.launch(headless=True)
        _run_device(browser,p.devices["Pixel 7"],servers)
        _run_device(browser,p.devices["iPhone 14"],servers)
        browser.close()
