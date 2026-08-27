from types import SimpleNamespace

from oryxenai.agents.code_generator.core.generation_orchestrator import (
    _invalidate_stale_route_batch_checkpoint,
)
from oryxenai.agents.code_generator.core.source_validation import (
    _canonical_visible_text,
    normalize_generated_route_contract,
    validate_local_imports,
    validate_route_batch_contract,
)


def test_canonical_visible_text_collapses_source_wrapping() -> None:
    approved = "Approved copy that spans one rendered sentence."
    wrapped = "Approved copy that spans one\n    rendered sentence."

    assert _canonical_visible_text(wrapped) == _canonical_visible_text(approved)


def test_validate_local_imports_uses_repository_source_locations(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    (tmp_path / "src" / "content").mkdir(parents=True)
    (tmp_path / "src" / "content" / "generated-content.ts").write_text(
        "export const contentValue = '';", encoding="utf-8"
    )
    source = section / "Hero.tsx"
    source.write_text(
        'import { contentValue } from "../../../content/generated-content";\n'
        'import { missing } from "../../../../content/generated-content";\n',
        encoding="utf-8",
    )

    diagnostics = validate_local_imports(
        tmp_path,
        ["src/routes/home/sections/Hero.tsx"],
        work_unit_id="route-home-batch-1",
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "SOURCE_LOCAL_IMPORT_MISSING"
    assert "../../../../content/generated-content" in diagnostics[0].normalized_message


def test_validate_local_imports_rejects_missing_named_export(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    source = section / "Hero.tsx"
    source.write_text(
        'import { HeroSection } from "./Hero";\nexport default function Hero() { return null; }\n',
        encoding="utf-8",
    )

    diagnostics = validate_local_imports(
        tmp_path,
        ["src/routes/home/sections/Hero.tsx"],
        work_unit_id="route-home-batch-1",
    )

    assert diagnostics and diagnostics[0].code == "SOURCE_LOCAL_EXPORT_MISSING"
    assert "HeroSection" in diagnostics[0].normalized_message


def test_validate_route_batch_contract_requires_authoritative_dom_ids(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    hero = section / "Hero.tsx"
    hero.write_text(
        '<section id="home:hero" data-content-id="home:hero" />\n',
        encoding="utf-8",
    )
    selected_work = section / "SelectedWork.tsx"
    selected_work.write_text(
        '<section id="selected-work" data-content-id="home:selected-work" />\n',
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/SelectedWork.tsx",
        ],
        route_id="home",
        section_ids=["home:hero", "home:selected-work"],
        work_unit_id="route-home-batch-1",
    )

    assert {item.code for item in diagnostics} == {"SOURCE_ROUTE_BATCH_DOM_ID_INVALID"}


def test_validate_route_batch_contract_rejects_aggregated_sections(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    (section / "Hero.tsx").write_text(
        '<section id="home:hero" data-content-id="home:hero" />\n'
        '<section id="home:selected-work" data-content-id="home:selected-work" />\n',
        encoding="utf-8",
    )
    (section / "SelectedWork.tsx").write_text(
        "export default function SelectedWork() { return null; }\n",
        encoding="utf-8",
    )

    diagnostics = validate_route_batch_contract(
        tmp_path,
        [
            "src/routes/home/sections/Hero.tsx",
            "src/routes/home/sections/SelectedWork.tsx",
        ],
        route_id="home",
        section_ids=["home:hero", "home:selected-work"],
        work_unit_id="route-home-batch-1",
    )

    assert {item.code for item in diagnostics} == {
        "SOURCE_ROUTE_BATCH_SECTION_OWNERSHIP_INVALID"
    }


def test_stale_route_batch_checkpoint_reopens_route_composition(tmp_path) -> None:
    section = tmp_path / "src" / "routes" / "home" / "sections"
    section.mkdir(parents=True)
    source = section / "Hero.tsx"
    source.write_text(
        'import { contentValue } from "../../../../content/generated-content";\n',
        encoding="utf-8",
    )
    batch = SimpleNamespace(
        unit_id="route-home-batch-1",
        kind="route_batch",
        owns_paths=["src/routes/home/sections/Hero.tsx"],
    )
    composer = SimpleNamespace(
        unit_id="route-home-compose",
        kind="route_compose",
        owns_paths=["src/routes/home/index.tsx"],
    )
    projection = SimpleNamespace(
        accepted_checkpoint=object(),
        work_units=[
            SimpleNamespace(
                unit_id=batch.unit_id,
                kind=batch.kind,
                status="checkpointed",
                checkpoint_after="old",
                call_receipt_id="old-call",
                repair_round=2,
            ),
            SimpleNamespace(
                unit_id=composer.unit_id,
                kind=composer.kind,
                status="model_requested",
                checkpoint_after="",
                call_receipt_id="",
                repair_round=1,
            ),
        ],
        phase="generating_routes",
        active_work_unit_id=composer.unit_id,
        source_ready=False,
        source_file_count=0,
        source_total_bytes=0,
    )
    plan = SimpleNamespace(work_graph=SimpleNamespace(units=[batch, composer]))

    diagnostics = _invalidate_stale_route_batch_checkpoint(
        projection,
        plan=plan,
        workspace=SimpleNamespace(repo_dir=tmp_path),
    )

    assert diagnostics and diagnostics[0].code == "SOURCE_LOCAL_IMPORT_MISSING"
    assert all(item.status == "pending" for item in projection.work_units)
    assert all(item.checkpoint_after == "" for item in projection.work_units)
    assert all(item.call_receipt_id == "" for item in projection.work_units)


def test_route_contract_normalizer_deduplicates_markers_and_restores_heading(tmp_path) -> None:
    route_dir = tmp_path / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    route_file = route_dir / "index.tsx"
    route_file.write_text(
        """
<nav><a data-interaction-id="interaction:home:explore">Hidden</a></nav>
<main>
  <section data-content-id="home:capabilities"><h2>Tools</h2></section>
  <a data-interaction-id="interaction:home:explore">Visible</a>
</main>
""",
        encoding="utf-8",
    )

    changed = normalize_generated_route_contract(
        tmp_path,
        plan=SimpleNamespace(
            interactions=[
                SimpleNamespace(
                    interaction_id="interaction:home:explore",
                    route_id="home",
                    accessible_name="Explore selected work",
                )
            ]
        ),
        site_contract={
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "public_content": [
                {
                    "route_id": "home",
                    "sections": [
                        {
                            "section_id": "home:capabilities",
                            "content": {"heading": "Capabilities"},
                        }
                    ],
                }
            ],
        },
    )

    updated = route_file.read_text(encoding="utf-8")
    assert changed
    assert updated.count('data-interaction-id="interaction:home:explore"') == 1
    assert 'aria-label="Explore selected work"' in updated
    assert "<h2>Capabilities</h2>" in updated


def test_route_contract_normalizer_disambiguates_indexed_reusable_controls(tmp_path) -> None:
    route_dir = tmp_path / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    route_file = route_dir / "sections.tsx"
    route_file.write_text(
        """
function CapabilityToggle({ groupIndex }: { groupIndex: number }) {
  return <button data-interaction-id="interaction:home:capability">Show more</button>;
}
""",
        encoding="utf-8",
    )

    changed = normalize_generated_route_contract(
        tmp_path,
        plan=SimpleNamespace(
            interactions=[
                SimpleNamespace(
                    interaction_id="interaction:home:capability",
                    route_id="home",
                    accessible_name="Show more",
                )
            ]
        ),
        site_contract={
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "public_content": [],
        },
    )

    updated = route_file.read_text(encoding="utf-8")
    assert changed
    assert (
        'data-interaction-id={groupIndex === 0 ? "interaction:home:capability" : undefined}'
        in updated
    )
    assert "OryxenAI interaction marker: interaction:home:capability" in updated


def test_route_contract_normalizer_adds_escape_close_to_stateful_trigger(tmp_path) -> None:
    route_dir = tmp_path / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    route_file = route_dir / "index.tsx"
    route_file.write_text(
        """
function SiteNav() {
  const [open, setOpen] = useState(false);
  return <button aria-expanded={open} data-interaction-id="interaction:home:nav-toggle" onClick={() => setOpen((value) => !value)}>Menu</button>;
}
""",
        encoding="utf-8",
    )

    changed = normalize_generated_route_contract(
        tmp_path,
        plan=SimpleNamespace(
            interactions=[
                SimpleNamespace(
                    interaction_id="interaction:home:nav-toggle",
                    route_id="home",
                    accessible_name="Open navigation menu",
                    keyboard_behavior="Enter/Space/Escape; Escape closes and returns focus.",
                )
            ]
        ),
        site_contract={
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "public_content": [],
        },
    )

    updated = route_file.read_text(encoding="utf-8")
    assert changed
    assert 'if (event.key === "Escape")' in updated
    assert "setOpen(false)" in updated


def test_route_contract_normalizer_recovers_legacy_malformed_escape_patch(tmp_path) -> None:
    route_dir = tmp_path / "src" / "routes" / "home"
    route_dir.mkdir(parents=True)
    route_file = route_dir / "index.tsx"
    route_file.write_text(
        """
function SiteNav() {
  const [open, setOpen] = useState(false);
  return <button aria-expanded={open} data-interaction-id="interaction:home:nav-toggle"
    onClick={() = onKeyDown={(event) => { if (event.key === "Escape") { setOpen(false); } }}> setOpen((value) => !value)}>
    Menu
  </button>;
}
""",
        encoding="utf-8",
    )

    changed = normalize_generated_route_contract(
        tmp_path,
        plan=SimpleNamespace(
            interactions=[
                SimpleNamespace(
                    interaction_id="interaction:home:nav-toggle",
                    route_id="home",
                    accessible_name="Open navigation menu",
                    keyboard_behavior="Escape closes and returns focus.",
                )
            ]
        ),
        site_contract={
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "public_content": [],
        },
    )

    updated = route_file.read_text(encoding="utf-8")
    assert changed
    assert "onClick={() => setOpen((value) => !value)}" in updated
    assert updated.count("onKeyDown={(event) =>") == 1
