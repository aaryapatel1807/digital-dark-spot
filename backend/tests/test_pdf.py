"""PDF extraction tests: real extraction with page refs, plus
rejections for non-PDF, oversize, and textless input."""

import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from app.main import app
from app.pdf import PdfRejected, extract_pdf_text

client = TestClient(app)


def _make_pdf(pages_text):
    writer = PdfWriter()
    for text in pages_text:
        page = writer.add_blank_page(width=200, height=200)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = StreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream.set_data(f"BT /F1 12 Tf 10 180 Td ({escaped}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_extract_pdf_with_page_refs():
    data = _make_pdf(["Scholarship renewal requires CGPA 7.0.", "Apply before 31 December 2026."])
    result = extract_pdf_text(data, "guide.pdf")
    assert result["pages"] == 2
    assert result["pages_with_text"] == 2
    assert "[Page 1]" in result["text"] and "[Page 2]" in result["text"]
    assert "CGPA 7.0" in result["text"]


def test_extract_rejects_non_pdf():
    try:
        extract_pdf_text(b"hello, not a pdf", "x.pdf")
    except PdfRejected as exc:
        assert "not a PDF" in str(exc)
    else:
        raise AssertionError("non-PDF was not rejected")


def test_extract_rejects_oversize():
    try:
        extract_pdf_text(b"%PDF-" + b"x" * (5 * 1024 * 1024 + 1), "big.pdf")
    except PdfRejected as exc:
        assert "5 MB" in str(exc)
    else:
        raise AssertionError("oversize PDF was not rejected")


def test_endpoint_accepts_pdf_and_rejects_text():
    data = _make_pdf(["Eligibility: family income below the limit."])
    response = client.post(
        "/api/pdf-text",
        files={"file": ("guide.pdf", data, "application/pdf")},
    )
    assert response.status_code == 200
    assert "Eligibility" in response.json()["text"]
    bad = client.post(
        "/api/pdf-text",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert bad.status_code == 415
