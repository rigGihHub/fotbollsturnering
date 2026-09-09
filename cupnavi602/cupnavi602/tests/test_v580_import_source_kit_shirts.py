from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VER = (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')


def test_version():
    assert '580-IMPORT-SOURCE-AND-KIT-SHIRTS' in VER


def test_kit_preview_uses_shirt_silhouette_not_rectangle_swatch():
    assert 'def _kit_shirt_svg' in APP
    assert 'shirt_path = "M17 8 L23 4' in APP
    assert "<path d='{shirt_path}'" in APP
    old = "width:58px;height:32px;border:1px solid #64748b;border-radius:7px;background:"
    assert old not in APP


def test_table_swatch_reuses_shirt_svg():
    assert 'svg = _kit_shirt_svg(kit_pattern(team_row, kit), c1, c2, width=40, height=36)' in APP


def test_shirt_supports_all_current_patterns():
    for pattern in ['Vertikala ränder', 'Horisontella ränder', 'Rutigt', 'Delad']:
        assert pattern in APP


def test_admin_overview_keeps_initial_import_available():
    assert '📦 Importerat underlag ·' in APP
    assert 'originalunderlaget från den första foto/PDF-importen' in APP
    assert 'Granska {_row[\'label\']} →' in APP
    assert 'Inget skrivs över automatiskt' in APP
