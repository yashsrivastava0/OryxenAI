from __future__ import annotations

from pathlib import Path

from oryxenai.agents.code_generator.core.development_schemas import Diagnostic
from oryxenai.agents.code_generator.core.diagnostics import build_bundle


def _route_diagnostic(route_id: str, code: str = "RUNTIME_FONT_NOT_LOADED") -> Diagnostic:
    return Diagnostic(
        diagnostic_id="diagnostic-runtime-test",
        group="dom_runtime",
        code=code,
        phase="dom_runtime",
        normalized_message="A required font face never reported loaded.",
        route_id=route_id,
        fingerprint="runtime-test",
    )


def test_route_scoped_diagnostic_with_no_file_still_gets_real_source(tmp_path: Path) -> None:
    """Every DOM/runtime diagnostic (font, layout, motion, interaction checks)
    carries only a route id, never `.file`. Before this fix, the repair model
    saw an empty bounded_related_source for the entire class of findings that
    remain the pipeline's actual unresolved frontier."""

    route_dir = tmp_path / "src/routes/home-4ea140588150"
    route_dir.mkdir(parents=True)
    (route_dir / "index.tsx").write_text("export default function Home() { return null; }")
    (route_dir / "route.css").write_text(".route {}")
    sections = route_dir / "sections"
    sections.mkdir()
    (sections / "hero.tsx").write_text("export const Hero = () => <section id='hero' />;")

    bundle = build_bundle(
        checkpoint_hash="checkpoint-test",
        diagnostics=[_route_diagnostic("home")],
        allowed_paths=["src/routes/home-4ea140588150/**"],
        plan_slice={},
        source_root=tmp_path,
        required_checks=["source.paths"],
    )

    assert bundle.bounded_related_source
    assert "src/routes/home-4ea140588150/index.tsx" in bundle.bounded_related_source
    assert "src/routes/home-4ea140588150/route.css" in bundle.bounded_related_source
    assert "src/routes/home-4ea140588150/sections/hero.tsx" in bundle.bounded_related_source
    assert (
        "export default function Home"
        in bundle.bounded_related_source["src/routes/home-4ea140588150/index.tsx"]
    )


def test_expansion_never_escapes_the_allowed_directory(tmp_path: Path) -> None:
    (tmp_path / "src/routes/home").mkdir(parents=True)
    outside = tmp_path.parent / "outside.tsx"
    outside.write_text("export const Secret = 1;")

    bundle = build_bundle(
        checkpoint_hash="checkpoint-test",
        diagnostics=[_route_diagnostic("home")],
        allowed_paths=["../outside.tsx"],
        plan_slice={},
        source_root=tmp_path,
        required_checks=[],
    )

    assert bundle.bounded_related_source == {}


def test_expansion_is_bounded_and_does_not_duplicate_explicit_file_matches(tmp_path: Path) -> None:
    route_dir = tmp_path / "src/routes/home-4ea140588150"
    route_dir.mkdir(parents=True)
    (route_dir / "index.tsx").write_text("export default function Home() { return null; }")

    file_diagnostic = Diagnostic(
        diagnostic_id="diagnostic-file-test",
        group="source_contract",
        code="SOURCE_LOCAL_IMPORT_MISSING",
        phase="source_contract",
        normalized_message="Missing import.",
        file="src/routes/home-4ea140588150/index.tsx",
        route_id="home",
        fingerprint="file-test",
    )

    bundle = build_bundle(
        checkpoint_hash="checkpoint-test",
        diagnostics=[file_diagnostic],
        allowed_paths=["src/routes/home-4ea140588150/**"],
        plan_slice={},
        source_root=tmp_path,
        required_checks=[],
    )

    assert list(bundle.bounded_related_source) == ["src/routes/home-4ea140588150/index.tsx"]
