"""Payment-provider-neutral monetization primitives.

No checkout or payment collection is enabled here. The module only defines the
stable billing vocabulary CupNavi can use when monetization is activated later.
Money is always represented in minor units (ore/cents/pence) to avoid floats.
"""

from dataclasses import dataclass

BILLING_MODEL_PER_TEAM = "per_team"
DEFAULT_BILLING_MODEL = BILLING_MODEL_PER_TEAM
DEFAULT_CURRENCY = "SEK"
DEFAULT_UNIT_PRICE_MINOR = 0  # Monetization is intentionally disabled for now.


@dataclass(frozen=True)
class BillingQuote:
    billable_teams: int
    unit_price_minor: int
    currency: str
    discount_minor: int
    subtotal_minor: int
    total_minor: int


def calculate_per_team_quote(*, billable_teams: int, unit_price_minor: int, currency: str, discount_minor: int = 0) -> BillingQuote:
    """Return an immutable per-team quote using integer minor currency units."""
    teams = int(billable_teams)
    price = int(unit_price_minor)
    discount = int(discount_minor)
    code = str(currency or "").strip().upper()
    if teams < 0 or price < 0 or discount < 0:
        raise ValueError("Billing amounts and team counts cannot be negative")
    if len(code) != 3 or not code.isalpha():
        raise ValueError("currency must be a three-letter ISO-style code")
    subtotal = teams * price
    total = max(0, subtotal - discount)
    return BillingQuote(teams, price, code, discount, subtotal, total)
