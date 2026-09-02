
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
ROLE=(ROOT/"cupnavi_core/admin_role_codes_view.py").read_text(encoding="utf-8")

def test_reporter_and_referee_regeneration_requires_confirmation():
    block=ROLE
    assert '"Regenerera ny kod"' in block
    assert '"Är du säker?' in block
    assert '"Ja, regenerera"' in block
    assert '"Avbryt"' in block

def test_all_team_codes_can_be_regenerated_with_confirmation():
    block=APP[APP.index('if st.toggle("Lagportal – koder"'):APP.index('if st.toggle("Lagmeddelanden"')]
    assert '"Regenerera koder för alla lag"' in block
    assert '"Ja, regenerera alla"' in block
    assert "Alla tidigare lagkoder är nu ogiltiga." in block
    assert "_rotate_all_participant_codes(tid)" in block

def test_individual_team_code_regeneration_requires_confirmation():
    block=APP[APP.index('if st.toggle("Lagportal – koder"'):APP.index('if st.toggle("Lagmeddelanden"')]
    assert '"Regenerera lagkod"' in block
    assert '"Ja, regenerera"' in block
    assert "individual_confirm_key" in block

def test_bulk_team_rotation_is_single_transaction_and_hashed():
    helper=APP[APP.index("def _rotate_all_participant_codes"):APP.index("def _trash_tournament_if_current")]
    assert "with db() as con:" in helper
    assert "new_code_hash(plain_code)" in helper
    assert "con.commit()" in helper
    assert "ON CONFLICT(tournament_id,team_id) DO UPDATE" in helper
