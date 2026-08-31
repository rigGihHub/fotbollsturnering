from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
RELEASE = "2026.08.31-353-GROUP-FLOW-PITCH-TIMING"


def test_v288_release_is_synced():
    assert VERSION == RELEASE
    assert f'APP_BUILD_VERSION = "{RELEASE}"' in APP
    assert f'APP_VERSION = "{RELEASE}"' in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_style_system_owns_the_large_style_injectors():
    tree = ast.parse(STYLE)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    expected = {
        "inject_custom_css",
        "inject_ux2_css",
        "inject_v191_design_system",
        "inject_v193_product_design_system",
        "inject_v266_public_mobile_css",
        "inject_v198_visual_system",
    }
    assert expected <= functions.keys()
    assert functions["inject_ux2_css"].args.args[0].arg == "st"
    assert functions["inject_ux2_css"].args.args[1].arg == "components"
    for name in expected - {"inject_ux2_css"}:
        assert functions[name].args.args[0].arg == "st"


def test_app_keeps_only_thin_compatibility_wrappers():
    tree = ast.parse(APP)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for name in (
        "inject_custom_css",
        "inject_ux2_css",
        "inject_v191_design_system",
        "inject_v193_product_design_system",
        "inject_v266_public_mobile_css",
        "inject_v198_visual_system",
    ):
        node = functions[name]
        assert node.end_lineno - node.lineno + 1 <= 2


def test_style_module_has_no_persistence_or_application_imports():
    assert "sqlite3" not in STYLE
    assert "cupnavi_core." not in STYLE
    assert "SELECT " not in STYLE
    assert "INSERT " not in STYLE
    assert "UPDATE " not in STYLE
    assert "DELETE " not in STYLE


def test_visual_contracts_remain_in_extracted_module():
    for token in (
        "CUPNAVI VISUAL SYSTEM v1.198",
        "CUPNAVI PRODUCT DESIGN SYSTEM v1.193",
        "--cn98-control:44px",
        "@media(prefers-reduced-motion:reduce)",
        "focus-visible",
        "cn-mobile-bottom-nav",
        "ctrlKey||e.metaKey",
    ):
        assert token in STYLE
