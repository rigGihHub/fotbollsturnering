from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_role_links_can_be_copied_with_cup_and_identity():
    reporter = (ROOT / "frontend-next/src/components/role-code-admin.tsx").read_text()
    assert "navigator.clipboard.writeText" in reporter
    assert "Kopiera inloggningslänk" in reporter


def test_reporter_login_needs_only_the_code():
    source = (ROOT / "frontend-next/src/components/reporter-client.tsx").read_text()
    assert "Cupens länk eller ID" not in source
    assert "JSON.stringify({code})" in source
    assert "Koden gäller i högst 3 dygn" in source


def test_reporter_can_roundtrip_to_public_view():
    reporter = (ROOT / "frontend-next/src/components/reporter-client.tsx").read_text()
    public = (ROOT / "frontend-next/src/components/PublicCupView.tsx").read_text()
    page = (ROOT / "frontend-next/src/app/cup/[publicKey]/page.tsx").read_text()
    assert "?from=reporter" in reporter
    assert "Till matchrapportering" in public
    assert 'reporterReturn={query.from==="reporter"}' in page


def test_match_events_have_dedicated_layout():
    source = (ROOT / "frontend-next/src/components/reporter-match-events.tsx").read_text()
    css = (ROOT / "frontend-next/src/app/reporter-flow-v2667.css").read_text()
    assert "reporter-events__teams" in source
    assert "reporter-event-team" in source
    assert "reporter-counter" in source
    assert ".reporter-events__teams" in css
