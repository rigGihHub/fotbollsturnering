from __future__ import annotations
from pathlib import Path
import os, re, sqlite3, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta
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
    env["CUPNAVI_E2E"]="1"
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


def assert_no_ui_error(page):
    body=page.locator("body").inner_text()
    assert "This app has encountered an error" not in body
    assert "Traceback" not in body
    assert "NameError:" not in body
    assert "ValueError:" not in body


def create_test_tournament_through_ui(page, cup_name):
    """Create a persisted Testmiljö using the real Streamlit UI and return its id."""
    page.get_by_text("Skapa ny turnering",exact=True).click()
    create_form=page.locator('[data-testid="stSidebar"] [data-testid="stForm"]').first
    create_form.get_by_label("Namn",exact=True).fill(cup_name)
    create_form.get_by_label("Spelort",exact=True).fill("Örebro")
    # Streamlit renders the semantic radio <input> as a hidden React-Aria
    # control. Playwright check() on that hidden input is not stable across
    # Firefox/Chromium/WebKit. Interact with the visible option label inside the
    # form's own stRadio widget, then reacquire the semantic input after rerender.
    environment_radio=create_form.locator('[data-testid="stRadio"]').first
    test_environment_label=environment_radio.locator("label").filter(has_text="Testmiljö")
    test_environment_label.click(force=True)
    page.wait_for_timeout(300)
    test_environment=create_form.get_by_role("radio",name="Testmiljö",exact=True)
    test_environment.wait_for(state="attached",timeout=10000)
    assert test_environment.is_checked(), "Testmiljö radio did not become selected"
    create_form.get_by_role("button",name="Skapa",exact=True).click()
    wait_app(page)

    with sqlite3.connect(DB) as con:
        row=con.execute(
            "SELECT id,environment_type FROM tournaments WHERE name=? ORDER BY id DESC LIMIT 1",
            (cup_name,),
        ).fetchone()
    assert row is not None
    assert row[1] == "test"

    continue_button=page.get_by_role("button",name="Fortsätt till Admin",exact=True)
    if continue_button.count():
        continue_button.wait_for(state="visible",timeout=20000)
        assert continue_button.is_enabled()
        continue_button.click()
        wait_app(page)
    assert_no_ui_error(page)
    return int(row[0])


def representative_public_tokens(tournament_id):
    with sqlite3.connect(DB) as con:
        team=con.execute(
            "SELECT name FROM teams WHERE tournament_id=? ORDER BY id LIMIT 1",
            (tournament_id,),
        ).fetchone()
        group=con.execute(
            "SELECT name FROM groups WHERE tournament_id=? ORDER BY id LIMIT 1",
            (tournament_id,),
        ).fetchone()
    return team[0] if team else None, group[0] if group else None


def click_if_enabled(locator):
    if locator.count() and locator.first.is_visible() and locator.first.is_enabled():
        locator.first.click()
        return True
    return False


def wait_until_enabled(locator, timeout=20000):
    deadline=time.time()+timeout/1000
    last_error=None
    while time.time()<deadline:
        try:
            if locator.count() and locator.first.is_visible() and locator.first.is_enabled():
                return locator.first
        except Exception as exc:
            last_error=exc
        time.sleep(.2)
    detail=f" ({last_error})" if last_error else ""
    raise AssertionError(f"Timed out waiting for enabled locator{detail}")


def choose_streamlit_option(page, label, option, timeout=20000):
    """Choose an option from Streamlit's React-Aria combobox.

    Streamlit selectbox is not a native <select>, so Playwright select_option()
    is intentionally not used here.
    """
    combo=wait_until_enabled(page.get_by_label(label,exact=True),timeout=timeout)
    combo.click()
    choice=page.get_by_role("option",name=option,exact=True)
    choice.wait_for(state="visible",timeout=timeout)
    choice.click()
    page.wait_for_function(
        "([label, expected]) => { const el=[...document.querySelectorAll('[aria-label]')].find(x => x.getAttribute('aria-label')===label && !x.disabled); return !!el && el.value===expected; }",
        arg=[label,option],
        timeout=timeout,
    )




def _cup_progress_state(tournament_id):
    try:
        with sqlite3.connect(DB) as con:
            return con.execute(
                """SELECT
                     (SELECT COUNT(*) FROM matches WHERE tournament_id=?),
                     (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL),
                     is_published,lifecycle_status
                   FROM tournaments WHERE id=?""",
                (tournament_id,tournament_id,tournament_id),
            ).fetchone()
    except sqlite3.OperationalError:
        return None


