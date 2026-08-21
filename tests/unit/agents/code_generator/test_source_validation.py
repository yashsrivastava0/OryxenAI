from types import SimpleNamespace

from oryxenai.agents.code_generator.core.source_validation import (
    _canonical_visible_text,
    normalize_generated_route_contract,
)


def test_canonical_visible_text_collapses_source_wrapping() -> None:
    approved = "Approved copy that spans one rendered sentence."
    wrapped = "Approved copy that spans one\n    rendered sentence."

    assert _canonical_visible_text(wrapped) == _canonical_visible_text(approved)


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
