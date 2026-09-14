from __future__ import annotations

import json
from pathlib import Path

import pytest

from oryxenai.agents.build_preparation.brief_assembly import (
    BRIEF_SOURCE_VERSION,
    build_content_brief,
    build_visual_brief,
)
from oryxenai.agents.build_preparation.schemas import RouteScope
from oryxenai.agents.code_generator.core.brief_ingestion import (
    BRIEF_ENVELOPE_VERSION,
    BRIEF_NAMESPACED_SOURCE_FORMAT,
    BRIEF_NAMESPACED_SOURCE_VERSION,
    BRIEF_RAW_SOURCE_FORMAT,
    BRIEF_STRUCTURE_VERSION,
    CONTENT_FILENAME,
    VISUAL_FILENAME,
    BriefContractError,
    _validate_indexes,
    compile_briefs,
    parse_brief_envelope,
)
from oryxenai.agents.code_generator.core.development_input import (
    DevelopmentInputAdapter,
    DevelopmentInputError,
    _blocking_execution_gaps,
)
from oryxenai.core.settings import Settings


def _adapter(tmp_path) -> DevelopmentInputAdapter:
    settings = Settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    return DevelopmentInputAdapter(settings)


def test_optional_execution_gaps_are_admissible_but_required_gaps_block() -> None:
    optional = {
        "slots": [{"resource_slot_id": "slot-optional", "required": False}],
        "execution_gaps": [{"slot_id": "slot-optional"}],
    }
    required = {
        "slots": [{"resource_slot_id": "slot-required", "required": True}],
        "execution_gaps": [{"slot_id": "slot-required"}],
    }

    assert _blocking_execution_gaps(optional) == []
    assert _blocking_execution_gaps(required) == required["execution_gaps"]


def test_fixture_markdown_pair_is_admitted_and_compiled(tmp_path) -> None:
    """Legacy privacy-safe fixtures are converted to the current brief contract."""

    adapter = _adapter(tmp_path)
    reference = adapter.from_fixture("privacy-safe-v3")

    receipt, projections = adapter.admit(reference)

    assert receipt.source_version == "build-preparation-brief-v1"
    assert receipt.source_format == BRIEF_NAMESPACED_SOURCE_FORMAT
    assert receipt.dispatch_mode == "legacy_unversioned"
    assert receipt.structural_signature.startswith(f"{BRIEF_STRUCTURE_VERSION}:")
    assert receipt.schema_version == "code-generator-brief-envelope-v1"
    assert receipt.route_ids == ["home"]
    assert projections["site/contract.json"]["navigation_contract"]["closed"] is True
    assert (
        projections["execution/contract.json"]["policy"]["runtime_network_fetch_allowed"] is False
    )


