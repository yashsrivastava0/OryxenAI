"""Content admission, bundle sealing, failure envelopes, and runtime isolation."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from oryxenai.agents.code_generator.admission import content_admission_issues
from oryxenai.agents.code_generator.bundle import build_bundle, resolve_bundle_file
from oryxenai.agents.code_generator.dev.reference_renderer import render_body
from oryxenai.agents.code_generator.diagnostics import (
    failure_from_admission,
    failure_from_provider_error,
    failure_from_validation,
    failure_unexpected,
    failure_worker_lost,
)
from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.agents.shared.providers.errors import (
    ModelJsonInvalidError,
    ModelOutputTruncatedError,
    ProviderAuthError,
    ProviderTimeoutError,
)
from oryxenai.themes import get_theme
from tests.unit.agents.code_generator.helpers import minimal_content, sample_content

THEME = get_theme()


# ── admission ────────────────────────────────────────────────────────────────


def _issues(mutate) -> list:  # type: ignore[no-untyped-def]
    content = copy.deepcopy(sample_content("01_strong_profile"))
    mutate(content)
    return content_admission_issues(content)


def test_missing_required_copy_is_reported_by_field() -> None:
    issues = _issues(lambda c: c["hero"].update(name=""))
    assert issues and issues[0].code == "CONTENT_INCOMPLETE" and issues[0].path == "hero.name"


def test_wrong_pillar_count_is_reported() -> None:
    issues = _issues(lambda c: c["systems_practice"]["pillars"].pop())
    assert any("pillars" in (issue.path or "") for issue in issues)


def test_unsafe_destination_scheme_is_refused() -> None:
    issues = _issues(lambda c: c["connect"]["destinations"][0].update(url="javascript:alert(1)"))
    assert any("destinations[0]" in (issue.path or "") for issue in issues)


@pytest.mark.parametrize(
    ("mutate", "path"),
    [
        (lambda c: c["hero"].update(intro="x" * 1500), "hero.intro"),
        (lambda c: c.update(marquee_keywords=[f"k{n}" for n in range(30)]), "marquee_keywords"),
        (
            lambda c: c["technical_capabilities"].update(
                groups=[
                    {"heading": f"G{g}", "items": [f"i{g}.{n}" for n in range(30)]}
                    for g in range(9)
                ]
            ),
            "technical_capabilities.groups",
        ),
        (
            lambda c: c["professional_context"].update(organizations=[f"O{n}" for n in range(40)]),
            "professional_context.organizations",
        ),
        (
            lambda c: c["connect"].update(
                destinations=[
                    {"label": f"L{n}", "url": f"https://e.example/{n}", "featured": False}
                    for n in range(15)
                ]
            ),
            "connect.destinations",
        ),
    ],
)
def test_oversized_content_is_refused_before_any_model_call(mutate, path: str) -> None:  # type: ignore[no-untyped-def]
    issues = _issues(mutate)
    assert issues and all(issue.code == "CONTENT_LIMIT_EXCEEDED" for issue in issues)
    assert any(issue.path == path or (issue.path or "").startswith(path) for issue in issues)


def test_admission_failure_names_every_field_and_is_not_retryable() -> None:
    issues = _issues(lambda c: c["hero"].update(name="", intro=""))
    envelope = failure_from_admission(issues, reference="cg-test")
    assert envelope.stage == "start" and envelope.owner == "content" and not envelope.retryable
    assert {location.ref for location in envelope.where} >= {"hero.name", "hero.intro"}
    assert envelope.reference == "cg-test"


# ── bundle ───────────────────────────────────────────────────────────────────


def test_bundle_is_host_head_plus_model_body_and_lists_theme_files_by_hash() -> None:
    content = minimal_content()
    derived = THEME.contract.derive(content)
    body = render_body(content, derived)
    bundle = build_bundle(content, derived, body, "en", THEME)
    assert bundle.index_html.startswith("<!doctype html>")
    assert "<title>Sam Lee</title>" in bundle.index_html
    assert bundle.index_html.rstrip().endswith("</html>")
    assert hashlib.sha256(bundle.index_html.encode()).hexdigest() == bundle.index_sha256
    paths = [entry["path"] for entry in bundle.manifest["files"]]
    assert paths[0] == "index.html" and "styles.css" in paths and "assets/hero-visual.svg" in paths
    css = next(entry for entry in bundle.manifest["files"] if entry["path"] == "styles.css")
    assert css["sha256"] == bundle.css_sha256 == THEME.css_sha256


def test_bundle_resolution_serves_index_and_theme_files_only() -> None:
    index = "<!doctype html><p>x</p>"
    served = resolve_bundle_file(index, THEME, "index.html")
    assert served is not None and served[0] == index.encode() and served[1].startswith("text/html")
    css = resolve_bundle_file(index, THEME, "styles.css")
    assert css is not None and css[0] == THEME.stylesheet.data and css[1].startswith("text/css")
    assert resolve_bundle_file(index, THEME, "assets/fonts/space-grotesk-400.woff2") is not None
    assert resolve_bundle_file(index, THEME, "../manifest.json") is None
    assert resolve_bundle_file(index, THEME, "manifest.json") is None
    assert resolve_bundle_file(index, THEME, "contract_rules.md") is None


def test_unknown_language_falls_back_to_the_default() -> None:
    content = minimal_content()
    derived = THEME.contract.derive(content)
    bundle = build_bundle(content, derived, render_body(content, derived), "<script>", THEME)
    assert bundle.lang == "en" and '<html lang="en">' in bundle.index_html


# ── failure envelopes ────────────────────────────────────────────────────────


def test_validation_failure_says_what_where_and_why() -> None:
    content = sample_content("01_strong_profile")
    body = render_body(content).replace(
        "designing the durable job infrastructure", "building durable job infrastructure"
    )
    report = validate_page(body, content, THEME)
    envelope = failure_from_validation(report, reference="cg-abc")
    assert envelope.code == "PAGE_COPY_MISMATCH" and envelope.stage == "validate"
    assert envelope.owner == "model_output" and envelope.retryable
    assert envelope.where[0].kind == "field" and envelope.where[0].ref == "hero.intro"
    assert "building durable job infrastructure" in (envelope.found or "")
    assert "designing the durable job infrastructure" in (envelope.expected or "")
    assert "unchanged" in envelope.action
    payload = envelope.to_payload()
    assert payload["issue_count"] >= 1 and payload["reference"] == "cg-abc"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda body: body.replace("</nav>", "</div>"), "HTML_NOT_WELL_FORMED"),
        (lambda body: "```html\n" + body, "PAGE_OUTPUT_INVALID"),
        (lambda body: body.replace("<h1>", '<h1 onclick="x()">'), "PAGE_MARKUP_NOT_ALLOWED"),
        (
            lambda body: body.replace('class="hero__visual"', 'class="hero__visual hero__x"'),
            "PAGE_MARKUP_NOT_ALLOWED",
        ),
    ],
)
def test_validation_failure_codes_by_category(mutation, code: str) -> None:  # type: ignore[no-untyped-def]
    content = sample_content("01_strong_profile")
    report = validate_page(mutation(render_body(content)), content, THEME)
    assert failure_from_validation(report).code == code


def test_provider_failures_are_classified_without_leaking_details() -> None:
    truncated = failure_from_provider_error(ModelOutputTruncatedError(), stage="generate")
    assert truncated.code == "MODEL_OUTPUT_TRUNCATED" and truncated.owner == "model_output"
    assert "shorten" in truncated.action
    timeout = failure_from_provider_error(ProviderTimeoutError(), stage="generate")
    assert timeout.owner == "infrastructure" and timeout.retryable
    auth = failure_from_provider_error(ProviderAuthError("secret key abc is bad"), stage="generate")
    assert (
        auth.owner == "configuration"
        and not auth.retryable
        and "abc" not in auth.summary + auth.cause
    )
    assert (
        failure_from_provider_error(ModelJsonInvalidError(), stage="generate").code
        == "MODEL_JSON_INVALID"
    )


def test_unexpected_errors_report_only_their_type() -> None:
    envelope = failure_unexpected(
        RuntimeError("db password=hunter2"), stage="bundle", reference="cg-1"
    )
    text = envelope.summary + envelope.cause + envelope.action
    assert "hunter2" not in text and "RuntimeError" in envelope.cause
    assert failure_worker_lost().code == "WORKER_LOST"


# ── runtime isolation ────────────────────────────────────────────────────────


def test_dev_utilities_are_never_imported_by_runtime_code() -> None:
    root = Path(__file__).resolve().parents[4] / "src" / "oryxenai"
    allowed = (
        root / "agents" / "code_generator" / "dev",
        root / "agents" / "code_generator" / "cli.py",
    )
    offenders = []
    for path in root.rglob("*.py"):
        if any(path == target or target in path.parents for target in allowed):
            continue
        if "code_generator.dev" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
