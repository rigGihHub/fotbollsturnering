# CupNavi v1.255 – Monetization readiness

This release prepares the data layer for a future low-cost per-team business model without enabling payments or changing the current UI.

- Provider-neutral `tournament_billing` table.
- Prices stored in minor currency units; no floating-point money.
- Per-team billing, currency, discounts, quote snapshots and payment status are representable.
- External provider identifiers are optional and do not couple CupNavi to Stripe or another provider.
- Defaults keep every existing tournament free (`unit_price_minor=0`, `payment_status=not_required`, `payment_provider=none`).
- No checkout, paywall, publication restriction or billing UI has been activated.

This intentionally keeps monetization dormant until product/market readiness justifies switching it on.
