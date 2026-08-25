import ast
from pathlib import Path


def test_all_direct_cupnavi_core_imports_exist():
    app = Path("app.py")
    tree = ast.parse(app.read_text(encoding="utf-8"))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("cupnavi_core."):
            imported_modules.add(node.module.split(".", 1)[1].split(".", 1)[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("cupnavi_core."):
                    imported_modules.add(alias.name.split(".", 1)[1].split(".", 1)[0])
    missing = [name for name in sorted(imported_modules) if not Path("cupnavi_core", f"{name}.py").exists()]
    assert not missing, f"Missing imported cupnavi_core modules: {missing}"
