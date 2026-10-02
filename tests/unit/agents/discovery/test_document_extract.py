"""Discovery attachment extraction and bounded input checks."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from docling.datamodel.base_models import ConversionStatus
from pypdf import PdfWriter

from oryxenai.agents.discovery import document_extract
from oryxenai.agents.discovery.document_extract import (
    DocumentExtractionError,
    extract_document,
)

LIMITS = {"max_chars": 200_000, "max_bytes": 10 * 1024 * 1024, "max_pdf_pages": 10}


def _pdf(*, page_count: int = 1, password: str | None = None, prefix: bytes = b"") -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=300)
    if password:
        writer.encrypt(password)
    output = BytesIO()
    writer.write(output)
    return prefix + output.getvalue()


def _install_fake_converter(
    monkeypatch: pytest.MonkeyPatch,
    transcript: str,
    *,
    status: ConversionStatus = ConversionStatus.SUCCESS,
    errors: tuple[object, ...] = (),
) -> None:
    class FakeDocument:
        def export_to_markdown(self, **_kwargs: object) -> str:
            return transcript

    class FakeConverter:
        def convert(self, _document_stream: object) -> SimpleNamespace:
            return SimpleNamespace(
                status=status,
                errors=errors,
                pages=[object()],
                document=FakeDocument(),
            )

    monkeypatch.setattr(
        document_extract,
        "_get_pdf_converter",
        lambda _artifacts_path, _timeout_seconds: FakeConverter(),
    )


def test_extracts_pdf_markdown_and_reports_page_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _install_fake_converter(monkeypatch, "# Resume &amp; work\n\n- Designed a useful product.")

    name, text, page_count, warnings = extract_document(
        "resume.pdf", _pdf(prefix=b"\n"), artifacts_path=str(tmp_path), **LIMITS
    )

    assert name == "resume.pdf"
    assert text == "# Resume & work\n\n- Designed a useful product."
    assert page_count == 1
    assert warnings == []


def test_warns_when_conversion_is_partial(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _install_fake_converter(
        monkeypatch,
        "# Resume",
        status=ConversionStatus.PARTIAL_SUCCESS,
    )

    _, _, _, warnings = extract_document(
        "resume.pdf", _pdf(), artifacts_path=str(tmp_path), **LIMITS
    )

    assert warnings == ["Some PDF content may need review. Check the complete preview."]


def test_preserves_utf8_markdown_and_text_exactly() -> None:
    for filename in ("notes.md", "notes.txt"):
        original = "# My work\r\n\r\n  Built reliable systems.  \r\n"
        name, extracted, page_count, warnings = extract_document(
            filename,
            original.encode("utf-8"),
            **LIMITS,
        )
        assert name == filename
        assert extracted == original
        assert page_count is None
        assert warnings == []


def test_rejects_empty_unsupported_and_non_utf8_files() -> None:
    with pytest.raises(DocumentExtractionError, match="empty"):
        extract_document("blank.txt", b"  \n", **LIMITS)
    with pytest.raises(DocumentExtractionError, match="PDF, Markdown"):
        extract_document("resume.docx", b"content", **LIMITS)
    with pytest.raises(DocumentExtractionError, match="UTF-8"):
        extract_document("notes.md", b"\xff", **LIMITS)


def test_rejects_invalid_encrypted_and_too_many_page_pdfs(tmp_path) -> None:
    with pytest.raises(DocumentExtractionError, match="valid PDF"):
        extract_document("resume.pdf", b"not a PDF", **LIMITS)
    with pytest.raises(DocumentExtractionError, match="Password protected"):
        extract_document("resume.pdf", _pdf(password="test-only-password"), **LIMITS)  # noqa: S106
    with pytest.raises(DocumentExtractionError, match="too many pages"):
        extract_document(
            "resume.pdf",
            _pdf(page_count=2),
            artifacts_path=str(tmp_path),
            **{**LIMITS, "max_pdf_pages": 1},
        )


def test_pdf_needs_bundled_ocr_artifacts() -> None:
    with pytest.raises(DocumentExtractionError, match="not ready on this server"):
        extract_document(
            "resume.pdf",
            _pdf(),
            artifacts_path="missing-docling-models",
            **LIMITS,
        )


def test_rejects_oversized_extracted_text_and_upload() -> None:
    with pytest.raises(DocumentExtractionError, match="too much text"):
        extract_document("notes.txt", b"more than allowed", **{**LIMITS, "max_chars": 4})
    with pytest.raises(DocumentExtractionError, match="upload size limit"):
        extract_document("notes.txt", b"12345", **{**LIMITS, "max_bytes": 4})
