from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reporter_page_uses_dedicated_layout():
    source = (ROOT / "frontend-next/src/components/reporter-client.tsx").read_text()
    css = (ROOT / "frontend-next/src/app/reporter-v2665.css").read_text()
    assert 'className="reporter-page reporter-page--login"' in source
    assert 'className="reporter-match__body"' in source
    assert 'className="reporter-score"' in source
    assert '.reporter-match__body{display:grid' in css
    assert '@media(max-width:520px)' in css


def test_score_inputs_have_team_specific_labels():
    source = (ROOT / "frontend-next/src/components/reporter-client.tsx").read_text()
    assert 'aria-label={`Mål för ${m.home_team}`}' in source
    assert 'aria-label={`Mål för ${m.away_team}`}' in source
    assert 'Spara resultat' in source
