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


def wait_for_public_cup(page, cup_name, timeout_ms=60000):
    """Wait for the actual public cup hero and fail with useful UI diagnostics."""
    wait_app(page)
    title=page.locator(".cup-hero .title")
    deadline=time.time() + timeout_ms / 1000
    last_body=""
    while time.time() < deadline:
        try:
            if title.count() and title.first.is_visible():
                value=title.first.inner_text().strip()
                if value == cup_name:
                    assert_no_ui_error(page)
                    return
        except Exception:
            pass
        try:
            last_body=page.locator("body").inner_text()
            if "This app has encountered an error" in last_body or "Traceback" in last_body:
                raise AssertionError(f"Public cup render failed: {last_body[-2500:]}")
            if "Ingen turnering är publicerad ännu." in last_body:
                # The E2E fixture writes directly to SQLite outside Streamlit. A newly
                # opened browser can briefly receive a render started before that commit
                # became visible to the server session. Retry the real direct URL instead
                # of accepting the empty state; the exact cup hero is still mandatory.
                page.reload(wait_until="domcontentloaded", timeout=60000)
                wait_app(page)
                title=page.locator(".cup-hero .title")
                continue
        except AssertionError:
            raise
        except Exception:
            pass
        page.wait_for_timeout(250)
    raise AssertionError(
        f"Timed out waiting for public cup hero {cup_name!r}. "
        f"URL={page.url!r}. Last body={last_body[-2500:]}"
    )


def _ensure_create_tournament_expander_open(page):
    """Return the creation form without accidentally toggling its expander closed."""
    sidebar=page.locator('[data-testid="stSidebar"]')
    expander=sidebar.locator("details").filter(has_text="Skapa ny turnering").first
    expander.wait_for(state="attached",timeout=10000)

    # Streamlit expanders are native <details>. The old helper clicked the title
    # unconditionally, so the second create attempt could close the already-open
    # expander and leave its animation layer intercepting the submit button.
    if expander.get_attribute("open") is None:
        summary=expander.locator("summary").first
        summary.click(force=True)
        deadline=time.time()+10
        while time.time() < deadline and expander.get_attribute("open") is None:
            page.wait_for_timeout(100)
        assert expander.get_attribute("open") is not None, "Create tournament expander did not open"

    create_form=expander.locator('[data-testid="stForm"]').first
    create_form.wait_for(state="visible",timeout=10000)
    return create_form


def _persisted_tournament_row(cup_name):
    try:
        with sqlite3.connect(DB) as con:
            return con.execute(
                "SELECT id,environment_type FROM tournaments WHERE name=? ORDER BY id DESC LIMIT 1",
                (cup_name,),
            ).fetchone()
    except sqlite3.OperationalError:
        return None


