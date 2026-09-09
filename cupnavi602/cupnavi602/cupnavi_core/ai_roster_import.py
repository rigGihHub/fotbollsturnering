import base64
import io
import json
import re
from urllib.request import Request, urlopen

ALLOWED_POSITIONS = ["Ej angiven", "Målvakt", "Försvarare", "Mittfältare", "Anfallare"]


def normalize_player_name(value):
    return " ".join(str(value or "").strip().split())


def normalize_position(value):
    text = str(value or "").strip().casefold()
    aliases = {
        "": "Ej angiven",
        "ej angiven": "Ej angiven",
        "unknown": "Ej angiven",
        "goalkeeper": "Målvakt",
        "keeper": "Målvakt",
        "målvakt": "Målvakt",
        "malvakt": "Målvakt",
        "defender": "Försvarare",
        "back": "Försvarare",
        "försvarare": "Försvarare",
        "forsvarare": "Försvarare",
        "midfielder": "Mittfältare",
        "mittfältare": "Mittfältare",
        "mittfaltare": "Mittfältare",
        "forward": "Anfallare",
        "striker": "Anfallare",
        "anfallare": "Anfallare",
    }
    return aliases.get(text, "Ej angiven")


def _optional_int(value, minimum, maximum):
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if minimum <= number <= maximum else None


def normalize_extracted_players(players):
    """Normalize and de-duplicate AI extracted roster rows without inventing data."""
    normalized = []
    seen = set()
    for row in players or []:
        name = normalize_player_name((row or {}).get("name"))
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append({
            "name": name,
            "player_number": _optional_int((row or {}).get("player_number"), 0, 999),
            "birth_year": _optional_int((row or {}).get("birth_year"), 1900, 2100),
            "position": normalize_position((row or {}).get("position")),
        })
    return normalized


def _extract_output_text(payload):
    for item in payload.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    # Kept for compatibility with response wrappers/proxies that expose output_text.
    if payload.get("output_text"):
        return str(payload["output_text"])
    raise ValueError("AI-tjänsten returnerade inget läsbart svar.")


def _compact_image(image_bytes, mime_type, max_dimension=1800, jpeg_quality=88):
    """Downscale very large screenshots/photos when Pillow is available.

    Smaller images reduce upload time and vision token use. If Pillow is absent or
    decoding fails, the original bytes are returned unchanged.
    """
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        if max(image.size) <= max_dimension:
            return image_bytes, mime_type
        image.thumbnail((max_dimension, max_dimension))
        out = io.BytesIO()
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(out, format="JPEG", quality=jpeg_quality, optimize=True)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, mime_type


def extract_roster_from_image(
    image_bytes,
    mime_type,
    api_key,
    *,
    model="gpt-5.6-luna",
    timeout_seconds=45,
    opener=urlopen,
):
    """Extract a roster from a static image through the OpenAI Responses API.

    The function intentionally only extracts values visible in the image. Missing
    shirt numbers, birth years or positions remain null and are reviewed in UI
    before anything is written to CupNavi.
    """
    if not api_key:
        raise ValueError("Ingen AI-nyckel är konfigurerad.")
    if not image_bytes:
        raise ValueError("Bilden är tom.")
    if len(image_bytes) > 20 * 1024 * 1024:
        raise ValueError("Bilden är större än 20 MB.")

    compact_bytes, compact_mime = _compact_image(image_bytes, mime_type or "image/png")
    image_data = base64.b64encode(compact_bytes).decode("ascii")
    data_url = f"data:{compact_mime};base64,{image_data}"

    schema = {
        "type": "object",
        "properties": {
            "players": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "player_number": {"type": ["integer", "null"]},
                        "birth_year": {"type": ["integer", "null"]},
                        "position": {
                            "type": "string",
                            "enum": ALLOWED_POSITIONS,
                        },
                    },
                    "required": ["name", "player_number", "birth_year", "position"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["players"],
        "additionalProperties": False,
    }
    instructions = (
        "Läs av laguppställningen eller spelarlistan i bilden. Extrahera endast riktiga spelare som "
        "syns i bilden. Ta inte med tränare, ledare, rubriker, avbytarmarkeringar eller annan text. "
        "Gissa aldrig värden som inte syns. Om tröjnummer eller födelseår saknas, använd null. "
        "Om positionen inte tydligt framgår, använd 'Ej angiven'. Behåll svenska tecken och namn exakt "
        "så långt bilden medger."
    )
    body = {
        "model": model,
        "store": False,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": instructions},
                {"type": "input_image", "image_url": data_url, "detail": "high"},
            ],
        }],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "cupnavi_roster",
                "strict": True,
                "schema": schema,
            }
        },
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"AI-avläsningen misslyckades: {exc}") from exc

    if response_payload.get("error"):
        message = response_payload["error"].get("message") if isinstance(response_payload["error"], dict) else response_payload["error"]
        raise RuntimeError(f"AI-avläsningen misslyckades: {message}")

    raw_text = _extract_output_text(response_payload)
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        # Defensive fallback for rare wrappers that surround JSON with fences.
        match = re.search(r"\{.*\}", raw_text, flags=re.S)
        if not match:
            raise ValueError("AI-svaret kunde inte tolkas som en spelarlista.") from exc
        parsed = json.loads(match.group(0))
    return normalize_extracted_players(parsed.get("players", []))
