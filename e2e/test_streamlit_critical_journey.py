from __future__ import annotations
from pathlib import Path
import os, re, sqlite3, subprocess, sys, time, urllib.request
import pytest
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PORT=8990
BASE=f"http://127.0.0.1:{PORT}"
DB=Path("/tmp/cupnavi-streamlit-critical-journey.db")


def wait_url(url, timeout=45):
    deadline=time.time()+timeout
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=2) as resp:
                if resp.status==200:
                    return
        except Exception:
            time.sleep(.4)
    raise RuntimeError(f"Timed out waiting for {url}")


@pytest.fixture(scope="module")
def server():
    DB.unlink(missing_ok=True)
    env=os.environ.copy()
    env["CUPNAVI_DB_PATH"]=str(DB)
    env.pop("TURSO_DATABASE_URL",None)
    env.pop("TURSO_AUTH_TOKEN",None)
    env.pop("ADMIN_PASSWORD",None)
    env.pop("MATCH_REPORTER_PASSWORD",None)
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
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()
        DB.unlink(missing_ok=True)


def wait_app(page):
    page.wait_for_selector(
        '[data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp',
        state="visible",timeout=30000,
    )
    page.wait_for_timeout(650)


def click_if_enabled(locator):
    if locator.count() and locator.first.is_visible() and locator.first.is_enabled():
        locator.first.click()
        return True
    return False


def assert_complete_database(cup_name):
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    cup=con.execute(
        "SELECT id,is_published,lifecycle_status FROM tournaments WHERE name=? ORDER BY id DESC LIMIT 1",
        (cup_name,),
    ).fetchone()
    assert cup is not None
    tid=int(cup["id"])
    classes=con.execute("SELECT COUNT(*) FROM competition_classes WHERE tournament_id=?",(tid,)).fetchone()[0]
    teams=con.execute("SELECT COUNT(*) FROM teams WHERE tournament_id=?",(tid,)).fetchone()[0]
    groups=con.execute("SELECT COUNT(*) FROM groups WHERE tournament_id=?",(tid,)).fetchone()[0]
    matches=con.execute("SELECT COUNT(*) FROM matches WHERE tournament_id=?",(tid,)).fetchone()[0]
    played=con.execute(
        "SELECT COUNT(*) FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (tid,),
    ).fetchone()[0]
    playoffs=con.execute(
        "SELECT COUNT(*) FROM matches WHERE tournament_id=? AND stage<>'Gruppspel'",
        (tid,),
    ).fetchone()[0]
    con.close()
    assert classes >= 1
    assert teams == 8
    assert groups == 2
    assert matches > 0
    assert played == matches
    assert playoffs > 0
    assert int(cup["is_published"]) == 1
    assert cup["lifecycle_status"] == "completed"
    return tid


