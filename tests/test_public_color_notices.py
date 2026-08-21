from pathlib import Path

def test_public_color_notice_rendering_is_removed():
    text=Path("app.py").read_text(encoding="utf-8")
    assert "ℹ Möjlig färglikhet: om färgerna upplevs som för lika kan ett extraställ behövas." not in text
    assert "använder sitt bortaställ för att skapa tydligare färgskillnad.</div>" not in text
    assert "# Färgnotiser visas inte i den publika turneringsvyn." in text
