"""Bounded text extraction for user supplied Discovery source documents."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePath

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


class DocumentExtractionError(ValueError):
    """A safe reason that an uploaded source cannot be used."""


def extract_document(
    filename: str,
    data: bytes,
    *,
    max_chars: int,
    max_bytes: int,
    max_pdf_pages: int,
) -> tuple[str, str]:
    """Return a display name and readable text without retaining file bytes."""
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

    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise DocumentExtractionError("The selected file is not a valid PDF.")
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            if reader.is_encrypted:
                raise DocumentExtractionError("Password protected PDFs cannot be read.")
            if len(reader.pages) > max_pdf_pages:
                raise DocumentExtractionError(
                    f"This PDF has too many pages. Use at most {max_pdf_pages} pages."
                )
            parts: list[str] = []
            total = 0
            for page in reader.pages:
                page_text = page.extract_text() or ""
                total += len(page_text) + 1
                if total > max_chars:
                    raise DocumentExtractionError(
                        "The document contains too much text for Discovery."
                    )
                parts.append(page_text)
            extracted = "\n".join(parts)
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError("This PDF could not be read. Try another file.") from exc
    else:
        try:
            extracted = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError("This text file must use UTF-8 encoding.") from exc

    if not extracted.strip():
        raise DocumentExtractionError(
            "No selectable text was found. Scanned image PDFs need text recognition first."
        )
    if len(extracted) > max_chars:
        raise DocumentExtractionError("The document contains too much text for Discovery.")
    return name, extracted
