"""Claret Marquee v1: pinned bytes, closed-world markup, routes, labels, budgets and safety."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from oryxenai.agents.code_generator.admission import content_admission_issues
from oryxenai.agents.code_generator.bundle import build_bundle
from oryxenai.agents.code_generator.serving import (
    ServedBundle,
    bundle_integrity_ok,
    preview_headers,
)
from oryxenai.agents.code_generator.validate import DEFAULT_MAX_BODY_BYTES, validate_page
from oryxenai.themes import (
    ThemeError,
    compute_manifest_files,
    get_theme,
    list_theme_ids,
    load_package,
    uses_atlas_content,
)
from oryxenai.themes.claret_marquee.v1 import contract as marquee
from oryxenai.themes.claret_marquee.v1.contract import (
    ILLUSTRATIVE_LABEL,
    SAMPLE_LABEL,
    MarqueeContract,
    exemplar_content,
)
from tests.unit.themes.atlas_fixtures import ALLOW_ILLUSTRATIVE, FIXTURES

THEME_ID = "claret-marquee/v1"
THEME = get_theme(THEME_ID)
ROOT = Path(marquee.__file__).resolve().parent
_REPO = Path(__file__).resolve().parents[3]
CRLF = bytes([13, 10])
NAMES = sorted(FIXTURES)

# Budgets (targets): the whole theme must stay small enough to be previewed instantly.
MAX_CSS_BYTES = 80_000
MAX_JS_BYTES = 46_000
MAX_FONT_BYTES = 230_000


def _body(content: dict[str, Any]) -> str:
    return THEME.contract.render_body(content)  # type: ignore[attr-defined,no-any-return]


def _codes(content: dict[str, Any], body: str) -> set[str]:
    return {issue.code for issue in validate_page(body, content, THEME).errors}


def test_registry_exposes_a_scripted_atlas_theme() -> None:
    assert THEME_ID in list_theme_ids()
    assert get_theme(THEME_ID) is THEME
    assert THEME.theme_id == THEME.contract.theme_id == THEME_ID
    assert THEME.allows_scripts
    assert THEME.manifest["runtime"] == {"global": "PortfolioTheme"}
    assert uses_atlas_content(THEME_ID) and uses_atlas_content("cobalt-atlas/v2")
    assert not uses_atlas_content("obsidian-signal/v1")
    assert not uses_atlas_content("")


def test_manifest_lists_every_served_file_with_matching_hashes() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    paths = [entry["path"] for entry in manifest["files"]]
    assert compute_manifest_files(ROOT, paths) == manifest["files"]
    assert set(paths) == {
        "style.css",
        "theme.js",
        "assets/fonts/bodoni-moda-roman.woff2",
        "assets/fonts/bodoni-moda-italic.woff2",
        "assets/fonts/hanken-grotesk.woff2",
        "assets/fonts/dm-mono-500.woff2",
    }
    assert manifest["stylesheet"] == "style.css" and manifest["script"] == "theme.js"
    assert manifest["capabilities"] == {"javascript": True, "generated_css": False}


def test_theme_data_files_are_stored_byte_exact() -> None:
    attributes = (_REPO / ".gitattributes").read_text(encoding="utf-8")
    for pattern in ("*.css", "*.js", "*.json", "*.md", "*.txt"):
        assert f"src/oryxenai/themes/**/{pattern} -text" in attributes
    assert "src/oryxenai/themes/**/*.woff2 binary" in attributes
    for path in ROOT.rglob("*"):
        if path.suffix in {".css", ".js", ".json", ".md", ".txt", ".j2", ".py"}:
            assert CRLF not in path.read_bytes(), path.name


def test_a_modified_theme_file_is_refused(tmp_path: Path) -> None:
    for entry in json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["files"]:
        target = tmp_path / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / entry["path"]).read_bytes())
    (tmp_path / "manifest.json").write_bytes((ROOT / "manifest.json").read_bytes())
    (tmp_path / "style.css").write_bytes(b"body{}")
    with pytest.raises(ThemeError, match="immutable"):
        load_package(tmp_path, MarqueeContract(tmp_path))


def test_every_asset_the_stylesheet_references_is_bundled() -> None:
    css = THEME.stylesheet.data.decode("utf-8")
    referenced = set(re.findall(r"url\(\"\./([^\"]+)\"\)", css))
    assert referenced, "the stylesheet should reference its font files"
    assert sorted(path for path in referenced if THEME.file(path) is None) == []


def test_fonts_ship_with_their_licences_and_stay_within_budget() -> None:
    total = 0
    for entry in THEME.files.values():
        if entry.path.endswith(".woff2"):
            assert entry.media_type == "font/woff2" and entry.data[:4] == b"wOF2"
            total += len(entry.data)
    assert 0 < total <= MAX_FONT_BYTES
    for name in ("bodoni-moda", "hanken-grotesk", "dm-mono"):
        licence = (ROOT / f"LICENSE-{name}-OFL.txt").read_text(encoding="utf-8")
        assert "SIL OPEN FONT LICENSE" in licence


def test_script_and_stylesheet_stay_small_and_self_contained() -> None:
    css = THEME.stylesheet.data.decode("utf-8")
    script = THEME.file("theme.js")
    assert script is not None
    assert len(css.encode()) <= MAX_CSS_BYTES and len(script.data) <= MAX_JS_BYTES
    source = script.data.decode("utf-8")
    forbidden = (
        r"\beval\s*\(",
        r"new\s+Function",
        r"\bfetch\s*\(",
        r"XMLHttpRequest",
        r"WebSocket",
        r"sendBeacon",
        r"\.innerHTML",
        r"document\.write",
        r"\bimport\s*\(",
        r"\bimportScripts",
    )
    for pattern in forbidden:
        assert not re.search(pattern, source), pattern
    assert "@import" not in css
    external = set(re.findall(r"https?://[^\s\"')]+", css))
    assert external <= {"http://www.w3.org/2000/svg"}


def test_class_vocabulary_covers_the_stylesheet_without_the_layer_trap() -> None:
    css = THEME.stylesheet.data.decode("utf-8")
    # A bare `@layer a,b;` statement directly before a style rule swallows that rule's classes.
    assert not re.search(r"@layer[^{};]*;\s*[^@\s]", css)
    vocabulary = THEME.contract.class_vocabulary()
    assert {"hero", "hero-name", "topbar", "route-view", "case-page", "poster", "figure-value"} <= (
        vocabulary
    )
    assert {"portrait", "destination", "ledger-row", "meta", "to-top", "pillar"} <= vocabulary


@pytest.mark.parametrize("name", NAMES)
def test_every_fixture_is_admitted_and_renders_a_valid_deterministic_body(name: str) -> None:
    content = FIXTURES[name]()
    admission = content_admission_issues(
        content, theme_id=THEME_ID, allow_illustrative_work=name in ALLOW_ILLUSTRATIVE
    )
    assert not admission, [issue.to_dict() for issue in admission]
    body = _body(content)
    report = validate_page(body, content, THEME)
    assert report.ok, [issue.to_dict() for issue in report.errors]
    assert body == _body(deepcopy(content))
    assert len(body.encode()) < DEFAULT_MAX_BODY_BYTES
    # No server-side word or letter splitting: the closed-world validator compares whole strings.
    assert 'class="w"' not in body


def test_exemplar_validates_and_contains_only_placeholders() -> None:
    content = exemplar_content()
    body = _body(content)
    assert validate_page(body, content, THEME).ok
    assert "{hero.name}" in body and "{atlas.projects[2].title}" in body
    for literal in ("Example Name", "Useful", "An approved introduction."):
        assert literal not in body
    prompt = THEME.contract.prompt_contract()
    assert "<exemplar>" in prompt and "never write a script" in prompt.lower()


def test_exemplar_composes_titles_and_labels_from_placeholders() -> None:
    body = _body(exemplar_content())
    assert 'aria-label="{atlas.projects[0].title} case study"' in body
    assert 'data-title="{metadata.title}"' in body
    assert 'data-title="{atlas.projects[0].title} — {hero.name}"' in body
    assert "{derived.monogram}" in body


def test_the_render_command_writes_a_complete_servable_bundle(tmp_path: Path) -> None:
    from argparse import Namespace

    from oryxenai.agents.code_generator.cli import _command_render

    source = tmp_path / "content.json"
    source.write_text(json.dumps(FIXTURES["designer"]()), encoding="utf-8")
    output = tmp_path / "render"
    args = Namespace(sample=None, content=str(source), theme=THEME_ID, out=output)
    assert _command_render(args) == 0
    for entry in THEME.files.values():
        assert (output / entry.path).read_bytes() == entry.data
    html = (output / "index.html").read_text(encoding="utf-8")
    assert "Maya Kapoor" in html and '<script src="./theme.js" defer></script>' in html


def test_case_routes_follow_the_project_position_even_with_gaps() -> None:
    body = _body(FIXTURES["engineer"]())
    ids = re.findall(r'<article class="route-view[^"]*" id="([^"]+)"', body)
    assert ids == ["home", "about", "case-1", "case-3"]
    designer = re.findall(
        r'<article class="route-view[^"]*" id="([^"]+)"', _body(FIXTURES["designer"]())
    )
    assert designer == ["home", "about", "case-1", "case-2", "case-3"]


def test_empty_sections_have_designed_fallbacks() -> None:
    content = FIXTURES["chef"]()
    body = _body(content)
    assert 'class="proof"' not in body and 'class="worked-with"' not in body
    assert 'class="ticker"' not in body
    content["atlas"]["projects"] = []
    sparse = _body(content)
    assert validate_page(sparse, content, THEME).ok
    assert 'class="work-empty"' in sparse and 'id="case-' not in sparse


def test_sample_and_illustrative_labels_are_printed_where_required() -> None:
    content = FIXTURES["sparse_samples"]()
    body = _body(content)
    assert body.count(SAMPLE_LABEL) == 3
    assert body.count(ILLUSTRATIVE_LABEL) >= 2
    without_label = body.replace(f'<p class="meta">{SAMPLE_LABEL}</p>', "", 1)
    assert "MARQUEE_SAMPLE_LABEL" in _codes(content, without_label)
    unlabelled = body.replace(ILLUSTRATIVE_LABEL, "Selected project", 1)
    assert "MARQUEE_ILLUSTRATIVE_LABEL" in _codes(content, unlabelled)


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda b: b + "<script>alert(1)</script>", "TAG_NOT_ALLOWED"),
        (
            lambda b: b.replace('<a class="skip-link"', '<a onclick="x()" class="skip-link"', 1),
            "ATTRIBUTE_FORBIDDEN",
        ),
        (
            lambda b: b.replace(
                '<span class="hero-ring">', '<span style="x:y" class="hero-ring">', 1
            ),
            "ATTRIBUTE_FORBIDDEN",
        ),
        (lambda b: b.replace('data-art="aperture"', 'data-art="neon"', 1), "MARQUEE_ART"),
        (lambda b: b.replace('id="about"', 'id="gone"', 1), "MARQUEE_ROUTES"),
        (
            lambda b: b.replace("mailto:maya@example.com", "https://evil.example", 1),
            "URL_NOT_ALLOWED",
        ),
        (lambda b: b.replace('data-len="s"', 'data-len="huge"', 1), "MARQUEE_SIZE"),
        (
            lambda b: b.replace(
                'data-field="hero.name">Maya Kapoor<', 'data-field="hero.name">Someone Else<', 1
            ),
            "MARQUEE_FIELD",
        ),
    ],
)
def test_hostile_or_drifting_markup_is_rejected(mutate: Any, expected: str) -> None:
    content = FIXTURES["designer"]()
    assert expected in _codes(content, mutate(_body(content)))


def test_head_is_escaped_directional_and_loads_the_fixed_assets() -> None:
    content = FIXTURES["designer"]()
    content["metadata"]["title"] = 'Tom & <Jerry> "Q"'
    derived = THEME.contract.derive(content)
    head = THEME.contract.render_head(content, derived, "ar")
    assert 'dir="rtl"' in head and 'lang="ar"' in head
    assert "Tom &amp; &lt;Jerry&gt; &quot;Q&quot;" in head
    assert '<link rel="icon" href="data:,">' in head
    assert '<link rel="stylesheet" href="./style.css">' in head
    assert '<script src="./theme.js" defer></script>' in head
    assert 'dir="rtl"' not in THEME.contract.render_head(content, derived, "en")
    assert THEME.contract.render_head(content, derived, "not a tag").count('lang="en"') == 1


def test_size_classes_scale_with_text_length() -> None:
    short = FIXTURES["designer"]()
    long = FIXTURES["stress"]()
    assert THEME.contract.derive(short)["len"]["name"] == "s"
    assert THEME.contract.derive(long)["len"]["name"] == "xl"
    assert THEME.contract.derive(long)["len"]["headline"] == "xl"


def test_scripted_preview_checks_all_assets_and_keeps_the_opaque_sandbox() -> None:
    content = FIXTURES["designer"]()
    bundle = build_bundle(content, THEME.contract.derive(content), _body(content), "en", THEME)
    served = ServedBundle(
        bundle.index_html, bundle.theme_id, bundle.css_sha256, bundle.index_sha256, bundle.manifest
    )
    assert bundle_integrity_ok(served, THEME)
    assert not bundle_integrity_ok(
        ServedBundle(
            served.index_html,
            served.theme_id,
            served.theme_sha256,
            served.index_sha256,
            {"files": []},
        ),
        THEME,
    )
    policy = preview_headers(html=True, scripts=True)["Content-Security-Policy"]
    assert "script-src 'self'" in policy and "sandbox allow-scripts" in policy
    assert "allow-same-origin" not in policy
