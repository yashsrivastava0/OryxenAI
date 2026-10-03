"""Developer CLI for the page builder: see the prompt, build a page, read exact failures.

    python -m oryxenai.agents.code_generator.cli prompt   --sample 01_strong_profile
    python -m oryxenai.agents.code_generator.cli render   --sample 01_strong_profile --out out/render
    python -m oryxenai.agents.code_generator.cli generate --sample 01_strong_profile --out out/mock
    python -m oryxenai.agents.code_generator.cli generate --sample 01_strong_profile --live --out out/live
    python -m oryxenai.agents.code_generator.cli validate --sample 01_strong_profile --html body.html

``generate`` runs exactly the production pipeline (``build_page``): mock mode uses
the deterministic reference renderer in place of the model; ``--live`` uses the
configured model route (it needs the application database for the usage ledger).
A failure prints the same what / where / why envelope the Studio shows and, with
``--out``, writes ``failure.json``, ``trace.json`` and the rejected markup.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from oryxenai.agents.code_generator.admission import content_admission_issues
from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.bundle import SiteBundle
from oryxenai.agents.code_generator.diagnostics import (
    failure_from_admission,
    failure_from_validation,
)
from oryxenai.agents.code_generator.pipeline import build_page
from oryxenai.agents.code_generator.prompt_builder import build_instructions
from oryxenai.agents.code_generator.schemas import CodeGeneratorFailure
from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.themes import DEFAULT_THEME_ID, ThemePackage, get_theme

_SAMPLES = Path(__file__).resolve().parents[1] / "content_architect" / "samples"


def load_content(sample: str | None, content_file: str | None) -> dict[str, Any]:
    """``page_content`` from a Content Architect sample name or a JSON file."""
    if content_file:
        data = json.loads(Path(content_file).read_text(encoding="utf-8"))
    else:
        name = sample or "01_strong_profile"
        path = _SAMPLES / f"{name}_output.json"
        if not path.exists():
            choices = sorted(
                p.name.removesuffix("_output.json") for p in _SAMPLES.glob("*_output.json")
            )
            raise SystemExit(f"Unknown sample '{name}'. Choose one of: {', '.join(choices)}")
        data = json.loads(path.read_text(encoding="utf-8"))
    content = data.get("page_content", data) if isinstance(data, dict) else {}
    if not isinstance(content, dict):
        raise SystemExit("The content file does not contain a page_content object.")
    return content


def write_bundle(out_dir: Path, bundle: SiteBundle, theme: ThemePackage) -> list[str]:
    """Write ``index.html`` and the theme's files so the folder can be served as-is."""
    written: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_bytes(bundle.index_html.encode("utf-8"))
    written.append("index.html")
    for entry in theme.files.values():
        target = out_dir / entry.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(entry.data)
        written.append(entry.path)
    return written


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


async def _live_agent(theme_id: str) -> CodeGeneratorAgent:
    from oryxenai.agents.shared.model_runtime import get_model_runtime
    from oryxenai.core.settings import get_settings
    from oryxenai.db.session import get_sessionmaker

    settings = get_settings()
    runtime = get_model_runtime(settings.models, get_sessionmaker(settings))
    return CodeGeneratorAgent(
        runtime.routed_client("code_generator", input_classification="personal"),
        theme_id=theme_id,
        profile_name=runtime.policy_profile_name("code_generator", "generate_page"),
    )


def _command_prompt(args: argparse.Namespace) -> int:
    theme = get_theme(args.theme)
    content = load_content(args.sample, args.content)
    bundle = build_instructions("generate_page", theme)
    derived = theme.contract.derive(content)
    print("=== SYSTEM PROMPT ===")
    print(bundle.system_prompt)
    print("\n=== TASK ===")
    print(bundle.task)
    print("\n=== UNTRUSTED INPUT (sent as a separate message) ===")
    _print_json({"content": content, "derived": derived, "theme": {"id": theme.theme_id}})
    print(f"\n=== prompt modules === {json.dumps(bundle.manifest)}")
    return 0


