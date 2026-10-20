"""Pure deterministic assembly from a public content projection and fixed TSX."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.agents.content_architect.schemas import PortfolioPageContent
from oryxenai.delivery.contracts import ADAPTER_REVISION, DeliveryError, safe_path, sha256
from oryxenai.themes import get_theme
from oryxenai.themes.contract import HostRenderedContract
from oryxenai.themes.lang import detect_language

TEMPLATES = Path(__file__).parent / "templates"
SUPPORTED_THEMES = frozenset(
    {
        "editorial-forest/v1",
        "editorial-forest-motion/v1",
        "cobalt-atlas/v1",
        "cobalt-atlas/v2",
        "obsidian-signal/v1",
        "claret-marquee/v1",
    }
)


def viewer_fingerprint() -> str:
    """Pin compatibility to the actual prebuilt React viewer bytes."""
    try:
        return sha256((TEMPLATES / "viewer.html").read_bytes())
    except OSError as exc:
        raise DeliveryError(
            "ADAPTER_BUILD_UNAVAILABLE",
            "Build the React delivery viewer before enabling sharing.",
            status_code=503,
        ) from exc


@dataclass(frozen=True)
class ReactProject:
    files: dict[str, bytes]
    portfolio: dict[str, Any]
    receipt: dict[str, Any]


def assemble_project(
    content_snapshot: dict[str, Any],
    theme_id: str,
    theme_sha256: str,
    source_sha256: str,
    *,
    max_bytes: int,
) -> ReactProject:
    if theme_id not in SUPPORTED_THEMES:
        raise DeliveryError(
            "UNSUPPORTED_THEME", "This theme revision has no verified React adapter."
        )
    theme = get_theme(theme_id)
    if theme.css_sha256 != theme_sha256:
        raise DeliveryError(
            "SOURCE_CHANGED", "The source theme does not match its immutable version."
        )
    contract = theme.contract
    if not isinstance(contract, HostRenderedContract):
        raise DeliveryError(
            "UNSUPPORTED_THEME", "This theme does not support deterministic React delivery."
        )
    # Explicit schema projection excludes all non-public session/review fields.
    try:
        content = PortfolioPageContent.model_validate(content_snapshot).model_dump(mode="json")
    except ValidationError as exc:
        raise DeliveryError(
            "CONTENT_INVALID", "The selected version has invalid public portfolio data."
        ) from exc
    derived = contract.derive(content)
    body = contract.render_body(content, derived)
    report = validate_page(body, content, theme, derived=derived, max_bytes=max_bytes)
    if not report.ok:
        raise DeliveryError(
            "CONTENT_INVALID", "The selected version no longer passes its pinned content contract."
        )
    try:
        template_manifest = json.loads(
            (TEMPLATES / "template-manifest.json").read_text(encoding="utf-8")
        )
        files = {
            safe_path(path): (TEMPLATES / path).read_bytes() for path in template_manifest["files"]
        }
    except (OSError, ValueError, KeyError) as exc:
        raise DeliveryError(
            "ADAPTER_BUILD_UNAVAILABLE",
            "Build the React delivery templates before enabling sharing.",
            status_code=503,
        ) from exc
    for path, data in files.items():
        if sha256(data) != template_manifest["files"][path]:
            raise DeliveryError(
                "ADAPTER_BUILD_INVALID",
                "The React adapter build failed integrity verification.",
                status_code=503,
            )
    lang = detect_language(content, contract.default_language)
    head = contract.render_head(content, derived, lang)
    body_class = re.search(r'<body\b[^>]*\bclass="([^"]*)"', head)
    if derived.get("hero_asset"):
        derived["hero_asset"] = "./theme/" + str(derived["hero_asset"]).removeprefix("./")
    portfolio = {
        "schema": "ReactPortfolio/v1",
        "theme_id": theme_id,
        "adapter_revision": ADAPTER_REVISION,
        "lang": lang,
        "body_class": body_class[1] if body_class else "",
        "stylesheet": "./theme/" + theme.stylesheet.path,
        "c": content,
        "d": derived,
    }
    files["portfolio.json"] = (json.dumps(portfolio, ensure_ascii=False, indent=2) + "\n").encode()
    for asset in theme.files.values():
        if asset.path.endswith((".js", ".html")):
            continue
        files[safe_path("public/theme/" + asset.path)] = asset.data
    # License text can be outside a theme's serving manifest.
    theme_root = getattr(contract, "root", getattr(contract, "_root", None))
    if theme_root:
        for license_path in Path(theme_root).rglob("*.txt"):
            if license_path.name.upper().startswith(("OFL", "LICENSE")):
                files[
                    safe_path("public/theme/" + license_path.relative_to(theme_root).as_posix())
                ] = license_path.read_bytes()
    receipt = {
        "schema": "ReactDeliveryReceipt/v1",
        "source_sha256": source_sha256,
        "adapter_revision": ADAPTER_REVISION,
        "adapter_sources_sha256": template_manifest["adapter_sources_sha256"],
        "viewer_sha256": viewer_fingerprint(),
        "theme_id": theme_id,
        "theme_sha256": theme_sha256,
        "model_calls": 0,
        "data_validation": "passed",
        "template_checks": template_manifest["checks"],
        "browser_verification": "not_run_for_this_portfolio",
    }
    files["delivery-receipt.json"] = (json.dumps(receipt, indent=2) + "\n").encode()
    files["README.md"] = (
        b"# React portfolio\n\nRun `npm ci`, `npm run typecheck`, `npm run build`, then `npm run dev`.\nThis project is independent of OryxenAI after import. Edit portfolio.json and src/themes/ to enhance it.\nThe delivery receipt distinguishes template checks from per-portfolio validation.\n"
    )
    files["project-manifest.json"] = (
        json.dumps(
            {
                "schema": "ReactProjectFiles/v1",
                "files": [
                    {"path": path, "bytes": len(data), "sha256": sha256(data)}
                    for path, data in sorted(files.items())
                ],
            },
            indent=2,
        )
        + "\n"
    ).encode()
    if len(files) > 256:
        raise DeliveryError("PROJECT_TOO_LARGE", "This project exceeds the supported file count.")
    if (
        sum(len(data) for data in files.values()) + (TEMPLATES / "viewer.html").stat().st_size
        > max_bytes
    ):
        raise DeliveryError(
            "PROJECT_TOO_LARGE", "This project exceeds the configured handoff size limit."
        )
    return ReactProject(files, portfolio, receipt)
