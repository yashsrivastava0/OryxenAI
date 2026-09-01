"""Small lexical helpers shared by generated-source contract checks."""

from __future__ import annotations

import re


def strip_source_comments(value: str) -> str:
    """Remove real source comments without truncating quoted URL strings.

    The Code Generator intentionally keeps its trusted source audits
    dependency-free.  A regular expression cannot distinguish ``//`` in a
    comment from ``//`` in a JavaScript string such as an HTTPS URL, so use a
    small quote-aware scanner instead.  Removed characters become spaces and
    line endings are preserved, which keeps later line/ordering diagnostics
    stable.
    """

    result: list[str] = []
    index = 0
    quote = ""
    length = len(value)
    while index < length:
        character = value[index]
        if quote:
            result.append(character)
            if character == "\\" and index + 1 < length:
                index += 1
                result.append(value[index])
            elif character == quote:
                quote = ""
            index += 1
            continue

        if character in {'"', "'", "`"}:
            quote = character
            result.append(character)
            index += 1
            continue

        if value.startswith("<!--", index):
            end = value.find("-->", index + 4)
            end = length if end < 0 else end + 3
            result.extend(
                "\n" if item == "\n" else "\r" if item == "\r" else " " for item in value[index:end]
            )
            index = end
            continue

        if value.startswith("/*", index):
            end = value.find("*/", index + 2)
            end = length if end < 0 else end + 2
            result.extend(
                "\n" if item == "\n" else "\r" if item == "\r" else " " for item in value[index:end]
            )
            index = end
            continue

        if value.startswith("//", index) and (index == 0 or value[index - 1] != ":"):
            end = index + 2
            while end < length and value[end] not in "\r\n":
                end += 1
            result.extend(" " for _ in value[index:end])
            index = end
            continue

        result.append(character)
        index += 1
    return "".join(result)


def _inside_jsx_opening_tag(value: str, position: int) -> bool:
    """Return whether ``position`` is top-level inside a static JSX opening tag.

    Work backward through possible ``<Tag`` starts, then scan each candidate
    forward while respecting quoted attribute values, comments, and JSX
    expression braces. This deliberately does not treat selector text inside
    ``querySelector('[data-x="y"]')`` as JSX attribute evidence.
    """

    search_before = position
    while search_before > 0:
        tag_start = value.rfind("<", 0, search_before)
        if tag_start < 0:
            return False
        search_before = tag_start
        tag = re.match(r"[A-Za-z_$][\w$.:~-]*", value[tag_start + 1 :])
        if tag is None:
            continue
        tag_name_end = tag_start + 1 + tag.end()
        if tag_name_end < len(value) and not (
            value[tag_name_end].isspace() or value[tag_name_end] in {"/", ">"}
        ):
            continue

        index = tag_name_end
        brace_depth = 0
        quote = ""
        line_comment = False
        block_comment = False
        closed = False
        while index < position:
            character = value[index]
            if line_comment:
                if character in "\r\n":
                    line_comment = False
                index += 1
                continue
            if block_comment:
                if value.startswith("*/", index):
                    block_comment = False
                    index += 2
                else:
                    index += 1
                continue
            if quote:
                if character == "\\" and index + 1 < position:
                    index += 2
                    continue
                if character == quote:
                    quote = ""
                index += 1
                continue
            if value.startswith("//", index):
                line_comment = True
                index += 2
                continue
            if value.startswith("/*", index):
                block_comment = True
                index += 2
                continue
            if character in {'"', "'", "`"}:
                quote = character
            elif character == "{":
                brace_depth += 1
            elif character == "}" and brace_depth:
                brace_depth -= 1
            elif character == ">" and brace_depth == 0:
                closed = True
                break
            index += 1
        if not closed and not quote and not line_comment and not block_comment and brace_depth == 0:
            return True
    return False


def static_jsx_attribute_values(value: str, attribute_name: str) -> list[tuple[int, str]]:
    """Return positions and values for literal attributes on JSX opening tags."""

    attribute = re.escape(attribute_name)
    pattern = re.compile(
        rf"(?<![\w:.-]){attribute}\s*=\s*(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
        re.DOTALL,
    )
    return [
        (match.start(), match.group("value"))
        for match in pattern.finditer(value)
        if _inside_jsx_opening_tag(value, match.start())
    ]
