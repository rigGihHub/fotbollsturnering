from pathlib import Path
VERSION="2026.09.09-600-PUBLIC-SHELL-MILESTONE"
ROOT=Path(__file__).resolve().parents[1]

def test_version_synced():
    assert ROOT.joinpath("VERSION.txt").read_text().strip()==VERSION
    assert VERSION in ROOT.joinpath("cupnavi_core/version.py").read_text()
    assert VERSION in ROOT.joinpath("app.py").read_text()

def test_v600_shell_injected_after_v599():
    app=ROOT.joinpath("app.py").read_text()
    assert "inject_v600_public_shell_milestone()" in app
    assert app.rfind("inject_v600_public_shell_milestone()") > app.rfind("inject_v599_desktop_density()")

def test_public_shell_visual_contract():
    css=ROOT.joinpath("cupnavi_core/style_system.py").read_text()
    for token in ["--cn600-navy", ".cup-hero", ".cn-public-top-nav", "#071521"]:
        assert token in css

def test_kit_discovery_preserved():
    css=ROOT.joinpath("cupnavi_core/style_system.py").read_text()
    assert ".cn-kit-discovery" in css
    app=ROOT.joinpath("app.py").read_text()
    assert "Tröjfärger" in app
