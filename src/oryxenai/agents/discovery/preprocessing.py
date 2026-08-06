"""Deterministic preprocessing for Discovery input.

Normalizes, deduplicates, and compacts user input before model consumption.
Never mutates the original input.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from oryxenai.agents.discovery.schemas import DiscoveryWarning


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def remove_unsafe_control_characters(text: str) -> str:
    safe = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x20 and ch not in ("\n", "\t", "\r"):
            continue
        if 0x7F <= cp <= 0x9F:
            continue
        safe.append(ch)
    return "".join(safe)


def trim_repeated_blank_lines(text: str, max_consecutive: int = 2) -> str:
    result: list[str] = []
    blank_count = 0
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "":
            blank_count += 1
            if blank_count <= max_consecutive:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result)


def deduplicate_lines(text: str, similarity_threshold: float = 0.85) -> str:
    lines = text.split("\n")
    seen: list[tuple[str, str]] = []
    result: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append(line)
            continue
        is_dup = False
        for _prev_line, prev_stripped in seen:
            if _line_similarity(stripped, prev_stripped) >= similarity_threshold:
                is_dup = True
                break
        if not is_dup:
            seen.append((line, stripped))
            result.append(line)

    return "\n".join(result)


def deduplicate_sections(text: str) -> str:
    lines = text.split("\n")
    sections: list[tuple[int, int, str]] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if _is_section_header(stripped) and _section_body_same_after(text, lines, i):
            i += 1
            continue
        sections.append((i, i, lines[i]))
        i += 1
    return "\n".join(line for _, _, line in sections)


def compact_resume(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False

    sections = _split_resume_sections(text)
    if not sections:
        # No recognizable section headers: keep the head and record the
        # compaction decision so long, header-less input is always bounded.
        return text[:max_chars], True

    prioritized = _prioritize_sections(sections)
    result_parts: list[str] = []
    remaining = max_chars

    for title, content in prioritized:
        part = f"{title}\n{content}\n"
        if len(part) <= remaining:
            result_parts.append(part)
            remaining -= len(part)
        else:
            truncated = part[:remaining]
            if truncated:
                result_parts.append(truncated)
            break

    compacted = "".join(result_parts)
    return compacted, True


def normalize_url(url_str: str) -> str:
    """Normalize a URL: lowercase scheme/host, strip tracking params."""
    from urllib.parse import unquote, urlparse, urlunparse

    try:
        parsed = urlparse(unquote(url_str))
    except (ValueError, UnicodeDecodeError):
        return url_str
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    normalized = urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))
    return normalized


def compute_source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def preprocess_text(
    text: str,
    max_chars: int | None = None,
    remove_duplicates: bool = True,
) -> tuple[str, list[DiscoveryWarning]]:
    warnings: list[DiscoveryWarning] = []
    original_len = len(text)

    text = normalize_line_endings(text)
    text = normalize_unicode(text)
    text = remove_unsafe_control_characters(text)
    text = trim_repeated_blank_lines(text)

    if remove_duplicates:
        text = deduplicate_lines(text)

    if max_chars and len(text) > max_chars:
        text, compacted = compact_resume(text, max_chars)
        if compacted:
            warnings.append(
                DiscoveryWarning(
                    code="resume_input_compacted",
                    message=(
                        f"Resume was compacted from {original_len} to {len(text)} "
                        f"characters. Repeated or low-information text was reduced."
                    ),
                    details={"original_length": original_len, "compacted_length": len(text)},
                )
            )

    return text, warnings


# ── Internal helpers ─────────────────────────────────────────────────────────


def _line_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return 0.0
    intersection = a_words & b_words
    union = a_words | b_words
    return len(intersection) / len(union)


def _is_section_header(line: str) -> bool:
    stripped = line.strip().rstrip(":")
    if not stripped:
        return False
    if len(stripped) > 60:
        return False
    if stripped.upper() == stripped and len(stripped) < 40:
        return True
    headers = {
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "education",
        "skills",
        "technical skills",
        "certifications",
        "awards",
        "projects",
        "publications",
        "languages",
        "contact",
        "summary",
        "profile",
        "objective",
        "qualifications",
        "achievements",
        "volunteer",
        "interests",
        "references",
    }
    return stripped.lower() in headers


def _section_body_same_after(full_text: str, lines: list[str], start: int) -> bool:
    """Simple heuristic: check if next section header follows within 5 lines."""
    for j in range(start + 1, min(start + 6, len(lines))):
        if _is_section_header(lines[j].strip()):
            return True
    return False


def _split_resume_sections(text: str) -> list[tuple[str, str]]:
    section_pattern = re.compile(r"^([A-Z][A-Z\s&/\-]{1,40}):?$", re.MULTILINE)
    sections: list[tuple[str, str]] = []
    matches = list(section_pattern.finditer(text))

    if not matches:
        return [("", text)]

    title_start = matches[0].start()
    if title_start > 0:
        sections.append(("", text[:title_start]))

    for idx, match in enumerate(matches):
        title = match.group(0).strip().rstrip(":")
        body_start = match.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((title, body))

    return sections


def _prioritize_sections(
    sections: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    priority = {
        "": 0,
        "summary": 1,
        "profile": 1,
        "objective": 1,
        "experience": 2,
        "work experience": 2,
        "professional experience": 2,
        "employment": 2,
        "employment history": 2,
        "projects": 3,
        "education": 4,
        "skills": 5,
        "technical skills": 5,
        "certifications": 6,
        "awards": 6,
        "publications": 7,
        "languages": 8,
        "contact": 9,
    }
    return sorted(sections, key=lambda s: priority.get(s[0].lower(), 10))
