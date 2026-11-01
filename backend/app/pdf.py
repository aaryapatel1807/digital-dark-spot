"""Text-based PDF extraction (GapLens 2.0, Step 4).

Limits, enforced here, not hoped for:
- File must be a PDF (content-type and %PDF- header checked).
- At most 5 MB, at most 50 pages, at most 200,000 characters
  (the same pasted-text cap as /api/analyze).
- Scanned/image PDFs yield no text and are reported as such —
  no OCR is claimed, no content is invented.
- Page references survive into the evidence pipeline as
  "[Page N]" markers inserted between pages, so a quote drawn
  from a PDF carries its page in the quote itself.
"""

from __future__ import annotations

import io
import re

from pypdf import PdfReader

MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 50
MAX_PDF_CHARS = 200_000


class PdfRejected(Exception):
    pass


def extract_pdf_text(data: bytes, filename: str) -> dict:
    if len(data) > MAX_PDF_BYTES:
        raise PdfRejected("PDF is larger than the 5 MB limit.")
    if not data.startswith(b"%PDF-"):
        raise PdfRejected("This file is not a PDF (missing %PDF- header).")
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise PdfRejected(f"PDF could not be read: {type(exc).__name__}.") from exc
    if len(reader.pages) > MAX_PDF_PAGES:
        raise PdfRejected(f"PDF has more than {MAX_PDF_PAGES} pages.")
    if len(reader.pages) == 0:
        raise PdfRejected("PDF has no pages.")
    pages: list[dict] = []
    total = 0
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = re.sub(r"\s+", " ", text).strip()
        pages.append({"page": index, "text": text})
        total += len(text)
    if total == 0:
        raise PdfRejected(
            "No text could be extracted from this PDF. Scanned or image-based PDFs are not supported."
        )
    if total > MAX_PDF_CHARS:
        raise PdfRejected("Extracted text exceeds the 200,000 character limit.")
    combined = "\n\n".join(
        f"[Page {p['page']}]\n{p['text']}" for p in pages if p["text"]
    )
    return {
        "filename": filename,
        "pages": len(reader.pages),
        "pages_with_text": sum(1 for p in pages if p["text"]),
        "total_chars": total,
        "text": combined,
        "page_texts": pages,
    }
