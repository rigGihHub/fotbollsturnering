from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "cupnavi_core" / "public_info_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

def test_release_version():
    assert VERSION == "2026.08.31-349-BEGINNER-FIRST-RUN"

def test_secondary_public_info_is_explicitly_lazy():
    gate = SRC.index('show_more_cup_details = st.toggle(')
    guarded = SRC.index('if show_more_cup_details:', gate)
    contacts = SRC.index('FROM teams WHERE tournament_id=? AND public_contact_enabled=1', guarded)
    functionaries = SRC.index('SELECT * FROM functionaries', guarded)
    offers = SRC.index('SELECT * FROM offers', guarded)
    sponsors = SRC.index('SELECT * FROM sponsors', guarded)
    feedback = SRC.index('Rapportera problem eller lämna synpunkt', guarded)
    assert gate < guarded < contacts < functionaries < offers < sponsors < feedback

def test_public_info_gate_covers_four_secondary_sections():
    assert '"Visa fler cupdetaljer"' in SRC
    assert '"📞 Lagkontakter"' in SRC
    assert 'tr("Funktionärer")' in SRC
    assert 'tr("Erbjudanden")' in SRC
    assert 'tr("Partners")' in SRC
