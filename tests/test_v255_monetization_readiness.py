import sqlite3

from cupnavi_core.billing import calculate_per_team_quote
from cupnavi_core.migrations import LATEST_SCHEMA_VERSION, apply_migrations


def test_per_team_quote_uses_minor_units_and_discount():
    quote = calculate_per_team_quote(billable_teams=40, unit_price_minor=2500, currency="sek", discount_minor=10000)
    assert quote.subtotal_minor == 100000
    assert quote.total_minor == 90000
    assert quote.currency == "SEK"


def test_discount_cannot_make_quote_negative():
    quote = calculate_per_team_quote(billable_teams=2, unit_price_minor=1000, currency="SEK", discount_minor=5000)
    assert quote.total_minor == 0


def test_v255_billing_schema_is_provider_neutral_and_free_by_default():
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY)")
    # Sparse fixture: mark earlier migrations as already applied so v24 can be tested alone.
    con.execute("CREATE TABLE cupnavi_schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)")
    con.execute("INSERT INTO cupnavi_schema_migrations VALUES(23,'fixture','now')")
    assert 24 in apply_migrations(con)
    cols = {r[1]: r for r in con.execute("PRAGMA table_info(tournament_billing)")}
    assert cols["billing_model"][4] == "'per_team'"
    assert cols["unit_price_minor"][4] == "0"
    assert cols["payment_status"][4] == "'not_required'"
    assert cols["payment_provider"][4] == "'none'"
    assert LATEST_SCHEMA_VERSION >= 24