def test_build_preparation_markdown_uploads_are_wrapped_and_admitted(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    fixture_reference = adapter.from_fixture("privacy-safe-v3")
    fixture_payload = json.loads(adapter.read(fixture_reference))
    reference = adapter.from_brief_uploads(
        content_filename=CONTENT_FILENAME,
        content_data=fixture_payload["content_brief_markdown"].encode("utf-8"),
        visual_filename=VISUAL_FILENAME,
        visual_data=fixture_payload["visual_brief_markdown"].encode("utf-8"),
    )
    receipt, _projections = adapter.admit(reference)

    assert reference.mode == "build_preparation_briefs"
    assert receipt.content_brief_sha256
    assert receipt.visual_brief_sha256
    assert receipt.source_sha256 == reference.source_sha256
    admitted_copy = (
        Path(adapter._config.input_root)
        / "admitted"
        / receipt.admitted_identity
        / "brief-envelope.json"
    )
    # The workspace consumes the identity-addressed admission tree even though
    # the immutable source itself remains content-addressed under inputs/.
    assert admitted_copy.is_file()
    assert admitted_copy.read_bytes() == adapter.read(reference)


def test_result_json_markdown_pair_is_admitted_from_the_mirror(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    fixture_reference = adapter.from_fixture("privacy-safe-v3")
    fixture_payload = json.loads(adapter.read(fixture_reference))
    mirror = tmp_path / "mirror" / "result-only"
    mirror.mkdir(parents=True)
    (mirror / "result.json").write_text(json.dumps(fixture_payload), encoding="utf-8")
    adapter._config.build_preparation_mirror_root = str(tmp_path / "mirror")

    packs = adapter.list_build_preparation_packs()
    assert packs[0]["brief_dir"] == "result-only"
    assert packs[0]["eligible"] is True
    reference = adapter.from_build_preparation_mirror("result-only")
    receipt, _projections = adapter.admit(reference)
    assert receipt.route_ids == ["home"]


def test_upload_mime_and_filename_are_rejected_before_storage(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    valid = adapter.read(adapter.from_fixture("privacy-safe-v3"))
    with pytest.raises(DevelopmentInputError, match="application/json"):
        adapter.from_upload(filename="briefs.json", mime_type="text/plain", data=valid)
    with pytest.raises(DevelopmentInputError, match=r"safe \.json"):
        adapter.from_upload(filename="../briefs.json", mime_type="application/json", data=valid)


def test_upload_size_limit_is_enforced_before_storage(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    adapter._config.max_upload_bytes = 1
    with pytest.raises(DevelopmentInputError, match="size limit"):
        adapter.from_upload(filename="briefs.json", mime_type="application/json", data=b"{}")


def test_json_envelope_upload_rejects_malformed_payload(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    with pytest.raises(DevelopmentInputError) as caught:
        adapter.from_upload(filename="briefs.json", mime_type="application/json", data=b"not-json")
    assert caught.value.code == "BRIEF_ENVELOPE_INVALID"


def test_markdown_upload_names_and_encoding_are_closed(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    with pytest.raises(DevelopmentInputError, match="named"):
        adapter.from_brief_uploads(
            content_filename="content.md",
            content_data=b"# content",
            visual_filename=VISUAL_FILENAME,
            visual_data=b"# visual",
        )
    with pytest.raises(DevelopmentInputError, match="UTF-8"):
        adapter.from_brief_uploads(
            content_filename=CONTENT_FILENAME,
            content_data=b"\xff",
            visual_filename=VISUAL_FILENAME,
            visual_data=b"# visual",
        )


def test_wire_shape_rejects_route_without_approved_sections() -> None:
    content = {
        "kind": "content_index",
        "run_id": "run-1",
        "content_architect_content_hash": "content-hash",
        "navigation_contract": {"closed": True, "allowed_destinations": ["home"]},
        "routes": [{"route_id": "home", "path": "/", "title": "Home", "sections": []}],
    }
    visual = {
        "kind": "visual_index",
        "run_id": "run-1",
        "visual_input_mode": "fixture",
        "target_contract": "react-vite-v1",
        "recommended_dependencies": [],
        "routes": ["home"],
        "resources": [],
        "components": [],
    }

    with pytest.raises(
        BriefContractError, match="route sections must be a non-empty array"
    ) as caught:
        _validate_indexes(content, visual)

    assert caught.value.code == "BRIEF_STRUCTURE_UNRECOGNIZED"


def _brief_pair(
    *,
    routes: list[tuple[str, str, list[str]]] | None = None,
    content_versions: dict[str, object] | None = None,
    visual_versions: dict[str, object] | None = None,
    content_extra: dict[str, object] | None = None,
    resources: list[dict[str, object]] | None = None,
    components: list[dict[str, object]] | None = None,
    duplicate_heading: bool = False,
) -> tuple[str, str]:
    route_specs = routes or [("home", "/", ["hero"])]
    content_routes = [
        {
            "route_id": route_id,
            "path": path,
            "title": route_id.title(),
            "sections": sections,
        }
        for route_id, path, sections in route_specs
    ]
    content_index: dict[str, object] = {
        "kind": "content_index",
        "run_id": "dispatch-fixture",
        "content_architect_content_hash": "content-hash",
        "navigation_contract": {
            "closed": True,
            "allowed_destinations": list(
                dict.fromkeys(
                    [
                        *(route_id for route_id, _path, _sections in route_specs),
                        *(
                            section
                            for _route_id, _path, sections in route_specs
                            for section in sections
                        ),
                    ]
                )
            ),
        },
        "routes": content_routes,
        **(content_versions or {}),
        **(content_extra or {}),
    }
    visual_index: dict[str, object] = {
        "kind": "visual_index",
        "run_id": "dispatch-fixture",
        "visual_input_mode": "fixture",
        "target_contract": "react-vite-v1",
        "recommended_dependencies": [],
        "routes": [route_id for route_id, _path, _sections in route_specs],
        "resources": resources or [],
        "components": components or [],
        **(visual_versions or {}),
    }
    content_lines = [
        "# Content",
        "",
        "```json build-preparation-content-index",
        json.dumps(content_index, indent=2),
        "```",
        "",
    ]
    section_headings: list[list[str]] = []
    for route_id, path, sections in route_specs:
        content_lines.extend([f"## Route: {path} ({route_id})", "", "*Purpose: Test route*", ""])
        for section in sections:
            heading = [
                f"### {section}",
                "*Test section*",
                "",
                "```json section-content",
                json.dumps({"heading": section}, indent=2),
                "```",
                "",
            ]
            section_headings.append(heading)
            content_lines.extend(heading)
    if duplicate_heading and section_headings:
        content_lines.extend(section_headings[0])
    visual_lines = [
        "# Visual",
        "",
        "```json build-preparation-visual-index",
        json.dumps(visual_index, indent=2),
        "```",
        "",
        "Use a local accessible composition.",
    ]
    return "\n".join(content_lines), "\n".join(visual_lines)


def _resource_entry(
    *,
    role_id: str = "assumed-image:hero:0",
    need_id: str = "need-hero",
    category: str = "editorial_photo",
    route_ids: list[str] | None = None,
    candidates: list[dict[str, object]] | None = None,
    primary_candidate_index: int | None = None,
) -> dict[str, object]:
    return {
        "need_id": need_id,
        "role_id": role_id,
        "category": category,
        "route_ids": route_ids or ["home"],
        "purpose": "Support the approved section.",
        "status": "candidates_found" if candidates else "no_material_found",
        "primary_candidate_index": primary_candidate_index,
        "guidance": "Use only approved local material.",
        "candidates": candidates or [],
    }


def _resource_candidate() -> dict[str, object]:
    return {
        "provider": "pexels",
        "provider_asset_id": "fixture-asset",
        "url": "https://images.pexels.com/photos/1/fixture.jpg",
        "preview_url": "https://images.pexels.com/photos/1/fixture.jpg",
        "license": "Pexels License",
        "license_reference": "https://www.pexels.com/license/",
        "title": "Fixture image",
        "width": 1200,
        "height": 800,
        "attribution": "Fixture",
        "additional_urls": {},
    }


def _component_entry(
    *,
    role_id: str = "assumed-component:hero:disclosure",
    need_id: str = "component-hero",
    route_ids: list[str] | None = None,
    suggestions: list[dict[str, object]] | None = None,
    primary_suggestion_index: int | None = None,
) -> dict[str, object]:
    return {
        "need_id": need_id,
        "role_id": role_id,
        "route_ids": route_ids or ["home"],
        "purpose": "Expose approved details accessibly.",
        "primary_suggestion_index": primary_suggestion_index,
        "guidance": "Retain keyboard behavior.",
        "suggestions": suggestions or [],
    }


def _component_suggestion() -> dict[str, object]:
    return {
        "provider": "shadcn",
        "name": "accordion",
        "title": "Accordion",
        "description": "Accessible disclosure pattern.",
        "item_url": "https://ui.shadcn.com/docs/components/accordion",
    }


def _rewrite_json_fence(
    markdown: str,
    tag: str,
    path: list[str | int],
    value: object,
) -> str:
    marker = f"```json {tag}\n"
    body_start = markdown.index(marker) + len(marker)
    body_end = markdown.index("\n```", body_start)
    payload = json.loads(markdown[body_start:body_end])
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return f"{markdown[:body_start]}{json.dumps(payload, indent=2)}{markdown[body_end:]}"


def _remove_json_fence_value(markdown: str, tag: str, path: list[str | int]) -> str:
    marker = f"```json {tag}\n"
    body_start = markdown.index(marker) + len(marker)
    body_end = markdown.index("\n```", body_start)
    payload = json.loads(markdown[body_start:body_end])
    target = payload
    for part in path[:-1]:
        target = target[part]
    del target[path[-1]]
    return f"{markdown[:body_start]}{json.dumps(payload, indent=2)}{markdown[body_end:]}"


def _duplicate_line(markdown: str, line: str, *, duplicate: str | None = None) -> str:
    assert markdown.count(line) == 1
    return markdown.replace(line, f"{line}\n{duplicate or line}", 1)


def test_post_67d5a75_raw_producer_fixture_is_canonicalized_fail_closed(tmp_path) -> None:
    adapter = _adapter(tmp_path)
    fixture_root = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "code_generator_build_preparation_post_67d5a75_v1"
    )
    adapter._config.fixture_map = {
        **adapter._config.fixture_map,
        "post-67d5a75-v1": str(fixture_root),
    }

    reference = adapter.from_fixture("post-67d5a75-v1")
    receipt, projections = adapter.admit(reference)

    expected_sections = [
        "home:hero",
        "home:metrics_summary",
        "home:flagship_projects",
        "home:automation_toolkits",
        "home:experience",
        "home:skills_and_certifications",
        "home:contact",
    ]
    site = projections["site/contract.json"]
    slots = {
        item["resource_slot_id"]: item for item in projections["execution/contract.json"]["slots"]
    }
    assert receipt.source_version == BRIEF_SOURCE_VERSION
    assert receipt.source_format == BRIEF_RAW_SOURCE_FORMAT
    assert receipt.dispatch_mode == "legacy_unversioned"
    assert receipt.structural_signature == (
        "bp-structure-v1:9e6cdb32b0ba7eaea1954eef35e8ae45fceb9a454116b6fc303af146c039d7a3"
    )
    assert receipt.content_brief_sha256 == (
        "40f9bc8b1e50ef7249a9569107004318e1037299b37fb2e78242bd7dd41f8a0a"
    )
    assert receipt.visual_brief_sha256 == (
        "be310a99769978e26372e94f1d6f59b7f4c28da61a4e253ed07662ec31c4cca1"
    )
    assert site["routes"][0]["section_sequence"] == expected_sections
    assert [item["section_id"] for item in site["public_content"][0]["sections"]] == (
        expected_sections
    )
    assert site["navigation_contract"]["allowed_destinations"] == [
        "home",
        *expected_sections,
    ]
    assert site["navigation_contract"]["allowed_hrefs"][:3] == [
        "/",
        "#hero",
        "#metrics-summary",
    ]
    assert {item["criterion_id"] for item in site["criteria"]} == {
        f"criterion:{section}" for section in expected_sections
    }
    assert slots["assumed-image:hero:0"]["section_ids"] == ["home:hero"]
    assert slots["assumed-component:flagship_projects:selected-work-detail"]["section_ids"] == [
        "home:flagship_projects"
    ]
    assert slots["typography-font"]["section_ids"] == expected_sections


@pytest.mark.parametrize(
    ("content_versions", "visual_versions", "sections", "content_extra", "error_code"),
    [
        (
            {"brief_contract_version": "future-v9"},
            {"brief_contract_version": "future-v9"},
            ["hero"],
            None,
            "BRIEF_VERSION_UNSUPPORTED",
        ),
        (
            {"brief_contract_version": ""},
            {"brief_contract_version": ""},
            ["hero"],
            None,
            "BRIEF_VERSION_INVALID",
        ),
        (
            {"brief_contract_version": BRIEF_SOURCE_VERSION},
            None,
            ["hero"],
            None,
            "BRIEF_VERSION_AMBIGUOUS",
        ),
        (
            {
                "brief_contract_version": BRIEF_SOURCE_VERSION,
                "schema_version": BRIEF_NAMESPACED_SOURCE_VERSION,
            },
            {"brief_contract_version": BRIEF_SOURCE_VERSION},
            ["hero"],
            None,
            "BRIEF_VERSION_AMBIGUOUS",
        ),
        (
            {"brief_contract_version": BRIEF_NAMESPACED_SOURCE_VERSION},
            {"brief_contract_version": BRIEF_NAMESPACED_SOURCE_VERSION},
            ["hero"],
            None,
            "BRIEF_VERSION_STRUCTURE_MISMATCH",
        ),
        (None, None, ["hero", "home:work"], None, "BRIEF_VERSION_AMBIGUOUS"),
        (None, None, ["hero"], {"unexpected_surface": True}, "BRIEF_STRUCTURE_UNRECOGNIZED"),
    ],
)
def test_brief_source_dispatch_rejects_ambiguous_or_mismatched_shapes(
    content_versions,
    visual_versions,
    sections,
    content_extra,
    error_code,
) -> None:
    content, visual = _brief_pair(
        content_versions=content_versions,
        visual_versions=visual_versions,
        routes=[("home", "/", sections)],
        content_extra=content_extra,
    )

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == error_code


def test_brief_envelope_rejects_duplicate_json_keys_recursively() -> None:
    envelope = (
        b'{"schema_version":"code-generator-brief-envelope-v1",'
        b'"schema_version":"future-v9",'
        b'"content_brief_markdown":"content",'
        b'"visual_brief_markdown":"visual"}'
    )

    with pytest.raises(BriefContractError) as caught:
        parse_brief_envelope(envelope)

    assert BRIEF_ENVELOPE_VERSION in envelope.decode()
    assert caught.value.code == "BRIEF_JSON_DUPLICATE_KEY"


@pytest.mark.parametrize(
    "location",
    ["version", "route", "navigation", "resource", "candidate", "section-content"],
)
def test_brief_json_rejects_duplicate_keys_at_every_structural_depth(location) -> None:
    candidate = _resource_candidate()
    content, visual = _brief_pair(
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=[_resource_entry(candidates=[candidate], primary_candidate_index=0)],
    )
    if location == "version":
        line = f'  "brief_contract_version": "{BRIEF_SOURCE_VERSION}"'
        content = _duplicate_line(
            content,
            line,
            duplicate='  "brief_contract_version": "future-v9"',
        ).replace(f"{line}\n", f"{line},\n", 1)
    elif location == "route":
        content = _duplicate_line(content, '      "route_id": "home",')
    elif location == "navigation":
        content = _duplicate_line(content, '    "closed": true,')
    elif location == "resource":
        visual = _duplicate_line(visual, '      "role_id": "assumed-image:hero:0",')
    elif location == "candidate":
        visual = _duplicate_line(visual, '          "provider": "pexels",')
    else:
        line = '  "heading": "hero"'
        content = _duplicate_line(
            content,
            line,
            duplicate='  "heading": "different"',
        ).replace(f"{line}\n", f"{line},\n", 1)

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == "BRIEF_JSON_DUPLICATE_KEY"


@pytest.mark.parametrize(
    ("document", "path", "value"),
    [
        ("content", ["routes", 0, "route_id"], 7),
        ("content", ["navigation_contract", "closed"], 1),
        ("visual", ["recommended_dependencies"], [1]),
        ("visual", ["routes"], [1]),
        ("visual", ["resources", 0, "route_ids"], [1]),
        ("visual", ["resources", 0, "primary_candidate_index"], "0"),
        ("visual", ["resources", 0, "candidates", 0, "width"], "1200"),
        ("visual", ["resources", 0, "candidates", 0, "additional_urls"], []),
        ("visual", ["components", 0, "suggestions", 0, "name"], 5),
    ],
)
def test_wire_shape_rejects_coercible_or_wrong_types(document, path, value) -> None:
    content, visual = _brief_pair(
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=[_resource_entry(candidates=[_resource_candidate()], primary_candidate_index=0)],
        components=[
            _component_entry(suggestions=[_component_suggestion()], primary_suggestion_index=0)
        ],
    )
    if document == "content":
        content = _rewrite_json_fence(content, "build-preparation-content-index", path, value)
    else:
        visual = _rewrite_json_fence(visual, "build-preparation-visual-index", path, value)

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == "BRIEF_STRUCTURE_UNRECOGNIZED"


@pytest.mark.parametrize(
    "path",
    [
        ["resources", 0, "need_id"],
        ["resources", 0, "status"],
        ["resources", 0, "candidates", 0, "width"],
        ["components", 0, "need_id"],
        ["components", 0, "suggestions", 0, "name"],
    ],
)
def test_declared_v1_requires_all_current_producer_fields(path) -> None:
    content, visual = _brief_pair(
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=[_resource_entry(candidates=[_resource_candidate()], primary_candidate_index=0)],
        components=[
            _component_entry(suggestions=[_component_suggestion()], primary_suggestion_index=0)
        ],
    )
    visual = _remove_json_fence_value(
        visual,
        "build-preparation-visual-index",
        path,
    )

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == "BRIEF_STRUCTURE_UNRECOGNIZED"


@pytest.mark.parametrize("field", ["dependencies", "registry_dependencies"])
def test_nested_resource_candidate_cannot_authorize_dependencies(field) -> None:
    content, visual = _brief_pair(
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=[_resource_entry(candidates=[_resource_candidate()], primary_candidate_index=0)],
    )
    visual = _rewrite_json_fence(
        visual,
        "build-preparation-visual-index",
        ["resources", 0, "candidates", 0, field],
        ["untrusted-package"],
    )

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == "BRIEF_STRUCTURE_UNRECOGNIZED"


def test_nested_component_suggestion_cannot_authorize_registry_dependencies() -> None:
    content, visual = _brief_pair(
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        components=[
            _component_entry(suggestions=[_component_suggestion()], primary_suggestion_index=0)
        ],
    )
    visual = _rewrite_json_fence(
        visual,
        "build-preparation-visual-index",
        ["components", 0, "suggestions", 0, "registry_dependencies"],
        ["untrusted-package"],
    )

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == "BRIEF_STRUCTURE_UNRECOGNIZED"


def test_plural_resource_ownership_expands_to_deterministic_route_local_slots() -> None:
    routes = [
        ("home", "/", ["hero"]),
        ("work", "/work", ["case_study"]),
    ]
    resources = [
        _resource_entry(
            role_id="shared-image:hero:case_study",
            need_id="shared-image",
            route_ids=["home", "work"],
        ),
        _resource_entry(
            role_id="typography-font",
            need_id="shared-font",
            category="font",
            route_ids=["home", "work"],
        ),
    ]
    content, visual = _brief_pair(
        routes=routes,
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=resources,
    )

    _receipt, projections, _summary = compile_briefs(content, visual)

    slots = projections["execution/contract.json"]["slots"]
    slots_by_id = {item["resource_slot_id"]: item for item in slots}
    assert list(slots_by_id) == [
        "shared-image:hero:case_study@home",
        "shared-image:hero:case_study@work",
        "typography-font@home",
        "typography-font@work",
    ]
    assert slots_by_id["shared-image:hero:case_study@home"]["section_ids"] == ["home:hero"]
    assert slots_by_id["shared-image:hero:case_study@work"]["section_ids"] == ["work:case_study"]
    assert slots_by_id["typography-font@home"]["criterion_ids"] == ["criterion:home:hero"]
    assert slots_by_id["typography-font@work"]["criterion_ids"] == ["criterion:work:case_study"]
    needs = projections["resources/projection.json"]["resource_needs"]
    assert {item["need_id"] for item in needs} == {
        "shared-image@home",
        "shared-image@work",
        "shared-font@home",
        "shared-font@work",
    }
    assert all(len(item["route_ids"]) == 1 for item in needs)


def test_namespaced_legacy_declaration_preserves_historical_role_projection() -> None:
    resources = [
        _resource_entry(role_id="assumed-image:hero:0", need_id="local-role"),
        _resource_entry(
            role_id="assumed-image:home:hero:1",
            need_id="namespaced-role",
        ),
    ]
    unversioned = _brief_pair(routes=[("home", "/", ["home:hero"])], resources=resources)
    legacy_declared = _brief_pair(
        routes=[("home", "/", ["home:hero"])],
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=resources,
    )
    namespaced_declared = _brief_pair(
        routes=[("home", "/", ["home:hero"])],
        content_versions={"brief_contract_version": BRIEF_NAMESPACED_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_NAMESPACED_SOURCE_VERSION},
        resources=resources,
    )

    unversioned_receipt, unversioned_projections, _ = compile_briefs(*unversioned)
    legacy_receipt, legacy_projections, _ = compile_briefs(*legacy_declared)
    namespaced_receipt, namespaced_projections, _ = compile_briefs(*namespaced_declared)

    slots = {
        item["resource_slot_id"]: item
        for item in legacy_projections["execution/contract.json"]["slots"]
    }
    assert slots["assumed-image:hero:0"]["section_ids"] == []
    assert slots["assumed-image:home:hero:1"]["section_ids"] == ["home:hero"]
    assert legacy_receipt["source_version"] == BRIEF_SOURCE_VERSION
    assert legacy_receipt["source_format"] == BRIEF_NAMESPACED_SOURCE_FORMAT
    assert legacy_receipt["dispatch_mode"] == "declared"
    assert unversioned_receipt["dispatch_mode"] == "legacy_unversioned"
    assert namespaced_receipt["source_version"] == BRIEF_NAMESPACED_SOURCE_VERSION
    assert namespaced_receipt["source_format"] == BRIEF_NAMESPACED_SOURCE_FORMAT
    assert (
        legacy_receipt["structural_signature"]
        == unversioned_receipt["structural_signature"]
        == namespaced_receipt["structural_signature"]
    )
    assert (
        legacy_projections["execution/contract.json"]
        == unversioned_projections["execution/contract.json"]
        == namespaced_projections["execution/contract.json"]
    )
    assert (
        legacy_receipt["projection_hashes"]["execution/contract.json"]
        == unversioned_receipt["projection_hashes"]["execution/contract.json"]
        == namespaced_receipt["projection_hashes"]["execution/contract.json"]
    )


def test_declared_legacy_namespaced_shape_keeps_historical_optional_fields() -> None:
    resource = _resource_entry(role_id="assumed-image:home:hero:0")
    del resource["need_id"]
    del resource["status"]
    routes = [("home", "/", ["home:hero"])]
    unversioned = _brief_pair(routes=routes, resources=[resource])
    legacy_declared = _brief_pair(
        routes=routes,
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=[resource],
    )
    current_declared = _brief_pair(
        routes=routes,
        content_versions={"brief_contract_version": BRIEF_NAMESPACED_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_NAMESPACED_SOURCE_VERSION},
        resources=[resource],
    )

    unversioned_receipt, unversioned_projections, _ = compile_briefs(*unversioned)
    legacy_receipt, legacy_projections, _ = compile_briefs(*legacy_declared)

    assert (
        legacy_projections["execution/contract.json"]
        == unversioned_projections["execution/contract.json"]
    )
    assert (
        legacy_projections["resources/projection.json"]
        == unversioned_projections["resources/projection.json"]
    )
    legacy_slot = legacy_projections["execution/contract.json"]["slots"][0]
    legacy_need = legacy_projections["resources/projection.json"]["resource_needs"][0]
    assert legacy_slot["source_ids"] == [""]
    assert legacy_need["need_id"] == "assumed-image:home:hero:0"
    assert (
        legacy_receipt["projection_hashes"]["execution/contract.json"]
        == unversioned_receipt["projection_hashes"]["execution/contract.json"]
    )
    with pytest.raises(BriefContractError) as caught:
        compile_briefs(*current_declared)
    assert caught.value.code == "BRIEF_STRUCTURE_UNRECOGNIZED"


def test_legacy_namespaced_plural_owner_projection_stays_frozen() -> None:
    routes = [
        ("home", "/", ["home:hero"]),
        ("work", "/work", ["work:case_study"]),
    ]
    resources = [
        _resource_entry(
            role_id="assumed-image:home:hero:work:case_study:0",
            need_id="shared-image",
            route_ids=["home", "work"],
        )
    ]
    unversioned = _brief_pair(routes=routes, resources=resources)
    legacy_declared = _brief_pair(
        routes=routes,
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=resources,
    )
    current_declared = _brief_pair(
        routes=routes,
        content_versions={"brief_contract_version": BRIEF_NAMESPACED_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_NAMESPACED_SOURCE_VERSION},
        resources=resources,
    )

    unversioned_receipt, unversioned_projections, _ = compile_briefs(*unversioned)
    legacy_receipt, legacy_projections, _ = compile_briefs(*legacy_declared)
    current_receipt, current_projections, _ = compile_briefs(*current_declared)

    legacy_slots = legacy_projections["execution/contract.json"]["slots"]
    assert [slot["resource_slot_id"] for slot in legacy_slots] == [
        "assumed-image:home:hero:work:case_study:0"
    ]
    assert legacy_slots[0]["route_id"] == "home"
    assert legacy_slots[0]["section_ids"] == ["home:hero"]
    legacy_needs = legacy_projections["resources/projection.json"]["resource_needs"]
    assert legacy_needs[0]["route_ids"] == ["home", "work"]
    assert (
        legacy_projections["execution/contract.json"]
        == unversioned_projections["execution/contract.json"]
    )
    assert (
        legacy_receipt["projection_hashes"]["execution/contract.json"]
        == unversioned_receipt["projection_hashes"]["execution/contract.json"]
    )

    current_slots = current_projections["execution/contract.json"]["slots"]
    assert [slot["resource_slot_id"] for slot in current_slots] == [
        "assumed-image:home:hero:work:case_study:0@home",
        "assumed-image:home:hero:work:case_study:0@work",
    ]
    assert [slot["section_ids"] for slot in current_slots] == [
        ["home:hero"],
        ["work:case_study"],
    ]
    assert current_receipt["source_version"] == BRIEF_NAMESPACED_SOURCE_VERSION


@pytest.mark.parametrize(
    ("second_role_id", "second_need_id", "identifier_kind"),
    [
        ("shared@home", "other-need", "resource_slot_id"),
        ("other-role", "shared-need@home", "need_id"),
    ],
)
def test_route_expansion_rejects_synthesized_identifier_collisions(
    second_role_id: str,
    second_need_id: str,
    identifier_kind: str,
) -> None:
    resources = [
        _resource_entry(
            role_id="shared",
            need_id="shared-need",
            route_ids=["home", "work"],
        ),
        _resource_entry(
            role_id=second_role_id,
            need_id=second_need_id,
            route_ids=["home"],
        ),
    ]
    content, visual = _brief_pair(
        routes=[("home", "/", ["hero"]), ("work", "/work", ["case_study"])],
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        resources=resources,
    )

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == "BRIEF_RESOURCE_ID_COLLISION"
    assert caught.value.details["identifier_kind"] == identifier_kind


def test_dispatch_provenance_distinguishes_declared_from_legacy_raw() -> None:
    unversioned = _brief_pair()
    declared = _brief_pair(
        content_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
        visual_versions={"brief_contract_version": BRIEF_SOURCE_VERSION},
    )

    unversioned_receipt, _unversioned_projections, _ = compile_briefs(*unversioned)
    declared_receipt, _declared_projections, _ = compile_briefs(*declared)

    assert unversioned_receipt["source_version"] == declared_receipt["source_version"]
    assert unversioned_receipt["source_format"] == declared_receipt["source_format"]
    assert unversioned_receipt["structural_signature"] == declared_receipt["structural_signature"]
    assert unversioned_receipt["dispatch_mode"] == "legacy_unversioned"
    assert declared_receipt["dispatch_mode"] == "declared"


def test_raw_v1_canonicalizes_repeated_route_local_section_ids() -> None:
    content, visual = _brief_pair(routes=[("home", "/", ["hero"]), ("work", "/work", ["hero"])])

    _receipt, projections, _summary = compile_briefs(content, visual)

    site = projections["site/contract.json"]
    assert [route["section_sequence"] for route in site["routes"]] == [
        ["home:hero"],
        ["work:hero"],
    ]
    assert site["navigation_contract"]["allowed_destinations"] == [
        "home",
        "work",
        "home:hero",
        "work:hero",
    ]
    assert [
        section["section_id"] for route in site["public_content"] for section in route["sections"]
    ] == ["home:hero", "work:hero"]


@pytest.mark.parametrize(
    ("routes", "error_code"),
    [
        ([("home", "/", ["hero", "hero"])], "BRIEF_SECTION_DUPLICATE"),
        ([("home", "/", ["home"])], "BRIEF_SECTION_ROUTE_COLLISION"),
    ],
)
def test_raw_v1_rejects_ambiguous_route_local_section_mapping(routes, error_code) -> None:
    content, visual = _brief_pair(routes=routes)

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == error_code


def test_section_heading_cardinality_rejects_duplicate_raw_heading() -> None:
    content, visual = _brief_pair(duplicate_heading=True)

    with pytest.raises(BriefContractError) as caught:
        compile_briefs(content, visual)

    assert caught.value.code == "BRIEF_SECTION_CONTENT_CARDINALITY"


def test_raw_v1_crlf_transport_preserves_structure_but_not_verbatim_hash() -> None:
    fixture_root = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "code_generator_build_preparation_post_67d5a75_v1"
    )
    content = (fixture_root / CONTENT_FILENAME).read_text(encoding="utf-8")
    visual = (fixture_root / VISUAL_FILENAME).read_text(encoding="utf-8")

    lf_receipt, lf_projections, _lf_summary = compile_briefs(content, visual)
    crlf_receipt, crlf_projections, _crlf_summary = compile_briefs(
        content.replace("\n", "\r\n"), visual.replace("\n", "\r\n")
    )

    assert lf_receipt["source_format"] == crlf_receipt["source_format"]
    assert lf_receipt["structural_signature"] == crlf_receipt["structural_signature"]
    assert lf_receipt["content_brief_sha256"] != crlf_receipt["content_brief_sha256"]
    assert (
        lf_projections["site/contract.json"]["routes"]
        == crlf_projections["site/contract.json"]["routes"]
    )
    assert (
        lf_projections["site/contract.json"]["public_content"]
        == crlf_projections["site/contract.json"]["public_content"]
    )


def test_current_build_preparation_producer_declares_and_compiles_raw_v1() -> None:
    routes = [
        RouteScope(
            route_id="home",
            path="/",
            title="Home",
            purpose="Introduce the approved portfolio.",
            section_ids=["hero"],
        ),
        RouteScope(
            route_id="work",
            path="/work",
            title="Work",
            purpose="Show approved work.",
            section_ids=["hero"],
        ),
    ]
    content = build_content_brief(
        content_architect={
            "approved": {"content_hash": "producer-content-hash"},
            "page_content_packs": [
                {
                    "route_id": route_id,
                    "sections": [
                        {
                            "section_id": "hero",
                            "purpose": purpose,
                            "content": {"headline": headline},
                        }
                    ],
                }
                for route_id, purpose, headline in (
                    ("home", "Introduce the portfolio.", "Approved home headline"),
                    ("work", "Introduce the work.", "Approved work headline"),
                )
            ],
        },
        routes=routes,
        run_id="producer-run",
        seo_suggestions={},
    )
    visual = build_visual_brief(
        routes=routes,
        resource_index=[],
        component_index=[],
        visual_brief_prose="Use a clear, accessible editorial hierarchy.",
        target_contract="react-vite-v1",
        recommended_dependencies=[],
        visual_input_mode="approved_vdd",
        run_id="producer-run",
        warnings=[],
    )

    receipt, projections, _summary = compile_briefs(content, visual)

    assert f'"brief_contract_version": "{BRIEF_SOURCE_VERSION}"' in content
    assert f'"brief_contract_version": "{BRIEF_SOURCE_VERSION}"' in visual
    assert receipt["source_version"] == BRIEF_SOURCE_VERSION
    assert receipt["source_format"] == BRIEF_RAW_SOURCE_FORMAT
    assert receipt["dispatch_mode"] == "declared"
    assert [route["section_sequence"] for route in projections["site/contract.json"]["routes"]] == [
        ["home:hero"],
        ["work:hero"],
    ]
    assert [
        section["content"]["headline"]
        for route in projections["site/contract.json"]["public_content"]
        for section in route["sections"]
    ] == ["Approved home headline", "Approved work headline"]


def test_current_build_preparation_producer_declares_namespaced_v1() -> None:
    route = RouteScope(
        route_id="home",
        path="/",
        title="Home",
        purpose="Introduce the approved portfolio.",
        section_ids=["home:hero"],
    )
    content = build_content_brief(
        content_architect={
            "approved": {"content_hash": "producer-content-hash"},
            "page_content_packs": [
                {
                    "route_id": "home",
                    "sections": [
                        {
                            "section_id": "home:hero",
                            "purpose": "Introduce the portfolio.",
                            "content": {"headline": "Approved headline"},
                        }
                    ],
                }
            ],
        },
        routes=[route],
        run_id="producer-namespaced-run",
        seo_suggestions={},
    )
    visual = build_visual_brief(
        routes=[route],
        resource_index=[],
        component_index=[],
        visual_brief_prose="Use a clear, accessible editorial hierarchy.",
        target_contract="react-vite-v1",
        recommended_dependencies=[],
        visual_input_mode="approved_vdd",
        run_id="producer-namespaced-run",
        warnings=[],
    )

    receipt, projections, _summary = compile_briefs(content, visual)

    assert f'"brief_contract_version": "{BRIEF_NAMESPACED_SOURCE_VERSION}"' in content
    assert f'"brief_contract_version": "{BRIEF_NAMESPACED_SOURCE_VERSION}"' in visual
    assert receipt["source_version"] == BRIEF_NAMESPACED_SOURCE_VERSION
    assert receipt["source_format"] == BRIEF_NAMESPACED_SOURCE_FORMAT
    assert receipt["dispatch_mode"] == "declared"
    assert projections["site/contract.json"]["routes"][0]["section_sequence"] == ["home:hero"]


def test_build_preparation_producer_rejects_mixed_section_id_styles() -> None:
    route = RouteScope(
        route_id="home",
        path="/",
        title="Home",
        purpose="Introduce the approved portfolio.",
        section_ids=["hero", "home:work"],
    )

    with pytest.raises(ValueError, match="mixed raw and namespaced"):
        build_content_brief(
            content_architect={"page_content_packs": []},
            routes=[route],
            run_id="producer-mixed-run",
            seo_suggestions={},
        )