@pytest.mark.parametrize("browser_name",["chromium","firefox","webkit"])
def test_full_cup_lifecycle_journey(server,browser_name):
    with sync_playwright() as p:
        browser=getattr(p,browser_name).launch(headless=True)
        ctx=browser.new_context(viewport={"width":1280,"height":900})
        page=ctx.new_page()
        page.goto(BASE,wait_until="domcontentloaded")
        wait_app(page)

        # 1. Admin → create a real persisted Testmiljö through the actual UI.
        page.get_by_role("button",name="Admin",exact=True).click()
        wait_app(page)
        page.get_by_text("Skapa ny turnering",exact=True).click()
        cup_name=f"E2E Full {browser_name}"
        page.get_by_label("Namn",exact=True).fill(cup_name)
        page.get_by_label("Spelort",exact=True).fill("Örebro")
        page.get_by_text("Testmiljö",exact=True).click()
        page.get_by_role("button",name="Skapa",exact=True).click()
        wait_app(page)

        # Creation lands in the guided setup before the normal Admin header is
        # rendered. Verify the persisted environment first instead of assuming
        # that the TESTMILJÖ banner is already visible on this intermediate page.
        with sqlite3.connect(DB) as con:
            created=con.execute(
                "SELECT environment_type FROM tournaments WHERE name=? ORDER BY id DESC LIMIT 1",
                (cup_name,),
            ).fetchone()
        assert created is not None
        assert created[0] == "test"

        # Finish the guided setup when its current defaults are valid. Once we
        # reach the regular Admin view, the visible environment marker must agree
        # with the persisted environment type.
        continue_button=page.get_by_role("button",name="Fortsätt till Admin",exact=True)
        if continue_button.count():
            continue_button.wait_for(state="visible",timeout=20000)
            assert continue_button.is_enabled(), "Guided setup unexpectedly blocks a newly created Testmiljö"
            continue_button.click()
            wait_app(page)
        assert "TESTMILJÖ" in page.locator("body").inner_text()

        # 2. Classes → teams → groups → players/referees through the app's Testmiljö tool.
        demo_button=page.get_by_role("button",name=re.compile(r"^Skapa testdata:"))
        demo_button.wait_for(state="visible",timeout=20000)
        assert demo_button.is_enabled()
        demo_button.click()
        wait_app(page)
        body=page.locator("body").inner_text()
        assert "Aktuellt testläge" in body

        # 3. Build schedule + publish + results + events + playoff to completion.
        page.get_by_label("Testnivå",exact=True).select_option(label="Hela cupen färdig")
        generate=page.get_by_role("button",name=re.compile(r"Generera testläge: Hela cupen färdig"))
        assert generate.is_enabled()
        generate.click()
        wait_app(page)

        # DB verification proves the UI action completed the whole persistence chain.
        tid=assert_complete_database(cup_name)

        # 4. Public tournament view: schedule/result → table → playoff → statistics → info.
        page.get_by_role("button",name="Turneringsvy",exact=True).click()
        wait_app(page)
        public_body=page.locator("body").inner_text()
        assert cup_name in public_body
        assert "This app has encountered an error" not in public_body
        assert "Traceback" not in public_body

        for label in ("Schema & resultat","Tabeller","Slutspel","Statistik","Cupinfo"):
            button=page.get_by_role("button",name=label,exact=True)
            button.wait_for(state="visible",timeout=15000)
            button.click()
            wait_app(page)
            current=page.locator("body").inner_text()
            assert "This app has encountered an error" not in current
            assert "Traceback" not in current

        overflow=page.evaluate(
            "() => Math.max(0,document.documentElement.scrollWidth-document.documentElement.clientWidth)"
        )
        assert overflow <= 4

        # 5. Role boundary remains part of the lifecycle journey.
        page.get_by_role("button",name="Matchrapportör",exact=True).click()
        wait_app(page)
        page.get_by_label("Lösenord",exact=True).fill("123")
        page.get_by_role("button",name="Logga in",exact=True).click()
        wait_app(page)
        reporter_body=page.locator("body").inner_text()
        assert "endast testmiljöer" in reporter_body
        assert cup_name in reporter_body
        ctx.close()

        # 6. Mobile public verification on the same completed cup.
        mobile=browser.new_context(
            viewport={"width":390,"height":844},
            has_touch=True,
            is_mobile=True if browser_name == "chromium" else False,
        )
        mobile_page=mobile.new_page()
        mobile_page.goto(
            f"{BASE}?public_only=1&cup={tid}&section=matches",
            wait_until="domcontentloaded",
        )
        wait_app(mobile_page)
        mobile_body=mobile_page.locator("body").inner_text()
        assert cup_name in mobile_body
        assert "This app has encountered an error" not in mobile_body
        assert "Traceback" not in mobile_body
        for label in ("Schema","Tabeller","Slutspel","Statistik","Cupinfo"):
            assert mobile_page.locator(".cn-mobile-bottom-nav a",has_text=label).count() >= 1
        mobile_overflow=mobile_page.evaluate(
            "() => Math.max(0,document.documentElement.scrollWidth-document.documentElement.clientWidth)"
        )
        assert mobile_overflow <= 4
        mobile.close()
        browser.close()
