from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VIEW=(ROOT/"cupnavi_core/initial_setup_view.py").read_text()
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text()
VERSION=(ROOT/"VERSION.txt").read_text().strip()
APP=(ROOT/"app.py").read_text()

def test_version():
 assert VERSION=="2026.08.31-348-GUIDED-CUP-SETUP"
 assert f'APP_BUILD_VERSION = "{VERSION}"' in APP

def test_visual_continuity():
 assert "cn-setup-hero" in VIEW and "cn-setup-progress-grid" in VIEW
 assert "Cup skapad · fortsätt setupen" in VIEW
 assert ".cn-setup-progress-grid{grid-template-columns:1fr 1fr}" in STYLE

def test_standard_path_is_core_only():
 before=VIEW[:VIEW.index('_show_advanced_setup = st.toggle(')]
 assert 'st.markdown("### Sportprofil")' not in before
 assert 'st.markdown("### 1. Vilka ska spela?")' in before
 assert 'st.markdown("### 2. Vad har ni tillgång till?")' in before
 assert 'Fortsätt → Lägg till lag' in before

def test_sport_profile_is_retained_advanced():
 advanced=VIEW[VIEW.index('if _show_advanced_setup:'):]
 assert 'with st.expander("Sportprofil", expanded=False):' in advanced
 assert 'Använd rekommenderade' in advanced


def test_environment_continuity():
 assert '_setup_environment_label = "🧪 Testmiljö"' in VIEW
 assert "{_setup_environment_label}" in VIEW
