from pathlib import Path

def test_public_color_notice_rendering_is_removed():
    text = Path("app.py").read_text(encoding="utf-8")
    public_start = text.index("def render_public_view(")
    public_end = text.index("\ninit_db()", public_start)
    public = text[public_start:public_end]
    assert "Möjlig färglikhet:" not in public
    assert "färgkrock" not in public.lower()
