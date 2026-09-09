import json
from pathlib import Path

from cupnavi_core.ai_cup_document_import import extract_cup_setup_from_document

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VIEW = (ROOT / 'cupnavi_core' / 'cup_document_creator_view.py').read_text(encoding='utf-8')

class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode('utf-8')


def test_pdf_is_sent_as_file_input_and_result_is_normalized():
    seen = {}
    payload = {'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps({
        'tournament_name': ' Slottskampen ', 'location': ' Örebro ', 'start_date': None, 'end_date': None,
        'venues': ['Sörbyvallen', 'Ekäng'], 'teams': [
            {'name': 'Hammarby', 'group_name': 'Grupp A'}, {'name': ' Hammarby ', 'group_name': 'Grupp A'},
            {'name': 'AIK', 'group_name': 'Grupp B'}], 'warnings': ['Årtal saknas']})}]}]}
    def opener(request, **kwargs):
        seen['body'] = json.loads(request.data.decode('utf-8'))
        return FakeResponse(payload)
    result = extract_cup_setup_from_document(b'%PDF-test', 'cup.pdf', 'application/pdf', 'x', opener=opener)
    content = seen['body']['input'][0]['content']
    assert any(part.get('type') == 'input_file' and part.get('filename') == 'cup.pdf' for part in content)
    assert result['tournament_name'] == 'Slottskampen'
    assert [x['name'] for x in result['teams']] == ['Hammarby', 'AIK']


def test_creation_ui_has_document_drop_review_and_safe_team_import():
    assert 'render_cup_document_import' in APP
    assert 'Läs in tidigare cupprogram eller importera från foto/dokument' in VIEW
    assert 'Lägg in de hittade lagen och grupperna när cupen skapas' in VIEW
    assert 'Never creates matches' in VIEW
    assert 'INSERT INTO groups(tournament_id,name)' in VIEW
    assert 'Importerad från' in VIEW
