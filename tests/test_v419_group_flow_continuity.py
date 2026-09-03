from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_groups_page_keeps_guided_planning_context():
    block = APP[APP.index('if admin_page == "Grupper":'):APP.index('if admin_page == "Trupper":')]
    assert 'Planeringsflöde · Tävlingsstruktur' in block
    assert '["Grundsetup", "Lag", "Grupper", "Schema", "Kontroll", "Publicera"]' in block
    assert '← Till Lag' in block
    assert 'Nästa steg: Schema' in block


def test_groups_page_does_not_push_automatic_grouping_as_primary_path():
    block = APP[APP.index('if admin_page == "Grupper":'):APP.index('if admin_page == "Trupper":')]
    assert 'Förslag från CupNavi · valfritt' in block
    assert 'CupNavis förslag är frivilligt' in block
    auto = block[block.index('"Använd CupNavis gruppindelning"'):]
    assert 'type="secondary"' in auto[:250]
    assert 'snabbaste vägen vidare' not in block
