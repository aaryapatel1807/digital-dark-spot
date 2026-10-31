"""Optional Groq question derivation for /api/analyze.

Rules, stated plainly:
- Only the research GOAL is sent to Groq. Source texts, URLs, and
  pasted content never leave this server.
- Groq only ever proposes QUESTIONS. It never writes findings,
  summaries, or quotes — those come from the deterministic engine
  over collected text, so a model hallucination cannot become
  evidence.
- Any failure (no key, timeout, bad JSON, empty list) returns None
  and the caller falls back to template questions. No exception
  ever reaches the user as a crash.
- The key is read from backend-only settings and is never logged
  or returned.
"""

from __future__ import annotations

import requests

from .config import get_settings

_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
_MAX_QUESTIONS = 8


def derive_questions_with_groq(goal: str) -> list[str] | None:
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    model = settings.groq_model or "llama-3.1-8b-instant"
    try:
        response = requests.post(
            _ENDPOINT,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.2,
                "max_tokens": 500,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Propose concise research questions for the given "
                            "research goal. Reply with JSON only, shaped as "
                            '{"questions": ["...", "..."]}. At most 8 '
                            "questions, each under 500 characters, no "
                            "answers, no citations, no URLs."
                        ),
                    },
                    {"role": "user", "content": goal},
                ],
            },
            timeout=settings.groq_timeout_seconds,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        content = response.json()["choices"][0]["message"]["content"]
        import json as _json

        data = _json.loads(content)
        raw = data.get("questions")
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    if not isinstance(raw, list):
        return None
    cleaned: list[str] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text and len(text) <= 500 and text not in cleaned:
                cleaned.append(text)
        if len(cleaned) >= _MAX_QUESTIONS:
            break
    return cleaned or None
