from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")

def test_v593_build_version():
    assert 'APP_BUILD_VERSION = "2026.09.09-593-DESIGN-UX-PLAN-FLOW"' in APP

def test_v593_plan_flow_has_one_bottom_primary_cta():
    block=APP.split('elif admin_page == "Planer & tider":',1)[1].split('elif admin_page == "Adminöversikt":',1)[0]
    assert '### 1. Hur många planer har ni?' in block
    assert '### 2. När kan planerna användas?' in block
    assert 'key=f"v593_plan_next_{tid}"' in block
    assert 'Rätta plantiderna ovan innan du går vidare.' in block

def test_v593_visual_system_and_accessibility():
    assert 'v593 — CUPNAVI VISUAL SYSTEM PASS' in APP
    assert '--cn-cyan:#20d9f6' in APP
    assert '@media(prefers-reduced-motion:reduce)' in APP
    assert 'min-height:44px' in APP
