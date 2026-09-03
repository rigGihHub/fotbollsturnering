from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v400_mobile_setup_progress_is_compact_and_five_step_desktop():
    assert VERSION == "2026.09.03-427-TRAVEL-RULES-FLOW"
    assert ".cn-setup-progress-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}" in STYLE
    assert ".cn-setup-progress-grid{display:flex!important;gap:5px!important;overflow:hidden!important}" in STYLE
    assert ".cn-setup-step.active{flex:2.45 1 0!important;font-size:.7rem!important" in STYLE
    assert ".cn-setup-copy{font-size:.86rem;line-height:1.4;margin-bottom:10px}" in STYLE
