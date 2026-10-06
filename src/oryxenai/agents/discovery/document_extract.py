"""Bounded, structure-aware extraction for user supplied Explorer documents."""

from __future__ import annotations

import gc
import logging
import time
from functools import lru_cache
from html import unescape
from io import BytesIO
from pathlib import Path, PurePath
from typing import Literal

from pypdf import PdfReader

logger = logging.getLogger(__name__)
PAGE_BREAK = "\n\n--- Page break ---\n\n"
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


class DocumentExtractionError(ValueError):
    """A safe reason that an uploaded source cannot be used."""


@lru_cache(maxsize=4)
def _get_pdf_converter(artifacts_path: str, timeout_seconds: float) -> object:
    """Keep one CPU OCR/layout pipeline per process and artifact directory."""
    try:
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            HeadingHierarchyOptions,
            OcrMode,
            PdfPipelineOptions,
            RapidOcrOptions,
        )
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as exc:
        logger.exception("Docling PDF engine is unavailable")
        raise DocumentExtractionError(
            "PDF reading is not ready on this server. Please try again later."
        ) from exc

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
    engine: Literal["docling", "light"] = "docling",
    light_ocr: bool = True,
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
            engine=engine,
            light_ocr=light_ocr,
        )
    else:
        try:
            # utf-8-sig accepts ordinary UTF-8 and removes a BOM, if present.
            extracted = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError("This text file must use UTF-8 encoding.") from exc

    if not extracted.strip():
        message = "The selected file is empty."
        if extension == ".pdf":
            message = (
                "This PDF has no selectable text. Export it as a text-based PDF or paste the text."
                if engine == "light" and not light_ocr
                else "No readable text was found in this PDF. Check that its pages are legible."
            )
        raise DocumentExtractionError(message)
    if len(extracted) > max_chars:
        raise DocumentExtractionError("The document contains too much text for Explorer.")
    return name, extracted, page_count, warnings


def _extract_pdf(
    name: str,
    data: bytes,
    *,
    max_pdf_pages: int,
    artifacts_path: str,
    timeout_seconds: float,
    engine: Literal["docling", "light"],
    light_ocr: bool,
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

    if engine == "light":
        transcript, warnings = _extract_pdf_light(
            data, page_count, timeout_seconds=timeout_seconds, light_ocr=light_ocr
        )
        return transcript, page_count, warnings

    if not Path(artifacts_path).is_dir():
        raise DocumentExtractionError(
            "PDF reading is not ready on this server. Please try again later."
        )

    try:
        from docling.datamodel.base_models import ConversionStatus
        from docling_core.types.doc.common.content_layer import ContentLayer
        from docling_core.types.io import DocumentStream

        converter = _get_pdf_converter(str(Path(artifacts_path).resolve()), timeout_seconds)
        result = converter.convert(DocumentStream(name=name, stream=BytesIO(data)))  # type: ignore[attr-defined]
        if result.status in {ConversionStatus.FAILURE, ConversionStatus.SKIPPED}:
            raise DocumentExtractionError(
                "This PDF could not be read. Try a clearer or unprotected copy."
            )
        transcript = unescape(
            result.document.export_to_markdown(
                included_content_layers={ContentLayer.BODY, ContentLayer.FURNITURE},
                page_break_placeholder=PAGE_BREAK,
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
    except ImportError as exc:
        logger.exception("Docling PDF engine is unavailable")
        raise DocumentExtractionError(
            "PDF reading is not ready on this server. Please try again later."
        ) from exc
    except TimeoutError as exc:
        raise DocumentExtractionError(
            "PDF reading took too long. Try a smaller or simpler PDF."
        ) from exc
    except Exception as exc:
        raise DocumentExtractionError(
            "This PDF could not be read. Try a clearer or unprotected copy."
        ) from exc


@lru_cache(maxsize=1)
def _get_light_ocr() -> object:
    from rapidocr import RapidOCR

    return RapidOCR()


def _ocr_page(bitmap: object) -> str:
    result = _get_light_ocr()(bitmap.to_numpy())  # type: ignore[operator, attr-defined]
    return "\n".join(result.txts or ())


def _extract_pdf_light(
    data: bytes, page_count: int, *, timeout_seconds: float, light_ocr: bool
) -> tuple[str, list[str]]:
    import pypdfium2 as pdfium  # type: ignore[import-untyped]

    deadline = time.monotonic() + timeout_seconds
    pages: list[str] = []
    try:
        document = pdfium.PdfDocument(data)
        try:
            for index in range(page_count):
                if time.monotonic() >= deadline:
                    raise TimeoutError
                page = document.get_page(index)
                try:
                    text_page = page.get_textpage()
                    try:
                        extracted = text_page.get_text_range().rstrip()
                    finally:
                        text_page.close()
                    if len("".join(extracted.split())) < 20 and light_ocr:
                        bitmap = page.render(scale=1.5)
                        try:
                            recognised = _ocr_page(bitmap).strip()
                        finally:
                            bitmap.close()
                        if len(recognised) > len(extracted.strip()):
                            extracted = recognised
                    pages.append(extracted)
                finally:
                    page.close()
                    gc.collect()
                if time.monotonic() >= deadline:
                    raise TimeoutError
        finally:
            document.close()
    except TimeoutError as exc:
        raise DocumentExtractionError(
            "PDF reading took too long. Try a smaller or simpler PDF."
        ) from exc
    except DocumentExtractionError:
        raise
    except Exception as exc:
        logger.exception("Light PDF extraction failed")
        raise DocumentExtractionError(
            "This PDF could not be read. Try a clearer or unprotected copy."
        ) from exc
    return PAGE_BREAK.join(pages), [
        "Layout and tables are simplified on this server; review the text."
    ]
