import json
from pathlib import Path

from cupnavi_core.ai_cup_document_import import extract_cup_setup_from_documents

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / 'cupnavi_core' / 'cup_document_creator_view.py').read_text(encoding='utf-8')
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()

class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode('utf-8')


def test_v500_version_and_requested_admin_copy():
    assert VERSION == '2026.09.07-525-OPTIONAL-REFEREE-SETUP'
    assert '<div class="cn-create-title">Vad vill du göra?</div>' in APP
    assert '<div class="cn-create-eyebrow">Admin</div>' not in APP
    assert 'Välj en väg först. CupNavi visar inget annat administrativt innehåll innan du har valt.' not in APP


def test_creator_accepts_multiple_files_and_new_label():
    assert 'Läs in tidigare cupprogram eller importera från foto/dokument' in VIEW
    assert 'accept_multiple_files=True' in VIEW
    assert 'Läs dokumenten' in VIEW
    assert 'extract_cup_setup_from_documents' in VIEW


def test_multiple_images_are_sent_in_one_request():
    seen = {}
    result_json = {
        'tournament_name': 'Slottskampen', 'location': 'Örebro', 'start_date': None, 'end_date': None,
        'venues': [], 'teams': [{'name': 'AIK', 'group_name': 'Grupp B'}], 'matches': [],
        'playoff_matches': [], 'rules': [], 'warnings': []
    }
    payload = {'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(result_json)}]}]}
    def opener(request, **kwargs):
        seen['body'] = json.loads(request.data.decode('utf-8'))
        return FakeResponse(payload)
    result = extract_cup_setup_from_documents([
        (b'one', 'page1.jpg', 'image/jpeg'),
        (b'two', 'page2.png', 'image/png'),
    ], 'x', opener=opener)
    parts = seen['body']['input'][0]['content']
    assert sum(1 for p in parts if p.get('type') == 'input_image') == 2
    assert result['teams'][0]['name'] == 'AIK'
