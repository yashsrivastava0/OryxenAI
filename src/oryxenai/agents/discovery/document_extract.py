"""Bounded, structure-aware extraction for user supplied Discovery documents."""

from __future__ import annotations

from functools import lru_cache
from html import unescape
from io import BytesIO
from pathlib import Path, PurePath

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import (
    HeadingHierarchyOptions,
    OcrMode,
    PdfPipelineOptions,
    RapidOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.common.content_layer import ContentLayer
from docling_core.types.io import DocumentStream
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


class DocumentExtractionError(ValueError):
    """A safe reason that an uploaded source cannot be used."""


@lru_cache(maxsize=4)
def _get_pdf_converter(artifacts_path: str, timeout_seconds: float) -> DocumentConverter:
    """Keep one CPU OCR/layout pipeline per process and artifact directory."""
    options = PdfPipelineOptions(
        document_timeout=timeout_seconds,
        accelerator_options=AcceleratorOptions(num_threads=2, device="cpu"),
        artifacts_path=artifacts_path,
        do_ocr=True,
        do_table_structure=True,
        # DEFAULT lets Docling keep selectable PDF text as the source of truth
        # and OCRs image regions (including fully scanned pages) only. FULL_PAGE
        # OCR replaces clean embedded glyphs with recognition guesses.
        ocr_options=RapidOcrOptions(mode=OcrMode.DEFAULT, lang=["en"], backend="onnxruntime"),
        heading_hierarchy_options=HeadingHierarchyOptions(enabled=True),
        generate_page_images=False,
        generate_picture_images=False,
        ocr_batch_size=1,
        layout_batch_size=1,
        table_batch_size=1,
    )
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=options,
                backend=PyPdfiumDocumentBackend,
            )
        }
    )


def extract_document(
    filename: str,
    data: bytes,
    *,
    max_chars: int,
    max_bytes: int,
    max_pdf_pages: int,
    artifacts_path: str = ".workspace/docling-models",
    pdf_timeout_seconds: float = 120.0,
) -> tuple[str, str, int | None, list[str]]:
    """Return a display name, full transcript, PDF page count, and review warnings.

    Plain-text formats are decoded without newline or whitespace normalization.
    PDFs are converted with local page OCR and layout analysis to preserve the
    document's semantic structure in Markdown. Uploaded bytes are never saved.
    """
    name = PurePath(filename.replace("\\", "/")).name.strip()
    if not name or len(name) > 200 or any(ord(char) < 32 for char in name):
        raise DocumentExtractionError("Choose a file with a valid name.")
    extension = PurePath(name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentExtractionError("Attach a PDF, Markdown, or plain text file.")
    if not data:
        raise DocumentExtractionError("The selected file is empty.")
    if len(data) > max_bytes:
        raise DocumentExtractionError("The selected file exceeds the upload size limit.")

    page_count: int | None = None
    warnings: list[str] = []
    if extension == ".pdf":
        extracted, page_count, warnings = _extract_pdf(
            name,
            data,
            max_pdf_pages=max_pdf_pages,
            artifacts_path=artifacts_path,
            timeout_seconds=pdf_timeout_seconds,
        )
    else:
        try:
            # utf-8-sig accepts ordinary UTF-8 and removes a BOM, if present.
            extracted = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError("This text file must use UTF-8 encoding.") from exc

    if not extracted.strip():
        message = (
            "No readable text was found in this PDF. Check that its pages are legible."
            if extension == ".pdf"
            else "The selected file is empty."
        )
        raise DocumentExtractionError(message)
    if len(extracted) > max_chars:
        raise DocumentExtractionError("The document contains too much text for Discovery.")
    return name, extracted, page_count, warnings


def _extract_pdf(
    name: str,
    data: bytes,
    *,
    max_pdf_pages: int,
    artifacts_path: str,
    timeout_seconds: float,
) -> tuple[str, int, list[str]]:
    # ISO PDF permits the header to occur within the first 1024 bytes.
    if b"%PDF-" not in data[:1024]:
        raise DocumentExtractionError("The selected file is not a valid PDF.")
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise DocumentExtractionError("Password protected PDFs cannot be read.")
        page_count = len(reader.pages)
        if page_count > max_pdf_pages:
            raise DocumentExtractionError(
                f"This PDF has too many pages. Use at most {max_pdf_pages} pages."
            )
        if page_count == 0:
            raise DocumentExtractionError("The selected PDF has no pages.")
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("This PDF could not be read. Try another file.") from exc

    if not Path(artifacts_path).is_dir():
        raise DocumentExtractionError(
            "PDF reading is not ready on this server. Please try again later."
        )

    try:
        converter = _get_pdf_converter(str(Path(artifacts_path).resolve()), timeout_seconds)
        result = converter.convert(DocumentStream(name=name, stream=BytesIO(data)))
        if result.status in {ConversionStatus.FAILURE, ConversionStatus.SKIPPED}:
            raise DocumentExtractionError(
                "This PDF could not be read. Try a clearer or unprotected copy."
            )
        transcript = unescape(
            result.document.export_to_markdown(
                included_content_layers={ContentLayer.BODY, ContentLayer.FURNITURE},
                page_break_placeholder="\n\n--- Page break ---\n\n",
            )
        )
        warnings = []
        if result.status is ConversionStatus.PARTIAL_SUCCESS or result.errors:
            warnings.append("Some PDF content may need review. Check the complete preview.")
        if len(result.pages) < page_count:
            warnings.append(
                f"The PDF has {page_count} pages; only {len(result.pages)} were processed."
            )
        return transcript, page_count, warnings
    except DocumentExtractionError:
        raise
    except TimeoutError as exc:
        raise DocumentExtractionError(
            "PDF reading took too long. Try a smaller or simpler PDF."
        ) from exc
    except Exception as exc:
        raise DocumentExtractionError(
            "This PDF could not be read. Try a clearer or unprotected copy."
        ) from exc
