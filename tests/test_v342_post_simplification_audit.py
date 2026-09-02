from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text()
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_version():
    assert VERSION=="2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP"
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP

def test_global_admin_navigation_has_four_real_groups():
    block=APP[APP.index("ADMIN_NAV_GROUPS = ["):APP.index("ADMIN_NAV = [")]
    assert '("Mer", [])' in block
    assert 'group_names = [group_name for group_name, items in ADMIN_NAV_GROUPS if items]' in APP

def test_remaining_low_frequency_tools_are_contextual():
    assert 'if page == "Cupverktyg":\n        return "Matcher"' in APP
    assert 'if page in {"Sponsorer", "Erbjudanden"}:\n        return "Organisation"' in APP
    assert 'if page == "Besöksstatistik":\n        return "Översikt"' in APP
    assert '"Cupverktyg"' in APP
    assert '"Sponsorer"' in APP
    assert '"Erbjudanden"' in APP
    assert '"Besöksstatistik"' in APP

def test_contextual_entry_points_exist():
    assert 'key=f"v342_open_cup_tools_{tid}"' in APP
    assert 'key=f"v342_open_visitor_stats_{tid}"' in APP
    assert 'key=f"v342_open_sponsors_{tid}"' in APP
    assert 'key=f"v342_open_offers_{tid}"' in APP

def test_legacy_workspaces_still_exist():
    for page in ["Cupverktyg","Sponsorer","Erbjudanden","Besöksstatistik","Kontroller","Problem & lösningar","Instruktioner"]:
        assert f'admin_page == "{page}"' in APP
