"""Optional, bounded intent suggestions from a local Ollama instance."""

import json
import os
import re
from http.client import HTTPConnection

from .places import PLACES

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_PATH = "/api/chat"
DEFAULT_MODEL = "llama3:8b"
TIMEOUT_SECONDS = 8
MAX_RESPONSE_BYTES = 16_384

_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "origin_id": {"type": ["string", "null"]},
        "destination_id": {"type": ["string", "null"]},
        "next_class": {"type": "boolean"},
        "step_free": {"type": "boolean"},
        "avoid_steep": {"type": "boolean"},
    },
    "required": ["origin_id", "destination_id", "next_class", "step_free", "avoid_steep"],
}


def _valid_suggestion(raw: object, allowed_ids: set[str], text: str) -> dict | None:
    if not isinstance(raw, dict) or set(raw) != set(_SCHEMA["properties"]):
        return None
    if any(raw[key] is not None and (not isinstance(raw[key], str) or raw[key] not in allowed_ids)
           for key in ("origin_id", "destination_id")):
        return None
    if any(type(raw[key]) is not bool for key in ("next_class", "step_free", "avoid_steep")):
        return None
    if raw["next_class"] and raw["destination_id"] is not None:
        return None
    step_cue = bool(re.search(r"\b(step[ -]?free|stairs?|steps?|wheelchair|accessible)\b", text, re.I))
    grade_cue = bool(re.search(r"\b(steep|slopes?|hills?|grades?)\b", text, re.I))
    next_class_cue = bool(re.search(r"\bmy next (class|lecture|course)\b", text, re.I))
    return {**raw, "step_free": step_cue, "avoid_steep": grade_cue,
            "next_class": raw["next_class"] and next_class_cue}


def suggest_intent(text: str) -> dict | None:
    """Return validated suggestions or None; errors never affect route computation."""
    model = os.getenv("UMASSNAV_OLLAMA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if len(model) > 100:
        return None
    candidates = [place for place in PLACES if any(
        re.search(r"(?<!\w)" + re.escape(alias.casefold()) + r"(?!\w)", text.casefold())
        for alias in (place.name, *place.aliases)
    )]
    catalog = "; ".join(f"{place.id}: {place.name}" for place in candidates)
    payload = {
        "model": model, "stream": False, "format": _SCHEMA,
        "options": {"temperature": 0, "num_predict": 160},
        "messages": [
            {"role": "system", "content": (
                "Extract campus trip intent from the user's text. Return only the JSON schema. "
                "Use an exact ID from the candidate catalog only when the place is clearly identified. "
                "Set next_class true only for an explicit request for the user's next class; then destination_id is null. "
                "Set step_free true only when requested (stairs, wheelchair, step-free). "
                "Set avoid_steep true only when requested. Never infer paths, coordinates, or accessibility. "
                "Candidate catalog: " + (catalog or "none; use null place IDs")
            )},
            {"role": "user", "content": text},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    connection = None
    try:
        connection = HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=TIMEOUT_SECONDS)
        connection.request("POST", OLLAMA_PATH, body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            return None
        if response.length is not None and response.length > MAX_RESPONSE_BYTES:
            return None
        if response.getheader("Content-Type", "").split(";")[0] != "application/json":
            return None
        if response.getheader("Location"):
            return None
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return None
        content = json.loads(raw).get("message", {}).get("content")
        return _valid_suggestion(json.loads(content), {place.id for place in candidates}, text) if isinstance(content, str) else None
    except (TimeoutError, OSError, ValueError, TypeError, AttributeError):
        return None
    finally:
        if connection is not None:
            connection.close()
