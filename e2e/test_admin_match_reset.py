"""Confirm cup-wide reset through the real mobile admin UI, with an isolated API."""
import copy

import pytest
from playwright.sync_api import expect, sync_playwright
from e2e.test_mobile_pwa import BASE, next_server


class AdminResetAPI:
    def __init__(self):
        self.cup={'id':1,'name':'Reset Test Cup','role':'admin','public_slug':'reset-test','is_published':1,'admin_revision':1,'arrangement_type':'tournament_playoffs'}
        self.matches=[{'id':i,'stage':stage,'home_team':home,'away_team':away,'home_score':2,'away_score':1,
                       'status':'played','match_status':'finished','requires_winner':False}
                      for i,stage,home,away in [(10,'Gruppspel','Bromölla','Örebro SK'),(20,'Guldgruppen','AIK','Heming')]]
        self.calls=[]
        self.held=None
        self.fail=False
        self.event_loads=0

    def route(self,route):
        request=route.request
        path=request.url.split('onrender.com')[-1]
        if path == '/health':
            route.fulfill(json={'ok':True})
        elif path == '/api/admin/session':
            route.fulfill(json={'account':{'id':7,'email':'test@example.org'},'cups':[self.cup]})
        elif path.endswith('/cupinfo'):
            route.fulfill(json=self.cup)
        elif path.endswith('/schedule'):
            route.fulfill(json={'match_count':2,'scheduled_count':2,'pitch_count':1,'schedule_dirty':False,'conflict_analysis':{'error_count':0,'warning_count':0}})
        elif path.endswith('/rules'):
            route.fulfill(json={'rules_reviewed':True,'schedule_dirty':False})
        elif path.endswith('/reporting/reset-all'):
            self.calls.append(request.post_data_json)
            if self.fail:
                route.fulfill(status=503,json={'detail':'Tillfälligt serverfel. Försök igen.'})
            else:
                self.held=route
        elif path.endswith('/reporting/events'):
            self.event_loads+=1
            route.fulfill(json={'matches':[]})
        elif path.endswith('/reporting'):
            route.fulfill(json={'matches':copy.deepcopy(self.matches)})
        else:
            route.fulfill(json={'cups':[],'teams':[],'groups':[],'codes':[],'matches':[],'settings':{}})

    def complete(self):
        for match in self.matches:
            match.update(home_score=None,away_score=None,status='scheduled',match_status='not_started')
        self.held.fulfill(json={'reset_count':len(self.matches)})
        self.held=None


def open_admin(playwright,browser,device,api):
    context=browser.new_context(**playwright.devices[device])
    context.add_init_script("localStorage.setItem('cupnavi_admin_session_v629','fixture-admin');localStorage.setItem('cupnavi_admin_active_cup_v651','1');")
    page=context.new_page()
    page.route('https://cupnavi-api.onrender.com/**',api.route)
    page.goto(f'{BASE}/admin?cup=1#reporting',wait_until='networkidle')
    expect(page.get_by_role('button',name='Återställ alla matcher',exact=True)).to_be_enabled()
    return context,page


@pytest.mark.parametrize('device',['Pixel 7','iPhone 14'])
def test_all_matches_reset_requires_yes_and_refreshes_scores_and_events(next_server,device):
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch()
        api=AdminResetAPI()
        context,page=open_admin(playwright,browser,device,api)
        button=page.get_by_role('button',name='Återställ alla matcher',exact=True)
        button.click()
        dialog=page.get_by_role('dialog',name='Är du säker?')
        expect(dialog).to_be_visible()
        expect(dialog.get_by_text('Alla 2 matcher',exact=False)).to_be_visible()
        expect(dialog.get_by_role('button',name='Nej',exact=True)).to_be_focused()
        assert page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth + 4')
        page.keyboard.press('Escape')
        expect(dialog).not_to_be_visible()
        assert api.calls == []
        button.click()
        dialog.get_by_role('button',name='Nej',exact=True).click()
        expect(dialog).not_to_be_visible()
        assert api.calls == []
        button.click()
        dialog.get_by_role('button',name='Ja',exact=True).click()
        expect(dialog.get_by_role('button',name='Återställer…')).to_be_disabled()
        assert api.calls == [{'confirmed':True,'expected_match_count':2}]
        with page.expect_response(lambda response: response.url.endswith('/reporting/events')):
            api.complete()
        expect(dialog).not_to_be_visible()
        expect(page.get_by_text('Alla 2 matcher är återställda som ospelade.',exact=True)).to_be_visible()
        expect(page.locator('#reporting').get_by_label('Hemmamål',exact=True)).to_have_value('')
        expect(page.locator('#reporting').get_by_label('Bortamål',exact=True)).to_have_value('')
        expect(page.locator('#reporting').get_by_text('0/2 KLARA',exact=True)).to_be_visible()
        expect(page.locator('#match-events').get_by_text('Inga färdigspelade matcher ännu',exact=True)).to_be_visible()
        page.wait_for_function('() => !document.querySelector("dialog[open]")')
        assert len(api.calls) == 1 and api.event_loads >= 2
        context.close()
        browser.close()


def test_all_matches_reset_error_keeps_confirmation_and_existing_result(next_server):
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch()
        api=AdminResetAPI()
        api.fail=True
        context,page=open_admin(playwright,browser,'Pixel 7',api)
        page.get_by_role('button',name='Återställ alla matcher',exact=True).click()
        dialog=page.get_by_role('dialog',name='Är du säker?')
        dialog.get_by_role('button',name='Ja',exact=True).click()
        expect(dialog.get_by_role('alert')).to_contain_text('Tillfälligt serverfel')
        expect(dialog).to_be_visible()
        expect(dialog.get_by_role('button',name='Ja',exact=True)).to_be_enabled()
        expect(page.locator('#reporting').get_by_label('Hemmamål',exact=True)).to_have_value('2')
        expect(page.get_by_text('Alla 2 matcher är återställda som ospelade.',exact=True)).not_to_be_visible()
        dialog.get_by_role('button',name='Nej',exact=True).click()
        assert len(api.calls) == 1
        context.close()
        browser.close()
