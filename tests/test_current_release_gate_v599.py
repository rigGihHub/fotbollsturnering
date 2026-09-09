from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='2026.09.09-599-DESKTOP-DENSITY-KIT-SPOTLIGHT'

def test_version_synced():
    assert (ROOT/'VERSION.txt').read_text().strip()==VERSION
    assert f'APP_BUILD_VERSION = "{VERSION}"' in (ROOT/'app.py').read_text()
    assert f'APP_VERSION = "{VERSION}"' in (ROOT/'cupnavi_core'/'version.py').read_text()

def test_desktop_density_layer_is_last_design_override():
    app=(ROOT/'app.py').read_text()
    assert 'inject_v599_desktop_density()' in app
    assert app.rfind('inject_v599_desktop_density()') > app.rfind('inject_v571_design_system_2()')
    css=(ROOT/'cupnavi_core'/'style_system.py').read_text()
    assert 'max-width:min(1520px,calc(100vw - 300px))' in css
    assert '@media (min-width:1600px)' in css

def test_kit_feature_is_prominent_and_direct():
    app=(ROOT/'app.py').read_text()
    assert 'Tröjfärger · NYTT' in app
    assert 'NY FUNKTION · MATCHSTÄLL' in app
    assert 'Tröjfärger & färgkrockar' in app
    assert 'Öppna tröjfärger →' in app
    assert 'args=("Tröj setup",)' in app

def test_mobile_guard_preserved():
    css=(ROOT/'cupnavi_core'/'style_system.py').read_text()
    assert '@media(max-width:768px)' in css
    assert '.stApp .block-container{max-width:100vw!important}' in css
