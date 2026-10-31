"""Collect sources for one analysis run and give each one a stable ID.

IDs are assigned in input order: URLs first (S1, S2, ...), then
pasted texts continuing the same sequence. An inaccessible URL
still gets an ID and a record — it is marked with its fetch status
and error, never silently dropped, so the analysis can say exactly
which inputs failed and why.

The full collected text stays server-side for this run only: the
response carries a short excerpt per source plus verified quotes.
It is never stored, and it never leaves the process except inside
those quotes. Pasted text is never fetched and never dated: its
date_status is always "unknown" unless the text itself is a demo
source built by the sample layer, which sets its date explicitly.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from pydantic import HttpUrl

from .analysis_schemas import PastedText, SourceRecord
from .fetcher import FetchedPage, fetch_url_record

_EXCERPT_CHARS = 1000
# Fetching was sequential: 20 slow URLs at the 10 s timeout meant a
# ~200 s analyze request. Five concurrent fetches cut the common
# case sharply without hammering any one site; order is preserved
# by executor.map, so source IDs never change.
_MAX_FETCH_WORKERS = 5


@dataclass
class CollectedSource:
    record: SourceRecord
    text: str | None  # Full normalized text; server-side only, per run.


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _safe_fetch(url: str) -> FetchedPage:
    """fetch_url_record already maps transport errors to results, but
    a bug in it must never take down a whole analyze run: fall back
    to a failed page for that one source instead."""
    try:
        return fetch_url_record(url)
    except Exception as exc:  # Defensive: keep the run alive.
        return FetchedPage(url=url, status="failed", error=f"Unexpected fetch error: {type(exc).__name__}.")


def collect_sources(
    urls: list[HttpUrl], texts: list[PastedText]
) -> list[CollectedSource]:
    """Fetch every URL and wrap every pasted text into collected sources."""
    collected: list[CollectedSource] = []
    index = 1
    url_strings = [str(raw_url) for raw_url in urls]
    if url_strings:
        with ThreadPoolExecutor(max_workers=min(_MAX_FETCH_WORKERS, len(url_strings))) as pool:
            pages = list(pool.map(_safe_fetch, url_strings))
    else:
        pages = []
    for raw_url, page in zip(urls, pages):
        source_id = f"S{index}"
        index += 1
        collected.append(
            CollectedSource(
                record=SourceRecord(
                    id=source_id,
                    kind="url",
                    url=page.url,
                    title=page.title,
                    fetch_status=page.status,
                    date_status="known" if page.published_date else "unknown",
                    published_date=page.published_date,
                    text_excerpt=page.text[:_EXCERPT_CHARS] if page.text else None,
                    text_length=len(page.text) if page.text else 0,
                    error=page.error,
                ),
                text=page.text,
            )
        )
    for item in texts:
        source_id = f"S{index}"
        index += 1
        clean = _normalize(item.text)
        collected.append(
            CollectedSource(
                record=SourceRecord(
                    id=source_id,
                    kind="pasted_text",
                    url=None,
                    title=item.title or f"Pasted text {source_id}",
                    fetch_status="ok",
                    date_status="unknown",
                    published_date=None,
                    text_excerpt=clean[:_EXCERPT_CHARS] if clean else None,
                    text_length=len(clean),
                    error=None,
                ),
                text=clean if clean else None,
            )
        )
    return collected
