import os
from pathlib import Path
from cupnavi_api import repository

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/"public_pwa/app.js").read_text()
CSS=(ROOT/"public_pwa/styles.css").read_text()
REPO=(ROOT/"cupnavi_api/repository.py").read_text()

def test_api_uses_same_turso_env_names_as_streamlit():
    assert "TURSO_DATABASE_URL" in REPO
    assert "TURSO_AUTH_TOKEN" in REPO
    assert "libsql.connect" in REPO

def test_backend_name_falls_back_to_sqlite(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL",raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN",raising=False)
    assert repository.backend_name()=="sqlite"

def test_public_tournament_is_allowlisted_not_select_star_payload():
    row={"id":1,"name":"Cup","is_published":1,"admin_code":"SECRET","feedback_email":"public@example.com"}
    projected=repository._public_tournament_projection(row)
    assert projected["name"]=="Cup"
    assert "admin_code" not in projected

def test_cors_is_environment_configurable():
    main=(ROOT/"cupnavi_api/main.py").read_text()
    assert "CUPNAVI_PWA_ORIGINS" in main

def test_pwa_has_cupday_visual_features():
    assert "renderLiveCenter" in JS
    assert "Vägbeskrivning" in JS
    assert "updateConnection" in JS
    assert ".live-center" in CSS
    assert ".match-card" in CSS

def test_pwa_uses_existing_brand_asset_when_available():
    assert (ROOT/"public_pwa/cupnavi_logo.png").exists()

def test_api_health_reports_backend_without_secrets():
    main=(ROOT/"cupnavi_api/main.py").read_text()
    assert '"database_backend":backend_name()' in main
    assert "TURSO_AUTH_TOKEN" not in main
