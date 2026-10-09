"""Exercise the actual production reporter UI with an isolated, stateful API."""
import json
from datetime import datetime, timezone

from playwright.sync_api import expect, sync_playwright
from e2e.test_mobile_pwa import BASE, next_server, reporter_test_token


class ReporterAPI:
    def __init__(self, status='live'):
        self.matches = [self.match(10, 'Bromölla', 'Örebro SK', status), self.match(20, 'Andra hemma', 'Andra borta', 'not_started')]
        self.held = None
        self.hold_next_score = False
        self.fail_next_score = False
        self.lost_acknowledgement = False
        self.puts = []

    @staticmethod
    def match(match_id, home, away, status):
        return {'id': match_id, 'home_team': home, 'away_team': away, 'stage': 'Gruppspel', 'requires_winner': False,
                'home_score': 0, 'away_score': 0, 'home_penalties': None, 'away_penalties': None,
                'match_status': status, 'status': 'played' if status == 'finished' else status,
                'clock_elapsed_seconds': 16, 'clock_synced_at': datetime.now(timezone.utc).isoformat()}

    def route(self, route):
        request = route.request
        url = request.url
        if url.endswith('/health'):
            route.fulfill(json={'ok': True})
        elif url.endswith('/api/reporter/reporting'):
            route.fulfill(json={'cup': {'id': 1, 'name': 'Testcup', 'public_slug': 'testcup'}, 'matches': self.matches,
                                'settings': {'scorers': False, 'assists': False, 'cards': False, 'minutes_per_half': 20, 'halves': 2}})
        elif request.method == 'PUT':
            match_id = int(url.split('/matches/')[1].split('/')[0])
            match = next(m for m in self.matches if m['id'] == match_id)
            payload = request.post_data_json
            self.puts.append((match_id, payload))
            if url.endswith('/status'):
                if match['match_status'] != payload['expected_status']:
                    route.fulfill(status=409, json={'detail': 'Nyare matchstatus'})
                    return
                match['match_status'] = payload['status']
                match['status'] = 'played' if payload['status'] == 'finished' else payload['status']
                match['clock_synced_at'] = datetime.now(timezone.utc).isoformat()
            else:
                if self.fail_next_score:
                    self.fail_next_score = False
                    route.fulfill(status=503, json={'detail': 'Tillfälligt anslutningsfel'})
                    return
                if match['home_score'] != payload['expected_home_score'] or match['away_score'] != payload['expected_away_score']:
                    route.fulfill(status=409, json={'detail': 'Nyare serverresultat'})
                    return
                for field in ('home_score', 'away_score', 'home_penalties', 'away_penalties'):
                    match[field] = payload[field]
                if self.hold_next_score:
                    self.hold_next_score = False
                    self.held = (route, dict(match))
                    return
                if self.lost_acknowledgement:
                    self.lost_acknowledgement = False
                    route.abort('failed')
                    return
            route.fulfill(json=match)
        else:
            route.fulfill(json={'matches': []})


def open_reporter(context, api):
    context.add_init_script(f"if (!localStorage.getItem('cupnavi_reporter_session_v1')) localStorage.setItem('cupnavi_reporter_session_v1',{json.dumps(reporter_test_token())})")
    page = context.new_page()
    page.route('https://cupnavi-api.onrender.com/**', api.route)
    page.goto(BASE + '/reporter?cup=testcup', wait_until='networkidle')
    page.locator('.reporter-live__picker select').select_option('10')
    return page


def wait_saved(page):
    page.wait_for_function("() => JSON.parse(localStorage.getItem('cupnavi_reporter_queue_v1') || '[]').length === 0", timeout=20000)