def _command_render(args: argparse.Namespace) -> int:
    from oryxenai.agents.code_generator.bundle import build_bundle
    from oryxenai.agents.code_generator.dev.reference_renderer import render_body

    theme = get_theme(args.theme)
    content = load_content(args.sample, args.content)
    derived = theme.contract.derive(content)
    bundle = build_bundle(
        content, derived, render_body(content, derived, theme_id=theme.theme_id), "en", theme
    )
    written = write_bundle(Path(args.out), bundle, theme)
    print(
        f"Wrote {len(written)} files to {args.out} (serve with: python -m http.server -d {args.out})"
    )
    return 0


async def _command_generate(args: argparse.Namespace) -> int:
    theme = get_theme(args.theme)
    content = load_content(args.sample, args.content)
    issues = content_admission_issues(content)
    if issues:
        _print_json({"ok": False, "failure": failure_from_admission(issues).to_payload()})
        return 2
    if args.live:
        agent = await _live_agent(args.theme)
    else:
        from oryxenai.agents.code_generator.dev.mock_client import ReferenceModelClient

        agent = CodeGeneratorAgent(ReferenceModelClient(), theme_id=args.theme)
    context = build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.CODE_GENERATOR,
        current_state={},
        agent_input={"operation": "generate_page", "routing_policy_snapshot": {}},
        run_id=uuid4(),
    )
    trace: dict[str, Any] = {}
    out = Path(args.out) if args.out else None

    async def on_stage(stage: str) -> None:
        print(f"  ... {stage}", file=sys.stderr)

    try:
        outcome = await build_page(
            page_content=content,
            agent=agent,
            context=context,
            theme=theme,
            max_body_bytes=262144,
            trace=trace,
            reference="cg-cli",
            on_stage=on_stage,
        )
    except CodeGeneratorFailure as exc:
        _print_json(
            {
                "ok": False,
                "failure": exc.envelope.to_payload(),
                "timings_ms": trace.get("timings_ms"),
            }
        )
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
            (out / "failure.json").write_text(
                json.dumps(exc.envelope.to_payload(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            rejected = trace.pop("rejected_body_html", None)
            if rejected is not None:
                (out / "rejected_body.html").write_text(rejected, encoding="utf-8")
            (out / "trace.json").write_text(
                json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        return 1
    _print_json({"ok": True, "receipt": outcome.receipt, "timings_ms": trace.get("timings_ms")})
    if out is not None:
        written = write_bundle(out, outcome.bundle, theme)
        (out / "trace.json").write_text(
            json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote {len(written)} files to {out} (serve with: python -m http.server -d {out})")
    return 0


def _command_validate(args: argparse.Namespace) -> int:
    theme = get_theme(args.theme)
    content = load_content(args.sample, args.content)
    body = Path(args.html).read_text(encoding="utf-8")
    report = validate_page(body, content, theme)
    if report.ok:
        _print_json({"ok": True, "warnings": [issue.to_dict() for issue in report.warnings]})
        return 0
    _print_json({"ok": False, "failure": failure_from_validation(report).to_payload()})
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="code_generator", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--sample", help="Content Architect sample name, e.g. 01_strong_profile")
        p.add_argument("--content", help="JSON file with page_content (or a full CA output)")
        p.add_argument("--theme", default=DEFAULT_THEME_ID)

    prompt = sub.add_parser("prompt", help="print the exact prompt and input the model receives")
    common(prompt)
    render = sub.add_parser("render", help="write the deterministic reference page")
    common(render)
    render.add_argument("--out", required=True)
    generate = sub.add_parser("generate", help="run the production build pipeline")
    common(generate)
    generate.add_argument("--live", action="store_true", help="call the configured model")
    generate.add_argument("--out", help="folder for the bundle (or the failure evidence)")
    validate = sub.add_parser("validate", help="validate a body HTML file against content")
    common(validate)
    validate.add_argument("--html", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prompt":
        return _command_prompt(args)
    if args.command == "render":
        return _command_render(args)
    if args.command == "validate":
        return _command_validate(args)
    return asyncio.run(_command_generate(args))


if __name__ == "__main__":
    raise SystemExit(main())
