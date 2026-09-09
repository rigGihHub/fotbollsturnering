import sqlite3
from pathlib import Path
from cupnavi_core.notification_service import token_hash, normalize_email, classify_notification, category_enabled
from cupnavi_core.migrations import ensure_v21_schema_compat

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
FOLLOW_VIEW=(ROOT/"cupnavi_core"/"public_team_follow_view.py").read_text(encoding="utf-8")

def test_v21_schema_has_verified_subscriptions_and_delivery_log():
    con=sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY)")
    con.execute("CREATE TABLE teams(id INTEGER PRIMARY KEY)")
    ensure_v21_schema_compat(con)
    tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"notification_subscriptions","notification_deliveries"} <= tables

def test_notification_tokens_are_hashed_and_email_normalized():
    assert token_hash("secret") != "secret"
    assert normalize_email(" Test@Example.COM ") == "test@example.com"

def test_notification_category_classification():
    assert classify_notification("Nytt resultat")=="results"
    assert classify_notification("Matchen har flyttats")=="schedule"
    assert classify_notification("Viktig information")=="messages"

def test_public_follow_has_verified_email_optin():
    assert "Få viktiga lagnotiser via e-post" in FOLLOW_VIEW
    assert "Skicka verifieringsmejl" in FOLLOW_VIEW
    assert "confirm_notification_subscription" in APP
    assert "unsubscribe_notification_subscription" in APP

def test_notification_is_persisted_before_email_delivery():
    block=APP[APP.index("def add_team_notification"):APP.index("def _match_team_ids")]
    assert block.index('INSERT INTO notifications') < block.index("_deliver_team_notification_emails")

def test_pwa_manifest_scaffold_exists_without_fake_webpush_claim():
    assert (ROOT/"static/manifest.webmanifest").exists()
    doc=(ROOT/"PWA_NOTIFICATIONS_V151.md").read_text()
    assert "Full browser Web Push is not enabled" in doc