def test_finished_match_correction_and_resume_on_mobile(next_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for device in ('Pixel 7', 'iPhone 14'):
            api = ReporterAPI('finished')
            context = browser.new_context(**p.devices[device])
            page = open_reporter(context, api)
            page.on('dialog', lambda dialog: dialog.accept())
            expect(page.locator('.reporter-live__clock strong')).to_have_text('00:16')
            page.get_by_role('button', name='Rätta slutresultat', exact=True).click()
            page.get_by_role('button', name='Öka mål för Bromölla', exact=True).click()
            page.get_by_role('button', name='Avsluta match', exact=True).click()
            wait_saved(page)
            assert api.matches[0]['home_score'] == 1
            assert api.matches[0]['match_status'] == 'finished'
            page.get_by_role('button', name='Återuppta match', exact=True).click()
            wait_saved(page)
            assert api.matches[0]['match_status'] == 'live'
            expect(page.get_by_role('button', name='Öka mål för Bromölla', exact=True)).to_be_enabled()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            context.close()
        browser.close()


def test_clicks_during_save_and_match_switch_are_preserved(next_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(**p.devices['Pixel 7'])
        api = ReporterAPI()
        page = open_reporter(context, api)
        api.hold_next_score = True
        page.get_by_role('button', name='Öka mål för Bromölla', exact=True).click()
        page.wait_for_function("() => document.querySelector('.reporter-network.is-syncing') !== null")
        # Wait for the PUT without blocking the browser's ability to accept more clicks.
        page.wait_for_timeout(1200)
        assert api.held is not None
        page.get_by_role('button', name='Öka mål för Bromölla', exact=True).click()
        page.get_by_role('button', name='Öka mål för Bromölla', exact=True).click()
        page.locator('.reporter-live__picker select').select_option('20')
        page.get_by_role('button', name='Starta match', exact=True).click()
        page.get_by_role('button', name='Öka mål för Andra hemma', exact=True).click()
        held, payload = api.held
        held.fulfill(json=payload)
        wait_saved(page)
        assert [m['home_score'] for m in api.matches] == [3, 1]
        expect(page.locator('.reporter-live__picker select')).to_have_value('20')
        page.reload(wait_until='networkidle')
        expect(page.locator('.reporter-live__picker select')).to_have_value('20')
        context.close()
        browser.close()


def test_offline_reload_then_reconnect_and_lost_acknowledgement(next_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(**p.devices['Pixel 7'], service_workers='allow')
        api = ReporterAPI('not_started')
        page = open_reporter(context, api)
        page.evaluate('() => navigator.serviceWorker.ready.then(() => true)')
        page.on('dialog', lambda dialog: dialog.accept())
        context.set_offline(True)
        page.get_by_role('button', name='Starta match', exact=True).click()
        page.get_by_role('button', name='Öka mål för Bromölla', exact=True).click()
        page.get_by_role('button', name='Öka mål för Bromölla', exact=True).click()
        page.get_by_role('button', name='Avsluta match', exact=True).click()
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('.reporter-live__picker select')).to_have_value('10')
        expect(page.locator('.reporter-live__status-actions')).to_contain_text('Slutresultat 2–0')
        api.lost_acknowledgement = True
        context.set_offline(False)
        wait_saved(page)
        assert api.matches[0]['match_status'] == 'finished'
        assert api.matches[0]['home_score'] == 2
        assert len([payload for match_id, payload in api.puts if match_id == 10 and 'home_score' in payload]) == 1
        context.close()
        browser.close()


def test_transient_server_failure_retries_without_losing_result(next_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(**p.devices['Pixel 7'])
        api = ReporterAPI()
        page = open_reporter(context, api)
        api.fail_next_score = True
        page.get_by_role('button', name='Öka mål för Bromölla', exact=True).click()
        wait_saved(page)
        assert api.matches[0]['home_score'] == 1
        assert len([payload for _, payload in api.puts if 'home_score' in payload]) == 2
        context.close()
        browser.close()


class EventAPI(ReporterAPI):
    def __init__(self):
        super().__init__()
        self.matches[1]['match_status'] = 'live'
        self.old_details = []
        self.cards = {10: 0, 20: 0}
        self.hold_event = False
        self.held_event = None

    def detail(self, match_id):
        match = next(m for m in self.matches if m['id'] == match_id)
        return {'match': {'id': match_id, 'home_team_name': match['home_team'], 'away_team_name': match['away_team'],
                          'home_score': match['home_score'], 'away_score': match['away_score'], 'match_status': match['match_status']},
                'enabled': {'assists': True, 'cards': True}, 'teams': [{'side': 'home', 'team_id': match_id,
                 'team_name': match['home_team'], 'team_score': match['home_score'], 'registered_goals': 0, 'registered_assists': 0,
                 'players': [{'id': match_id, 'name': f'Spelare {match_id}', 'goals': 0, 'assists': 0, 'yellow_cards': self.cards[match_id], 'red_cards': 0}]}]}

    def route(self, route):
        url = route.request.url
        if url.endswith('/api/reporter/reporting'):
            route.fulfill(json={'cup': {'id': 1, 'name': 'Testcup', 'public_slug': 'testcup'}, 'matches': self.matches,
                                'settings': {'scorers': True, 'assists': True, 'cards': True, 'minutes_per_half': 20, 'halves': 2}})
        elif url.endswith('/reporting/events'):
            route.fulfill(json={'matches': [{**m, 'home_team_name': m['home_team'], 'away_team_name': m['away_team']} for m in self.matches]})
        elif '/events' in url:
            match_id = int(url.split('/matches/')[1].split('/')[0])
            if route.request.method == 'GET':
                if match_id == 10:
                    self.old_details.append(route)
                else:
                    route.fulfill(json=self.detail(match_id))
            else:
                payload = route.request.post_data_json
                assert payload['expected']['yellow_cards'] == self.cards[match_id]
                self.cards[match_id] = payload['yellow_cards']
                if self.hold_event:
                    self.hold_event = False
                    self.held_event = (route, self.detail(match_id))
                else:
                    route.fulfill(json=self.detail(match_id))
        else:
            super().route(route)


def test_selected_match_events_ignore_late_responses_and_finish_after_pending_cards(next_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(**p.devices['Pixel 7'])
        api = EventAPI()
        # A held detail request intentionally prevents networkidle.
        context.add_init_script(f"localStorage.setItem('cupnavi_reporter_session_v1',{json.dumps(reporter_test_token())})")
        page = context.new_page()
        page.route('https://cupnavi-api.onrender.com/**', api.route)
        page.goto(BASE + '/reporter?cup=testcup', wait_until='domcontentloaded')
        page.wait_for_timeout(600)
        assert api.old_details
        page.locator('.reporter-live__picker select').select_option('20')
        expect(page.get_by_text('Spelare 20', exact=True)).to_be_visible()
        for route in api.old_details:
            route.fulfill(json=api.detail(10))
        expect(page.get_by_text('Spelare 20', exact=True)).to_be_visible()
        expect(page.get_by_text('Spelare 10', exact=True)).to_have_count(0)
        api.hold_event = True
        page.get_by_role('button', name='Öka Gult', exact=True).click()
        page.wait_for_timeout(1200)
        assert api.held_event is not None
        page.get_by_role('button', name='Öka Gult', exact=True).click()
        page.on('dialog', lambda dialog: dialog.accept())
        page.get_by_role('button', name='Avsluta match', exact=True).click()
        held, payload = api.held_event
        held.fulfill(json=payload)
        wait_saved(page)
        assert api.cards == {10: 0, 20: 2}
        assert api.matches[1]['match_status'] == 'finished'
        expect(page.get_by_text('Spelare 10', exact=True)).to_have_count(0)
        context.close()
        browser.close()