def _submit_create_tournament_form(page, cup_name, attempts=2):
    """Submit Streamlit's create form and prove that the click was accepted.

    `Locator.click(force=True)` can report success even when Streamlit's rerendering
    layer swallows the React button event. Trigger the real DOM click instead, then
    wait for either persistence or the post-create UI. Retry only when neither signal
    appears.
    """
    last_body=""
    for attempt in range(attempts):
        create_form=_ensure_create_tournament_expander_open(page)
        name_input=create_form.get_by_label("Namn",exact=True)
        place_input=create_form.get_by_label("Spelort",exact=True)

        # A rerun may have replaced the form after the caller originally filled it.
        if name_input.input_value() != cup_name:
            name_input.fill(cup_name)
        if place_input.input_value() != "Örebro":
            place_input.fill("Örebro")

        test_environment=create_form.get_by_role("radio",name="Testmiljö",exact=True)
        test_environment.wait_for(state="attached",timeout=10000)
        assert test_environment.is_checked(), "CUPNAVI_E2E must preselect Testmiljö"

        submit=create_form.get_by_role("button",name="Skapa",exact=True)
        submit.wait_for(state="visible",timeout=10000)
        assert submit.is_enabled()
        page.wait_for_timeout(250)

        # DOM click avoids pointer-interception/animation races while still invoking
        # Streamlit/React's actual onClick handler. Reacquire the button every attempt.
        submit.evaluate("el => el.click()")

        deadline=time.time()+4
        while time.time() < deadline:
            row=_persisted_tournament_row(cup_name)
            if row is not None:
                return row
            try:
                if page.get_by_role("button",name="Fortsätt till Admin",exact=True).count():
                    # The UI accepted the submit; allow the DB commit a little longer.
                    return wait_for_persisted_tournament(cup_name,timeout_ms=12000)
                last_body=page.locator("body").inner_text()
                if "This app has encountered an error" in last_body or "Traceback" in last_body:
                    raise AssertionError(f"Create tournament UI failed: {last_body[-2500:]}")
            except AssertionError:
                raise
            except Exception:
                pass
            page.wait_for_timeout(150)

        # No persistence and no post-create UI: this was a swallowed submit event.
        # Reopen/reacquire the form and retry once rather than extending a useless DB wait.
        if attempt + 1 < attempts:
            page.wait_for_timeout(350)

    raise AssertionError(
        f"Create tournament submit was not accepted for {cup_name!r}; body={last_body[-1800:]}"
    )


def wait_for_persisted_tournament(cup_name, timeout_ms=20000):
    """Wait for Streamlit form submission to become visible in SQLite.

    The browser rerender and the committed DB write are separate observable events;
    do not assume a fixed sleep means persistence has completed on every browser.
    """
    deadline=time.time() + timeout_ms / 1000
    last_row=None
    while time.time() < deadline:
        try:
            with sqlite3.connect(DB) as con:
                last_row=con.execute(
                    "SELECT id,environment_type FROM tournaments WHERE name=? ORDER BY id DESC LIMIT 1",
                    (cup_name,),
                ).fetchone()
            if last_row is not None:
                return last_row
        except sqlite3.OperationalError:
            pass
        time.sleep(.15)
    raise AssertionError(
        f"Timed out waiting for persisted tournament {cup_name!r}; last_row={last_row!r}"
    )


