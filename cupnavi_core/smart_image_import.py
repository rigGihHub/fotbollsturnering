"""Safe discovery pass for image-based CupNavi import.

The first AI pass only identifies information visible in the image. Nothing is
written to the tournament until the organizer chooses which detected sections
they want to continue with.
"""
import base64, json, re
from urllib.request import Request, urlopen

ALLOWED_SECTIONS = ["Cupinfo", "Lag", "Grupper", "Regler", "Planer & tider", "Domare", "Schema", "Trupper", "Övrigt"]


def _output_text(payload):
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            if isinstance(content.get("text"), str):
                return content["text"]
    return ""


def detect_importable_sections(image_bytes, mime_type, api_key, *, model="gpt-5.6-luna", timeout_seconds=45, opener=urlopen):
    if not api_key:
        raise ValueError("Ingen AI-nyckel är konfigurerad.")
    if not image_bytes:
        raise ValueError("Bilden är tom.")
    if len(image_bytes) > 20 * 1024 * 1024:
        raise ValueError("Bilden är större än 20 MB.")
    data_url = f"data:{mime_type or 'image/png'};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    schema = {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "enum": ALLOWED_SECTIONS},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        "summary": {"type": "string"},
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["section", "confidence", "summary", "items"],
                    "additionalProperties": False,
                },
            },
            "caveats": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["sections", "caveats"],
        "additionalProperties": False,
    }
    prompt = (
        "Analysera bilden som underlag för en cup/turnering. Identifiera ENDAST information som faktiskt syns "
        "och som kan föras in i CupNavi. Klassificera den under Cupinfo, Lag, Grupper, Regler, Planer & tider, "
        "Domare, Schema, Trupper eller Övrigt. Utelämna helt kategorier där ingen relevant information syns. "
        "Skriv kort sammanfattning och konkreta synliga datapunkter. Gissa aldrig saknade värden. Markera låg "
        "säkerhet när texten är svårläst eller tolkningen osäker."
    )
    body = {
        "model": model, "store": False,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}, {"type": "input_image", "image_url": data_url, "detail": "high"}]}],
        "text": {"format": {"type": "json_schema", "name": "cupnavi_selective_import", "strict": True, "schema": schema}},
    }
    req = Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with opener(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode())
    except Exception as exc:
        raise RuntimeError(f"Bildanalysen misslyckades: {exc}") from exc
    if payload.get("error"):
        err = payload["error"]
        raise RuntimeError(f"Bildanalysen misslyckades: {err.get('message') if isinstance(err, dict) else err}")
    raw = _output_text(payload)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if not match:
            raise ValueError("AI-svaret kunde inte tolkas.")
        parsed = json.loads(match.group(0))
    seen, sections = set(), []
    for row in parsed.get("sections", []):
        section = row.get("section")
        if section not in ALLOWED_SECTIONS or section in seen:
            continue
        seen.add(section); sections.append(row)
    return {"sections": sections, "caveats": parsed.get("caveats", [])}
