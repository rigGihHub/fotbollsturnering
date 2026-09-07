import base64
import json
import re
from datetime import date
from urllib.request import Request, urlopen


def _output_text(payload):
    for item in payload.get('output', []) or []:
        if item.get('type') != 'message':
            continue
        for content in item.get('content', []) or []:
            if content.get('type') == 'output_text' and content.get('text'):
                return str(content['text'])
    if payload.get('output_text'):
        return str(payload['output_text'])
    raise ValueError('AI-tjänsten returnerade inget läsbart svar.')


def _normalize(result):
    result = dict(result or {})
    teams, seen = [], set()
    for row in result.get('teams') or []:
        name = ' '.join(str((row or {}).get('name') or '').split())
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        teams.append({'name': name, 'group_name': ' '.join(str((row or {}).get('group_name') or '').split()) or None})
    result['teams'] = teams
    result['tournament_name'] = ' '.join(str(result.get('tournament_name') or '').split()) or None
    result['location'] = ' '.join(str(result.get('location') or '').split()) or None
    for key in ('start_date', 'end_date'):
        value = str(result.get(key) or '').strip()
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                value = ''
        result[key] = value or None
    result['venues'] = [str(v).strip() for v in (result.get('venues') or []) if str(v).strip()]
    result['matches'] = [dict(v) for v in (result.get('matches') or []) if isinstance(v, dict)]
    result['playoff_matches'] = [dict(v) for v in (result.get('playoff_matches') or []) if isinstance(v, dict)]
    result['rules'] = [str(v).strip() for v in (result.get('rules') or []) if str(v).strip()]
    result['warnings'] = [str(v).strip() for v in (result.get('warnings') or []) if str(v).strip()]
    return result