def seed_completed_cup_fixture(tournament_id):
    """Prepare a deterministic completed cup for downstream browser checks.

    Cup creation and demo-data creation still happen through the real UI.
    Scheduling/result algorithms are covered by the normal regression suite;
    this fixture isolates browser navigation/rendering from scheduler timing.
    """
    with sqlite3.connect(DB) as con:
        con.row_factory=sqlite3.Row

        groups=con.execute(
            "SELECT id FROM groups WHERE tournament_id=? ORDER BY id",
            (tournament_id,),
        ).fetchall()
        teams=con.execute(
            "SELECT id,group_id FROM teams WHERE tournament_id=? ORDER BY id",
            (tournament_id,),
        ).fetchall()
        if len(groups) != 2 or len(teams) != 8:
            raise AssertionError(
                f"Fixture requires 2 groups/8 teams; got {len(groups)} groups/{len(teams)} teams"
            )

        # Ensure a complete round-robin group phase exists.
        existing=con.execute(
            "SELECT COUNT(*) FROM matches WHERE tournament_id=? AND stage='Gruppspel'",
            (tournament_id,),
        ).fetchone()[0]
        if existing == 0:
            match_no=1
            for group in groups:
                ids=[
                    int(row["id"]) for row in teams
                    if int(row["group_id"]) == int(group["id"])
                ]
                for i,home_id in enumerate(ids):
                    for away_id in ids[i+1:]:
                        con.execute(
                            """INSERT INTO matches(
                                 tournament_id,group_id,stage,round_no,match_no,
                                 home_source,away_source
                               ) VALUES(?,?,?,?,?,?,?)""",
                            (
                                tournament_id,int(group["id"]),"Gruppspel",1,match_no,
                                f"team:{home_id}",f"team:{away_id}",
                            ),
                        )
                        match_no+=1

        group_matches=con.execute(
            """SELECT id,home_source,away_source FROM matches
               WHERE tournament_id=? AND stage='Gruppspel'
               ORDER BY id""",
            (tournament_id,),
        ).fetchall()
        base=datetime(2026,8,26,9,0)
        for index,row in enumerate(group_matches):
            home_id=int(str(row["home_source"]).split(":")[1])
            away_id=int(str(row["away_source"]).split(":")[1])
            home_score=2 if index % 3 else 1
            away_score=0 if index % 2 else 1
            winner=home_id if home_score > away_score else (away_id if away_score > home_score else None)
            con.execute(
                """UPDATE matches
                   SET home_score=?,away_score=?,decided_winner_id=?,
                       scheduled_start=?,pitch_number=?,schedule_published=1
                   WHERE id=?""",
                (
                    home_score,away_score,winner,
                    (base+timedelta(minutes=35*index)).isoformat(timespec="minutes"),
                    1+(index % 4),int(row["id"]),
                ),
            )

        # Deterministic playoff fixture for real bracket rendering.
        con.execute(
            "DELETE FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL",
            (tournament_id,),
        )
        con.execute("DELETE FROM brackets WHERE tournament_id=?",(tournament_id,))
        bracket_id=con.execute(
            "INSERT INTO brackets(tournament_id,name,size,bronze_match) VALUES(?,?,?,?)",
            (tournament_id,"A-slutspel",4,0),
        ).lastrowid

        team_ids=[int(row["id"]) for row in teams[:4]]
        semi1=con.execute(
            """INSERT INTO matches(
                 tournament_id,bracket_id,stage,round_no,match_no,
                 home_source,away_source,home_score,away_score,decided_winner_id,
                 scheduled_start,pitch_number,schedule_published
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tournament_id,bracket_id,"Semifinal",1,1,
                f"team:{team_ids[0]}",f"team:{team_ids[1]}",2,0,team_ids[0],
                (base+timedelta(hours=8)).isoformat(timespec="minutes"),1,1,
            ),
        ).lastrowid
        semi2=con.execute(
            """INSERT INTO matches(
                 tournament_id,bracket_id,stage,round_no,match_no,
                 home_source,away_source,home_score,away_score,decided_winner_id,
                 scheduled_start,pitch_number,schedule_published
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tournament_id,bracket_id,"Semifinal",1,2,
                f"team:{team_ids[2]}",f"team:{team_ids[3]}",1,0,team_ids[2],
                (base+timedelta(hours=8)).isoformat(timespec="minutes"),2,1,
            ),
        ).lastrowid
        con.execute(
            """INSERT INTO matches(
                 tournament_id,bracket_id,stage,round_no,match_no,
                 home_source,away_source,home_score,away_score,decided_winner_id,
                 scheduled_start,pitch_number,schedule_published
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tournament_id,bracket_id,"Final",2,1,
                f"winner:{semi1}",f"winner:{semi2}",3,1,team_ids[0],
                (base+timedelta(hours=9)).isoformat(timespec="minutes"),1,1,
            ),
        )

        con.execute(
            """UPDATE tournaments
               SET is_published=1,lifecycle_status='completed',completed_at=?
               WHERE id=?""",
            (datetime.now().isoformat(timespec="seconds"),tournament_id),
        )
        con.commit()
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
        cup_name=f"E2E Full {browser_name}"
        tid=create_test_tournament_through_ui(page,cup_name)
        assert "TESTMILJÖ" in page.locator("body").inner_text()

        # 2. Classes → teams → groups → players/referees through the app's Testmiljö tool.
        demo_button=page.get_by_role("button",name=re.compile(r"^Skapa testdata:"))
        demo_button.wait_for(state="visible",timeout=20000)
        assert demo_button.is_enabled()
        demo_button.click()

        # In CUPNAVI_E2E mode the server auto-completes immediately once persisted
        # demo data exists. Do not wait for the Testnivå widget: that control is part
        # of the normal interactive test workflow, not the deterministic CI contract.
        demo_deadline=time.time()+30
        demo_counts=None
        while time.time()<demo_deadline:
            try:
                with sqlite3.connect(DB) as con:
                    demo_counts=con.execute(
                        """SELECT
                             (SELECT COUNT(*) FROM teams WHERE tournament_id=?),
                             (SELECT COUNT(*) FROM groups WHERE tournament_id=?),
                             (SELECT COUNT(*) FROM referees WHERE tournament_id=?)""",
                        (tid,tid,tid),
                    ).fetchone()
                if demo_counts and demo_counts[0] == 8 and demo_counts[1] == 2 and demo_counts[2] >= 1:
                    break
            except sqlite3.OperationalError:
                pass
            time.sleep(.2)
        else:
            raise AssertionError(f"Timed out waiting for persisted demo data; last counts={demo_counts}")

        # 3. Prepare a deterministic completed state for downstream browser
        # verification. The scheduler/result engine has its own regression coverage;
        # this browser journey verifies UI integration and public rendering.
        seed_completed_cup_fixture(tid)
        tid=assert_complete_database(cup_name)

        # 4. Public tournament view: use an explicit cup URL in a fresh browser
        # context. This verifies the real share/direct-link contract rather than
        # inheriting stale Admin session state after an out-of-process DB fixture.
        ctx.close()
        public_ctx=browser.new_context(viewport={"width":1280,"height":900})
        page=public_ctx.new_page()
        page.goto(f"{BASE}?cup={tid}&section=matches",wait_until="domcontentloaded")
        page.get_by_text(cup_name,exact=True).wait_for(state="visible",timeout=30000)
        wait_app(page)
        public_body=page.locator("body").inner_text()
        assert cup_name in public_body
        assert "This app has encountered an error" not in public_body
        assert "Traceback" not in public_body

        team_token,group_token=representative_public_tokens(tid)
        section_contracts = [
            ("Schema & resultat", team_token),
            ("Tabeller", group_token),
            ("Slutspel", "FINAL"),
            ("Statistik", "Skytteliga"),
            ("Cupinfo", "Cupens regler"),
        ]
        for label,expected_token in section_contracts:
            button=page.get_by_role("button",name=label,exact=True)
            button.wait_for(state="visible",timeout=15000)
            button.click()
            wait_app(page)
            assert_no_ui_error(page)
            current=page.locator("body").inner_text()
            assert expected_token and expected_token in current, (
                f"{label} rendered without its expected domain content: {expected_token!r}"
            )

        overflow=page.evaluate(
            "() => Math.max(0,document.documentElement.scrollWidth-document.documentElement.clientWidth)"
        )
        assert overflow <= 4

        # 5. Role boundary remains part of the lifecycle journey. The clean
        # Turneringsvy exposes only Turneringsvy + Admin; Admin expands the rest.
        page.get_by_role("button",name="Admin",exact=True).click()
        wait_app(page)
        page.get_by_role("button",name="Matchrapportör",exact=True).click()
        wait_app(page)
        page.get_by_label("Lösenord",exact=True).fill("123")
        page.get_by_role("button",name="Logga in",exact=True).click()
        wait_app(page)
        reporter_body=page.locator("body").inner_text()
        assert "endast testmiljöer" in reporter_body
        assert cup_name in reporter_body
        public_ctx.close()

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
        mobile_page.get_by_text(cup_name,exact=True).wait_for(state="visible",timeout=30000)
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

def test_active_tournament_switch_survives_browser_rerun(server):
    """Regression guard for the v1.197 active-tournament state bug."""
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        ctx=browser.new_context(viewport={"width":1280,"height":900})
        page=ctx.new_page()
        page.goto(BASE,wait_until="domcontentloaded")
        wait_app(page)
        page.get_by_role("button",name="Admin",exact=True).click()
        wait_app(page)

        suffix=str(int(time.time()*1000))[-7:]
        first=f"E2E Switch A {suffix}"
        second=f"E2E Switch B {suffix}"
        first_id=create_test_tournament_through_ui(page,first)
        second_id=create_test_tournament_through_ui(page,second)
        assert first_id != second_id

        choose_streamlit_option(page,"Aktiv turnering",first)
        wait_app(page)
        assert page.get_by_label("Aktiv turnering",exact=True).input_value() == first
        assert_no_ui_error(page)

        # A real browser reload must restore the deliberate selection through the
        # canonical cup query parameter, not snap back to the previously active cup.
        page.reload(wait_until="domcontentloaded")
        wait_app(page)
        selector=page.get_by_label("Aktiv turnering",exact=True)
        selector.wait_for(state="visible",timeout=20000)
        assert selector.input_value() == first
        assert_no_ui_error(page)

        ctx.close()
        browser.close()

