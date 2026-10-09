"""Public homepage filters, deep links and failure recovery on mobile."""
import pytest
from playwright.sync_api import expect, sync_playwright
from e2e.test_mobile_pwa import BASE, next_server


CUPS = [
    {"id": 1, "name": "Pågående matchcamp", "public_slug": "current-camp", "start_date": "2026-10-09", "end_date": "2026-10-10", "status": "ongoing", "arrangement_type": "matchcamp", "arena_address": "Sörbyvallen"},
    {"id": 46, "name": "Slottskampen 2026", "public_slug": "slottskampen-2026-2", "start_date": "2026-10-24", "end_date": "2026-10-24", "status": "upcoming", "arrangement_type": "tournament_playoffs", "arena_address": None},
    {"id": 3, "name": "Avslutad cup", "public_slug": None, "start_date": "2026-09-01", "end_date": "2026-09-01", "status": "completed", "arrangement_type": "tournament", "arena_address": None},
]


@pytest.mark.parametrize("device", ["Pixel 7", "iPhone 14"])
def test_public_directory_filters_links_and_mobile_layout(next_server, device):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(**playwright.devices[device])
        page = context.new_page()
        page.route("**/api/public/cups", lambda route: route.fulfill(json={"cups": CUPS, "as_of": "2026-10-09"}))
        page.goto(BASE, wait_until="networkidle")
        page.get_by_role("link", name="Hitta en cup").click()
        directory = page.locator("#public-cups")
        expect(directory.get_by_role("link", name="Öppna Pågående matchcamp")).to_have_attribute("href", "/cup/current-camp")
        directory.get_by_role("button", name="Kommande 1").click()
        expect(directory.get_by_role("link", name="Öppna Slottskampen 2026")).to_have_attribute("href", "/cup/slottskampen-2026-2")
        expect(directory.get_by_role("link", name="Öppna Pågående matchcamp")).not_to_be_visible()
        directory.get_by_role("button", name="Avslutade 1").click()
        link = directory.get_by_role("link", name="Öppna Avslutad cup")
        expect(link).to_have_attribute("href", "/cup/3")
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 4")
        page.route("**/cup/3", lambda route: route.fulfill(content_type="text/html", body="<h1>Avslutad cup</h1>"))
        link.click()
        expect(page).to_have_url(f"{BASE}/cup/3")
        context.close()
        browser.close()


def test_directory_error_retry_and_empty_category(next_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.route("**/api/public/cups", lambda route: route.fulfill(status=503, json={"detail": "Unavailable"}))
        page.goto(BASE)
        directory = page.locator("#public-cups")
        expect(directory.get_by_role("alert")).to_contain_text("Det gick inte att hämta", timeout=20000)
        expect(directory.get_by_role("button", name="Pågående", exact=False)).not_to_be_visible()
        page.unroute("**/api/public/cups")
        page.route("**/api/public/cups", lambda route: route.fulfill(json={"cups": [CUPS[1]], "as_of": "2026-10-09"}))
        directory.get_by_role("button", name="Försök igen").click()
        expect(directory.get_by_role("button", name="Kommande 1")).to_have_attribute("aria-pressed", "true")
        expect(directory.get_by_role("link", name="Öppna Slottskampen 2026")).to_be_visible()
        directory.get_by_role("button", name="Pågående 0").click()
        expect(directory.get_by_text("Inga publicerade matchcamper eller cuper pågår just nu.")).to_be_visible()
        browser.close()
