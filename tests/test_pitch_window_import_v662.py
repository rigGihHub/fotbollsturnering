from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pitch_window_import_backend_is_registered():
    routes = (ROOT / "cupnavi_api" / "competition_admin_routes.py").read_text(encoding="utf-8")
    repository = (ROOT / "cupnavi_api" / "pitch_window_import_repository.py").read_text(encoding="utf-8")
    api = (ROOT / "cupnavi_api" / "pitch_window_import_routes.py").read_text(encoding="utf-8")

    assert "register_pitch_window_import_routes" in routes
    assert "/import/pitch-windows" in api
    assert "CupNavi gissar inte vilken dag" in repository
    assert "ON CONFLICT(tournament_id,pitch_number,play_date)" in repository
    assert "confirmed=1" in repository


def test_pitch_window_import_is_visible_in_next_admin():
    page = (ROOT / "frontend-next" / "src" / "components" / "admin-lazy-extras.tsx").read_text(encoding="utf-8")
    component = (ROOT / "frontend-next" / "src" / "components" / "pitch-window-import-review.tsx").read_text(encoding="utf-8")

    assert "PitchWindowImportReview" in page
    assert "Bekräfta när planerna är öppna" in component
    assert "Spara granskade plantider" in component
    assert "CupNavi chansar" in component