def create_test_tournament_through_ui(page, cup_name):
    """Create a persisted Testmiljö using the real Streamlit UI and return its id."""
    create_form=_ensure_create_tournament_expander_open(page)
    create_form.get_by_label("Namn",exact=True).fill(cup_name)
    create_form.get_by_label("Spelort",exact=True).fill("Örebro")
    test_environment=create_form.get_by_role("radio",name="Testmiljö",exact=True)
    test_environment.wait_for(state="attached",timeout=10000)
    assert test_environment.is_checked(), "CUPNAVI_E2E must preselect Testmiljö"

    row=_submit_create_tournament_form(page,cup_name)
    wait_app(page)
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

    Streamlit selectbox is not a native <select>. React-Aria may omit the currently
    selected item from the popup options, so selecting the already-active value must
    be a no-op rather than waiting for an option that is not rendered.
    """
    combo=wait_until_enabled(page.get_by_label(label,exact=True),timeout=timeout)
    if combo.input_value().strip() == option:
        return

    # The widget may be replaced by a Streamlit rerun between lookup and click.
    # Reacquire it and retry opening the popup instead of assuming one click is enough.
    choice=None
    deadline=time.time()+timeout/1000
    while time.time()<deadline:
        combo=wait_until_enabled(page.get_by_label(label,exact=True),timeout=min(5000,timeout))
        if combo.input_value().strip() == option:
            return
        try:
            combo.click(force=True)
        except Exception:
            time.sleep(.15)
            continue

        # Streamlit has used both React-Aria and BaseWeb markup. Search by the
        # semantic option role first, then by exact visible text in an open popup.
        semantic=page.get_by_role("option",name=option,exact=True)
        if semantic.count() and semantic.first.is_visible():
            choice=semantic.first
            break
        popup_text=page.locator('[role="listbox"], [data-baseweb="popover"], [data-baseweb="menu"]').get_by_text(option,exact=True)
        if popup_text.count() and popup_text.last.is_visible():
            choice=popup_text.last
            break
        time.sleep(.2)

    if choice is None:
        raise AssertionError(f"Could not open {label!r} and find option {option!r}")
    choice.click()

    # Streamlit rerenders the widget after selection, so reacquire by label while
    # waiting for the persisted UI value rather than holding the pre-rerun locator.
    page.wait_for_function(
        "([label, expected]) => { const el=[...document.querySelectorAll('[aria-label]')].find(x => x.getAttribute('aria-label')===label && !x.disabled); return !!el && (el.value || '').trim()===expected; }",
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
               SET is_published=1,
                   lifecycle_status='completed',
                   completed_at=?,
                   playoff_format='A- och B-slutspel',
                   playoff_model_confirmed=1
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
        # Testverktyg is intentionally collapsed in the production UX; open the real
        # expander explicitly rather than relying on a formerly always-visible button.
        test_tools=page.locator("details").filter(has_text="Testverktyg").first
        test_tools.wait_for(state="attached",timeout=20000)
        if test_tools.get_attribute("open") is None:
            test_tools.locator("summary").first.click(force=True)
            page.wait_for_function(
                "el => el.hasAttribute('open')",
                arg=test_tools.element_handle(),
                timeout=10000,
            )
        demo_button=test_tools.get_by_role("button",name=re.compile(r"^Skapa testdata:"))
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
        page.goto(f"{BASE}?cup={tid}&section=matches",wait_until="domcontentloaded",timeout=60000)
        wait_for_public_cup(page,cup_name)
        public_body=page.locator("body").inner_text()
        assert cup_name in public_body
        assert "This app has encountered an error" not in public_body
        assert "Traceback" not in public_body

        team_token,group_token=representative_public_tokens(tid)
        section_contracts = [
            ("Schema & resultat", "matches", team_token),
            ("Tabeller", "tables", group_token),
            ("Slutspel", "playoffs", "FINAL"),
            ("Statistik", "stats", "Skytteliga"),
            ("Cupinfo", "info", "Cupens regler"),
        ]
        for label,section,expected_token in section_contracts:
            button=page.get_by_role("button",name=label,exact=True)
            button.wait_for(state="visible",timeout=15000)
            button.click()
            # Public navigation is made of real links. wait_app() can otherwise
            # return against the old Streamlit DOM before the URL navigation has
            # committed, which made the cross-browser journey assert stale content.
            page.wait_for_url(re.compile(rf"[?&]section={re.escape(section)}(?:&|$)"),timeout=20000)
            wait_for_public_cup(page,cup_name)
            assert_no_ui_error(page)
            page.get_by_text(expected_token,exact=False).first.wait_for(state="visible",timeout=20000)
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
        page.get_by_label("Kod",exact=True).fill("123")
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

        # Creating the second tournament must not silently overwrite an already-valid
        # deliberate selector state. To test the actual switch regression, first move
        # to B and then explicitly back to A.
        choose_streamlit_option(page,"Aktiv turnering",second)
        wait_app(page)
        assert page.get_by_label("Aktiv turnering",exact=True).input_value() == second
        assert_no_ui_error(page)

        choose_streamlit_option(page,"Aktiv turnering",first)
        wait_app(page)
        assert page.get_by_label("Aktiv turnering",exact=True).input_value() == first
        assert_no_ui_error(page)

        # A real browser reload must restore the deliberate A selection through the
        # canonical cup query parameter, not snap back to B or another preferred cup.
        page.reload(wait_until="domcontentloaded")
        wait_app(page)
        selector=page.get_by_label("Aktiv turnering",exact=True)
        selector.wait_for(state="visible",timeout=20000)
        assert selector.input_value() == first
        assert_no_ui_error(page)

        ctx.close()
        browser.close()

