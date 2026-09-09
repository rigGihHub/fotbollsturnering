from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
P=(ROOT/'cupnavi_core'/'public_presentation_view.py').read_text(encoding='utf-8')
VERSION='2026.09.09-598-TEXTTV-TABLE-KIT-DISCOVERY'
def test_release_identity():
    assert VERSION in APP
    assert (ROOT/'VERSION.txt').read_text().strip()==VERSION
    assert VERSION in (ROOT/'cupnavi_core'/'version.py').read_text()
def test_startup_version_contract():
    f=ROOT/'cupnavi_core'/'version.py'; spec=importlib.util.spec_from_file_location('v598',f); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); assert m.release_ui_label(m.APP_VERSION)==f'CupNavi {VERSION}'
def test_texttv_is_full_black_data_surface():
    assert 'background:#020402!important' in P
    assert 'background:#020402!important;\n          white-space:nowrap' in P
    assert 'TABELL · LIVE STÄLLNING' in P
    assert 'border:0;' in P and 'qualifier' in P
def test_texttv_keeps_accessible_headers_and_color_not_alone():
    assert '<th>Pl</th><th>Lag</th><th>S</th><th>V</th><th>O</th><th>F</th>' in P
    assert 'Qualification is communicated with accent + label, never colour alone.' in P
def test_kit_feature_is_promoted():
    assert '👕 Tröjfärger · NYTT' in APP
    assert 'Öppna tröjfärger →' in APP
    assert '👕 Tröjfärger & matchställ' in APP
    assert 'upptäcka färgkrockar' in APP
def test_kit_workflow_still_requires_confirmation():
    assert 'Inget sparas förrän du godkänner' in APP
    assert 'Scanna nätet för alla lag' in APP
