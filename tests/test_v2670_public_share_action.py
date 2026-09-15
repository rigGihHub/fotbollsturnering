from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_share_action_is_prominent_in_global_header():
    action = (ROOT / "frontend-next/src/components/HeaderShareAction.tsx").read_text()
    layout = (ROOT / "frontend-next/src/app/layout.tsx").read_text()

    assert 'className="header-share-action"' in action
    assert 'pathname.startsWith("/cup/")' in action
    assert "new URL(pathname,window.location.origin)" in action
    assert "<HeaderShareAction />" in layout


def test_old_share_card_is_not_duplicated_in_cup_info():
    view = (ROOT / "frontend-next/src/components/PublicCupView.tsx").read_text()

    assert '<span className="feature-card__number">DELA</span>' not in view