def extract_cup_setup_from_document(raw, filename, mime_type, api_key, *, model='gpt-5.6-luna', timeout_seconds=60, opener=urlopen):
    if not api_key:
        raise ValueError('Ingen AI-nyckel är konfigurerad.')
    if not raw:
        raise ValueError('Dokumentet är tomt.')
    if len(raw) > 25 * 1024 * 1024:
        raise ValueError('Dokumentet är större än 25 MB.')

    lower = str(filename or '').lower()
    mime = str(mime_type or '')
    text = None
    image_url = None
    file_input = None
    if lower.endswith('.pdf') or mime == 'application/pdf':
        file_input = {'type': 'input_file', 'filename': filename or 'cupprogram.pdf', 'file_data': base64.b64encode(raw).decode('ascii')}
    elif lower.endswith('.txt') or mime.startswith('text/'):
        text = raw.decode('utf-8', errors='replace')
    elif mime.startswith('image/') or lower.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        image_url = f"data:{mime or 'image/jpeg'};base64,{base64.b64encode(raw).decode('ascii')}"
    else:
        raise ValueError('Filtypen stöds inte ännu. Använd PDF, TXT, PNG eller JPG.')

    schema = {
        'type': 'object',
        'properties': {
            'tournament_name': {'type': ['string', 'null']},
            'location': {'type': ['string', 'null']},
            'start_date': {'type': ['string', 'null'], 'description': 'ISO YYYY-MM-DD when explicitly inferable from document, otherwise null'},
            'end_date': {'type': ['string', 'null']},
            'venues': {'type': 'array', 'items': {'type': 'string'}},
            'teams': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'name': {'type': 'string'}, 'group_name': {'type': ['string', 'null']}
            }, 'required': ['name', 'group_name'], 'additionalProperties': False}},
            'matches': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'time': {'type': ['string', 'null']}, 'venue': {'type': ['string', 'null']},
                'group_name': {'type': ['string', 'null']}, 'home_team': {'type': ['string', 'null']},
                'away_team': {'type': ['string', 'null']}, 'stage': {'type': ['string', 'null']},
                'duration': {'type': ['string', 'null']}
            }, 'required': ['time','venue','group_name','home_team','away_team','stage','duration'], 'additionalProperties': False}},
            'playoff_matches': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'time': {'type': ['string', 'null']}, 'venue': {'type': ['string', 'null']},
                'label': {'type': ['string', 'null']}, 'home_source': {'type': ['string', 'null']},
                'away_source': {'type': ['string', 'null']}, 'duration': {'type': ['string', 'null']}
            }, 'required': ['time','venue','label','home_source','away_source','duration'], 'additionalProperties': False}},
            'rules': {'type': 'array', 'items': {'type': 'string'}},
            'warnings': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['tournament_name','location','start_date','end_date','venues','teams','matches','playoff_matches','rules','warnings'],
        'additionalProperties': False,
    }
    instruction = (
        'Du läser ett cupprogram för CupNavi. Extrahera bara uppgifter som faktiskt framgår. '
        'Prioritera cupnamn, spelort/område, datum, planer/anläggningar, alla deltagande lagnamn och eventuell grupp. '
        'Extrahera också gruppspelsmatcher med tid, plan, grupp, hemma/borta, spelfas och matchtid när detta faktiskt framgår, samt slutspelsmatcher med källor som 1:a grupp A eller Vinnare semi 1. Extrahera korta uttryckliga regler. Gissa aldrig. Ta inte med rubriker som lag. Behåll lagnamn exakt som i dokumentet. '
        'Om årtal saknas i datum ska start_date/end_date vara null och datumproblemet nämnas i warnings.'
    )
    content = [{'type': 'input_text', 'text': instruction + ('\n\nDOKUMENTTEXT:\n' + text[:60000] if text is not None else '')}]
    if image_url:
        content.append({'type': 'input_image', 'image_url': image_url, 'detail': 'high'})
    if file_input:
        content.append(file_input)
    body = {
        'model': model, 'store': False,
        'input': [{'role': 'user', 'content': content}],
        'text': {'format': {'type': 'json_schema', 'name': 'cupnavi_cup_document', 'strict': True, 'schema': schema}},
    }
    request = Request('https://api.openai.com/v1/responses', data=json.dumps(body).encode('utf-8'), headers={
        'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, method='POST')
    try:
        with opener(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        raise RuntimeError(f'AI-avläsningen misslyckades: {exc}') from exc
    if payload.get('error'):
        err = payload['error']
        raise RuntimeError(f"AI-avläsningen misslyckades: {err.get('message') if isinstance(err, dict) else err}")
    try:
        parsed = json.loads(_output_text(payload))
    except json.JSONDecodeError as exc:
        raise ValueError('AI-svaret kunde inte tolkas.') from exc
    return _normalize(parsed)


def extract_cup_setup_from_documents(documents, api_key, *, model='gpt-5.6-luna', timeout_seconds=90, opener=urlopen):
    """Extract one cup proposal from several related PDFs/images/text files in one AI request."""
    if not api_key:
        raise ValueError('Ingen AI-nyckel är konfigurerad.')
    documents = list(documents or [])
    if not documents:
        raise ValueError('Inga dokument har valts.')
    if len(documents) > 12:
        raise ValueError('Välj högst 12 filer åt gången.')

    content = [{
        'type': 'input_text',
        'text': (
            'Du läser ett eller flera dokument/bilder som tillsammans beskriver samma cup för CupNavi. '
            'Sammanför uppgifterna över alla sidor/filer och extrahera bara sådant som faktiskt framgår. '
            'Prioritera cupnamn, spelort/område, datum, planer/anläggningar, alla deltagande lagnamn och eventuell grupp. '
            'Extrahera gruppspelsmatcher med tid, plan, grupp, hemma/borta, spelfas och matchtid när detta framgår, '
            'samt slutspelsmatcher med källor som 1:a grupp A eller Vinnare semi 1. Extrahera korta uttryckliga regler. '
            'Gissa aldrig. Ta inte med rubriker som lag. Behåll lagnamn exakt som i dokumenten. '
            'Om filer motsäger varandra ska du inte välja på måfå: använd warnings. Om årtal saknas ska datumfält vara null.'
        ),
    }]
    total_bytes = 0
    for index, item in enumerate(documents, start=1):
        try:
            raw, filename, mime_type = item
        except Exception as exc:
            raise ValueError('Ogiltigt dokumentunderlag.') from exc
        raw = raw or b''
        if not raw:
            continue
        if len(raw) > 25 * 1024 * 1024:
            raise ValueError(f'{filename or "En fil"} är större än 25 MB.')
        total_bytes += len(raw)
        if total_bytes > 60 * 1024 * 1024:
            raise ValueError('Filerna är tillsammans för stora. Dela upp importen i färre filer.')
        filename = filename or f'dokument-{index}'
        lower = str(filename).lower()
        mime = str(mime_type or '')
        content.append({'type': 'input_text', 'text': f'FIL {index}: {filename}'})
        if lower.endswith('.pdf') or mime == 'application/pdf':
            content.append({'type': 'input_file', 'filename': filename, 'file_data': base64.b64encode(raw).decode('ascii')})
        elif lower.endswith('.txt') or mime.startswith('text/'):
            content.append({'type': 'input_text', 'text': raw.decode('utf-8', errors='replace')[:60000]})
        elif mime.startswith('image/') or lower.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            content.append({'type': 'input_image', 'image_url': f"data:{mime or 'image/jpeg'};base64,{base64.b64encode(raw).decode('ascii')}", 'detail': 'high'})
        else:
            raise ValueError(f'Filtypen stöds inte för {filename}. Använd PDF, TXT, PNG, JPG eller WEBP.')

    if len(content) == 1:
        raise ValueError('Dokumenten är tomma.')

    schema = {
        'type': 'object',
        'properties': {
            'tournament_name': {'type': ['string', 'null']},
            'location': {'type': ['string', 'null']},
            'start_date': {'type': ['string', 'null']},
            'end_date': {'type': ['string', 'null']},
            'venues': {'type': 'array', 'items': {'type': 'string'}},
            'teams': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'name': {'type': 'string'}, 'group_name': {'type': ['string', 'null']}
            }, 'required': ['name', 'group_name'], 'additionalProperties': False}},
            'matches': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'time': {'type': ['string', 'null']}, 'venue': {'type': ['string', 'null']},
                'group_name': {'type': ['string', 'null']}, 'home_team': {'type': ['string', 'null']},
                'away_team': {'type': ['string', 'null']}, 'stage': {'type': ['string', 'null']},
                'duration': {'type': ['string', 'null']}
            }, 'required': ['time','venue','group_name','home_team','away_team','stage','duration'], 'additionalProperties': False}},
            'playoff_matches': {'type': 'array', 'items': {'type': 'object', 'properties': {
                'time': {'type': ['string', 'null']}, 'venue': {'type': ['string', 'null']},
                'label': {'type': ['string', 'null']}, 'home_source': {'type': ['string', 'null']},
                'away_source': {'type': ['string', 'null']}, 'duration': {'type': ['string', 'null']}
            }, 'required': ['time','venue','label','home_source','away_source','duration'], 'additionalProperties': False}},
            'rules': {'type': 'array', 'items': {'type': 'string'}},
            'warnings': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['tournament_name','location','start_date','end_date','venues','teams','matches','playoff_matches','rules','warnings'],
        'additionalProperties': False,
    }
    body = {
        'model': model,
        'store': False,
        'input': [{'role': 'user', 'content': content}],
        'text': {'format': {'type': 'json_schema', 'name': 'cupnavi_multi_cup_document', 'strict': True, 'schema': schema}},
    }
    request = Request('https://api.openai.com/v1/responses', data=json.dumps(body).encode('utf-8'), headers={
        'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, method='POST')
    try:
        with opener(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        raise RuntimeError(f'AI-avläsningen misslyckades: {exc}') from exc
    if payload.get('error'):
        err = payload['error']
        raise RuntimeError(f"AI-avläsningen misslyckades: {err.get('message') if isinstance(err, dict) else err}")
    try:
        parsed = json.loads(_output_text(payload))
    except json.JSONDecodeError as exc:
        raise ValueError('AI-svaret kunde inte tolkas.') from exc
    return _normalize(parsed)
