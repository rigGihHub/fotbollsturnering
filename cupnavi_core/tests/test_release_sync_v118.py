from pathlib import Path
import ast
import re


def test_release_versions_are_synchronized():
    root = Path('.')
    app = (root / 'app.py').read_text(encoding='utf-8')
    version_txt = (root / 'VERSION.txt').read_text(encoding='utf-8').strip()
    core_version = (root / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')
    m = re.search(r'APP_BUILD_VERSION = "([^"]+)"', app)
    assert m, 'APP_BUILD_VERSION missing from app.py'
    assert m.group(1) == version_txt
    assert f'APP_VERSION = "{version_txt}"' in core_version


def test_all_direct_cupnavi_core_imports_exist():
    root = Path('.')
    tree = ast.parse((root / 'app.py').read_text(encoding='utf-8'))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('cupnavi_core.'):
            imported.add(node.module.split('.', 1)[1].split('.', 1)[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('cupnavi_core.'):
                    imported.add(alias.name.split('.', 1)[1].split('.', 1)[0])
    missing = [name for name in sorted(imported) if not (root / 'cupnavi_core' / f'{name}.py').exists()]
    assert not missing, f'Missing imported cupnavi_core modules: {missing}'


def test_release_manifest_contains_ux2_and_current_tests():
    manifest = Path('RELEASE_MANIFEST.txt').read_text(encoding='utf-8')
    assert 'cupnavi_core/ux2.py' in manifest
    assert 'tests/test_release_sync_v118.py' in manifest
