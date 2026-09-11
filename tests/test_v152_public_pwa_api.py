from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_public_api_is_read_only_even_when_admin_api_can_write():
    main=(ROOT/"cupnavi_api/main.py").read_text()
    assert '@app.get("/api/public/cups/{public_key}")' in main
    assert '@app.post("/api/public/' not in main
    assert '@app.put("/api/public/' not in main
    assert '@app.delete("/api/public/' not in main

def test_api_hides_unpublished_cups():
    repo=(ROOT/"cupnavi_api/repository.py").read_text()
    assert "is_published=1" in repo

def test_pwa_has_real_service_worker_and_manifest():
    assert (ROOT/"public_pwa/service-worker.js").exists()
    assert (ROOT/"public_pwa/manifest.webmanifest").exists()
    sw=(ROOT/"public_pwa/service-worker.js").read_text()
    assert 'self.addEventListener("fetch"' in sw
    assert 'caches.open' in sw

def test_pwa_persists_followed_team_locally():
    js=(ROOT/"public_pwa/app.js").read_text()
    assert "localStorage.setItem" in js
    assert "cupnavi:team:" in js

def test_pwa_table_is_api_backed_not_locally_guessed():
    js=(ROOT/"public_pwa/app.js").read_text()
    assert "fetchStandings" in js
    assert "Tabellberäkning flyttas till API:t i nästa steg" not in js

def test_api_dependencies_are_declared():
    req=(ROOT/"requirements.txt").read_text()
    assert "fastapi" in req and "uvicorn" in req
