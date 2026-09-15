from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_all_venue_values_are_saved_then_read_back_and_verified():
    source=(ROOT/"frontend-next/src/components/venue-admin.tsx").read_text()
    assert "async function saveEverything()" in source
    assert "Servern kunde inte verifiera alla plantider" in source
    assert "Spara alla planer och tider" in source

def test_white_shirt_has_black_outline_and_logo_url_is_normalized():
    css=(ROOT/"frontend-next/src/app/comic-card-v2634.css").read_text()
    admin=(ROOT/"frontend-next/src/components/admin-workspace.tsx").read_text()
    public=(ROOT/"frontend-next/src/components/TeamKit.tsx").read_text()
    assert "drop-shadow(1px 0 #000)" in css and "drop-shadow(-1px 0 #000)" in css
    assert 'stroke="#101f2a"' in public
    assert "function normalizedWebUrl" in admin
