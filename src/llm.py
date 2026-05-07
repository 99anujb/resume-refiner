"""Wrapper around Google Gemini (google-genai SDK) for structured JSON + text calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash"
HEAVY_MODEL = "gemini-2.5-pro"

_client: "genai.Client | None" = None


def client() -> "genai.Client":
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) not set in environment")
        _client = genai.Client(api_key=api_key)
    return _client


def load_profile() -> dict:
    p = Path(__file__).resolve().parent.parent / "data" / "master_profile.json"
    return json.loads(p.read_text())


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    return text


def _generate(system: str, user: str, *, model: str, max_tokens: int,
              json_mode: bool) -> str:
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.4,
        max_output_tokens=max_tokens,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    resp = client().models.generate_content(
        model=model,
        contents=user,
        config=cfg,
    )
    text = getattr(resp, "text", None)
    if not text:
        finish = None
        try:
            finish = resp.candidates[0].finish_reason
        except Exception:
            pass
        raise RuntimeError(f"Gemini returned no text (finish_reason={finish})")
    return text


def call_json(
    system: str,
    user: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    cache_system: bool = True,  # accepted for API parity
) -> dict[str, Any]:
    raw = _generate(system, user, model=model, max_tokens=max_tokens, json_mode=True)
    text = _strip_fences(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Gemini occasionally produces unescaped quotes or stray newlines inside strings.
        # Try json-repair, then a retry with a strictness reminder.
        try:
            from json_repair import repair_json
            return json.loads(repair_json(text))
        except Exception:
            pass
        retry_user = (
            user
            + "\n\nIMPORTANT: Your previous output failed JSON.parse. "
            + "Return ONLY valid RFC 8259 JSON. Escape every \" inside strings as \\\". "
            + "Do not include unescaped newlines inside strings."
        )
        raw2 = _generate(system, retry_user, model=model, max_tokens=max_tokens, json_mode=True)
        text2 = _strip_fences(raw2)
        try:
            return json.loads(text2)
        except json.JSONDecodeError:
            from json_repair import repair_json
            return json.loads(repair_json(text2))


def call_text(
    system: str,
    user: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    cache_system: bool = True,
) -> str:
    raw = _generate(system, user, model=model, max_tokens=max_tokens, json_mode=False)
    return raw.strip()
