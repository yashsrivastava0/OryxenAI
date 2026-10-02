"""Discovery attachment extraction and bounded input checks."""

from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from oryxenai.agents.discovery.document_extract import (
    DocumentExtractionError,
    extract_document,
)

LIMITS = {"max_chars": 200_000, "max_bytes": 8 * 1024 * 1024, "max_pdf_pages": 40}


def _text_pdf() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    contents = DecodedStreamObject()
    contents.set_data(b"BT /F1 12 Tf 20 200 Td (Resume project experience) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(contents)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_extracts_text_from_pdf() -> None:
    name, text = extract_document("resume.pdf", _text_pdf(), **LIMITS)
    assert name == "resume.pdf"
    assert "Resume project experience" in text


def test_accepts_utf8_markdown_and_rejects_empty_or_unsupported() -> None:
    assert extract_document("notes.md", b"\xef\xbb\xbf# My work", **LIMITS)[1] == "# My work"
    with pytest.raises(DocumentExtractionError, match="selectable text"):
        extract_document("blank.txt", b"  \n", **LIMITS)
    with pytest.raises(DocumentExtractionError, match="PDF, Markdown"):
        extract_document("resume.docx", b"content", **LIMITS)


def test_rejects_oversized_extracted_text() -> None:
    with pytest.raises(DocumentExtractionError, match="too much text"):
        extract_document("notes.txt", b"more than allowed", **{**LIMITS, "max_chars": 4})
