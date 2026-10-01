"""Theme integrity: pinned bytes, referenced assets, vocabulary, exemplar drift."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from oryxenai.agents.code_generator.dev.reference_renderer import render_symbolic_body
from oryxenai.themes import ThemeError, compute_manifest_files, get_theme, load_package
from oryxenai.themes.editorial_forest.v1 import ROOT
from oryxenai.themes.editorial_forest.v1.contract import EditorialForestContract, monogram

_REPO = Path(__file__).resolve().parents[3]
# SHA-256 of the LF-normalized reviewed reference stylesheet. (The original CRLF file recorded in
# docs/architecture/10 hashes to 3a643eee...925ce; only the line endings differ.)
_PINNED_CSS_SHA256 = "a74260f29a014d4c28aa3cfc497094d4236194fafbbc476bc60177cf6bba612b"
CRLF = bytes([13, 10])
LF = bytes([10])


def test_theme_loads_and_pins_the_reviewed_stylesheet() -> None:
    theme = get_theme("editorial-forest/v1")
    assert theme.css_sha256 == _PINNED_CSS_SHA256
    assert theme.manifest["capabilities"] == {"javascript": False, "generated_css": False}


def test_stylesheet_matches_the_reference_fixture_modulo_line_endings() -> None:
    fixture = _REPO / "docs" / "pinned-theme" / "styles.css"
    if not fixture.exists():
        pytest.skip("reference fixture not present")
    assert fixture.read_bytes().replace(CRLF, LF) == (ROOT / "styles.css").read_bytes()


def test_theme_data_files_are_stored_byte_exact() -> None:
    attributes = (_REPO / ".gitattributes").read_text(encoding="utf-8")
    for pattern in ("*.css", "*.html", "*.json", "*.md", "*.txt", "*.svg"):
        assert f"src/oryxenai/themes/**/{pattern} -text" in attributes
    for path in ROOT.rglob("*"):
        if path.suffix in {".css", ".html", ".json", ".md", ".txt", ".svg"}:
            assert CRLF not in path.read_bytes(), path.name


def test_manifest_lists_every_file_with_matching_hashes() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    paths = [entry["path"] for entry in manifest["files"]]
    assert compute_manifest_files(ROOT, paths) == manifest["files"]


def test_every_asset_the_stylesheet_references_is_bundled() -> None:
    theme = get_theme()
    css = theme.stylesheet.data.decode("utf-8")
    referenced = set(re.findall(r"url\(\"\./([^\"]+)\"\)", css))
    assert referenced, "the stylesheet should reference its font files"
    missing = sorted(path for path in referenced if theme.file(path) is None)
    assert missing == []
    assert theme.file("assets/hero-visual.svg") is not None


def test_a_modified_theme_file_is_refused(tmp_path: Path) -> None:
    for entry in json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["files"]:
        target = tmp_path / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / entry["path"]).read_bytes())
    (tmp_path / "manifest.json").write_bytes((ROOT / "manifest.json").read_bytes())
    (tmp_path / "styles.css").write_bytes(b"body{}")
    with pytest.raises(ThemeError, match="immutable"):
        load_package(tmp_path, EditorialForestContract(tmp_path))


def test_unknown_theme_is_refused() -> None:
    with pytest.raises(ThemeError):
        get_theme("nope/v9")


def test_class_vocabulary_is_the_stylesheet_plus_declared_hooks() -> None:
    theme = get_theme()
    vocabulary = theme.contract.class_vocabulary()
    assert {
        "hero__headline",
        "pillar-grid",
        "capability-list",
        "destination-list__featured",
    } <= vocabulary
    assert "context-content__intro" in vocabulary  # declared hook class, unstyled
    assert "hero__title" not in vocabulary
    assert len(vocabulary) == 62


def test_fonts_ship_with_their_license_and_hashes() -> None:
    theme = get_theme()
    for weight in (400, 500, 600, 700):
        entry = theme.file(f"assets/fonts/space-grotesk-{weight}.woff2")
        assert entry is not None and entry.media_type == "font/woff2"
        assert hashlib.sha256(entry.data).hexdigest() == entry.sha256
        assert entry.data[:4] == b"wOF2"
    assert "SIL OPEN FONT LICENSE" in (ROOT / "LICENSE-fonts-OFL.txt").read_text(encoding="utf-8")


def test_the_prompt_exemplar_is_generated_by_the_reference_renderer() -> None:
    assert (ROOT / "exemplar.html").read_text(encoding="utf-8") == render_symbolic_body()


def test_prompt_contract_embeds_rules_and_exemplar() -> None:
    contract = get_theme().contract.prompt_contract()
    assert "<empty_fields>" in contract and '<a class="skip-link"' in contract
    assert contract.count("<exemplar>") == 1


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Dr. Aditya Vikram Joshi", "AVJ"),
        ("Arjun Mehta", "AM"),
        ("Maria de la Cruz Santos", "MCS"),
        ("Madonna", "M"),
        ("O'Brien Smith-Jones", "OS"),
        ("अनुराग शर्मा", "अश"),
        ("李 小龍", "李小"),
        ("Prof. Dame Jane Q. Public Jr.", "JQP"),
        ("a b c d e", "ABE"),
        ("  ", ""),
    ],
)
def test_monogram_derivation(name: str, expected: str) -> None:
    assert monogram(name) == expected


def test_head_is_host_owned_and_escapes_metadata() -> None:
    theme = get_theme()
    content = {"metadata": {"title": 'A & B <x> "q"', "description": "d's"}}
    head = theme.contract.render_head(content, {}, "fr-CA")
    assert head.startswith("<!doctype html>")
    assert '<html lang="fr-CA">' in head
    assert "<title>A &amp; B &lt;x&gt; &quot;q&quot;</title>" in head
    assert '<link rel="stylesheet" href="./styles.css">' in head
    assert "<script" not in head
    assert theme.contract.render_head(content, {}, "not a tag!").startswith(
        '<!doctype html>\n<html lang="en">'
    )
