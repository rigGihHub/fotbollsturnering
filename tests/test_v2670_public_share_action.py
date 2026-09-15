from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_share_action_is_prominent_and_uses_clean_public_url():
    view = (ROOT / "frontend-next/src/components/PublicCupView.tsx").read_text()

    assert 'className="public-share-action"' in view
    assert 'className="public-share-action public-share-action--mobile"' in view
    assert "new URL(`/cup/${encodeURIComponent(publicKey)}`" in view


def test_old_share_card_is_not_duplicated_in_cup_info():
    view = (ROOT / "frontend-next/src/components/PublicCupView.tsx").read_text()

    assert '<span className="feature-card__number">DELA</span>' not in view
