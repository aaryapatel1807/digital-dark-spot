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


def derive_semantic_terms(questions: list[str]) -> dict[str, set[str]]:
    """Optional equivalent terms (GapLens 2.0, Step 2), mapped by
    original word: {"renewed": {"continue", "extended"}, ...}.

    Only the question texts are sent — never source text, URLs, or
    pasted content. The mapping form matters: an expanded term may
    stand for exactly one original word, so one matching term can
    never inflate every question token. Any failure returns {},
    so the static concept clusters remain the fallback. Terms are
    validated as single alphabetic words, at most 10 per word, and
    are used only to SELECT sentences — never as findings or quotes.
    """
    settings = get_settings()
    if not settings.groq_api_key or not questions:
        return {}
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
                "temperature": 0.0,
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "For each research question, map each important "
                            "word to single-word equivalent terms a source "
                            "might use instead. Reply with JSON only, shaped "
                            'as {"terms": {"renewed": ["continue"], '
                            '"amount": ["grant"]}}. Keys must be words from '
                            "the questions; values are single words only. "
                            "No answers, no citations, no URLs, no "
                            "multi-word phrases."
                        ),
                    },
                    {"role": "user", "content": "\n".join(questions)},
                ],
            },
            timeout=settings.groq_timeout_seconds,
        )
    except requests.RequestException:
        return {}
    if response.status_code != 200:
        return {}
    try:
        import json as _json

        data = _json.loads(response.json()["choices"][0]["message"]["content"])
        raw = data.get("terms")
    except (ValueError, KeyError, IndexError, TypeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    question_words = {w.strip().lower() for q in questions for w in q.split()}
    out: dict[str, set[str]] = {}
    for key, values in raw.items():
        if not isinstance(key, str) or key.strip().lower() not in question_words:
            continue
        terms: set[str] = set()
        if isinstance(values, list):
            for term in values[:10]:
                if isinstance(term, str) and term.strip().isalpha() and len(term) <= 30:
                    terms.add(term.strip().lower())
        if terms:
            out[key.strip().lower()] = terms
    return out

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
