from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()
CORE_VERSION = (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')


def test_versions_are_synchronized():
    expected = '2026.09.08-561-ACCESS-CENTER-LOCAL-ADMINS'
    assert VERSION == expected
    assert f'APP_BUILD_VERSION = "{expected}"' in APP
    assert f'APP_VERSION = "{expected}"' in CORE_VERSION


def test_access_center_manages_local_cup_admins():
    assert 'st.header("Alla koder")' in APP
    assert 'Åtkomstcenter · hantera cupadministratörer och alla koder på ett ställe.' in APP
    assert 'st.subheader("Cupadministratörer")' in APP
    assert 'Lägg till lokal cupadministratör' in APP
    assert 'tournament_members' in APP
    assert 'role=CASE WHEN tournament_members.role=\'owner\'' in APP


def test_only_owner_or_superadmin_can_manage_other_admins():
    assert 'def _can_manage_tournament_admins(tournament_id):' in APP
    assert '_current_tournament_member_role(tournament_id) == "owner"' in APP
    assert 'Endast cupens ägare kan lägga till eller ta bort andra cupadministratörer.' in APP


def test_new_local_admin_gets_scrypt_hashed_temporary_password():
    assert 'def _generate_temporary_admin_password' in APP
    assert '_account_password_hash(temporary_password, salt)' in APP
    assert 'Tillfälligt lösenord' in APP
    assert 'Lösenordet visas bara nu' in APP


def test_owner_membership_cannot_be_removed_by_local_admin_tool():
    assert "if row[\"role\"] != \"owner\"" in APP
    assert "AND role<>'owner'" in APP


def test_current_organizer_can_change_own_password():
    assert 'Min profil · byt lösenord' in APP
    assert 'Nuvarande lösenord' in APP
    assert 'UPDATE organizer_accounts SET password_salt=?,password_hash=? WHERE id=?' in APP
