"""Pure match-kit guidance for schedule/admin presentation."""

from __future__ import annotations


def build_kit_guidance(
    *,
    home_name: str,
    away_name: str,
    home_home_conflict: bool,
    away_kit_used: bool,
    unresolved_conflict: bool,
) -> dict[str, str | bool]:
    """Describe the safest practical kit choice without changing match data."""
    home_name = str(home_name or "Hemmalaget")
    away_name = str(away_name or "Bortalaget")

    if unresolved_conflict:
        return {
            "state": "conflict",
            "label": "Färgkrock kvar",
            "short": f"{away_name} behöver annat/extraställ",
            "detail": (
                f"{home_name}s hemmaställ ligger för nära både {away_name}s hemma- och bortaställ. "
                "Samordna ett annat/extraställ före matchen."
            ),
            "away_kit": "extra",
            "needs_action": True,
        }

    if home_home_conflict and away_kit_used:
        return {
            "state": "resolved",
            "label": "Krock löst",
            "short": f"{away_name} spelar i bortaställ",
            "detail": (
                f"Hemmaställen är för lika. CupNavi rekommenderar därför {away_name}s bortaställ."
            ),
            "away_kit": "away",
            "needs_action": False,
        }

    return {
        "state": "clear",
        "label": "Ställen fungerar",
        "short": "Ordinarie ställ",
        "detail": f"{home_name} och {away_name} kan använda ordinarie hemmaställ.",
        "away_kit": "home",
        "needs_action": False,
    }
