from pathlib import Path

def test_match_results_use_autosave():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'st.button("Spara alla resultat"' not in text
    assert "Resultat och ändringar sparas automatiskt" in text
    assert "auto_updates" in text

def test_partial_score_is_not_silently_saved():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "(home_score is None) != (away_score is None)" in text
    assert "fyll i båda målresultaten så sparas det automatiskt" in text
