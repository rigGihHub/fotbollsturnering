from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
RESULTS_VIEW = (ROOT / "cupnavi_core" / "admin_results_view.py").read_text(encoding="utf-8")


def test_match_results_use_autosave():
    assert 'st.button("Spara alla resultat"' not in RESULTS_VIEW
    assert "Ändringar sparas automatiskt" in RESULTS_VIEW
    assert "auto_updates" in RESULTS_VIEW
    assert "save_result_updates=_save_admin_result_updates" in APP


def test_partial_score_is_not_silently_saved():
    assert "(home_score is None) != (away_score is None)" in RESULTS_VIEW
    assert "fyll i båda målresultaten så sparas det automatiskt" in RESULTS_VIEW
