"""Command-line entry point for an isolated Build Preparation validation run."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from oryxenai.agents.build_preparation.fixture import FixturePreparationError, run_fixture
from oryxenai.agents.shared.model_client import build_provider_client
from oryxenai.core.settings import get_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the detached Build Preparation validation pipeline."
    )
    parser.add_argument(
        "--vdd-input",
        help="Optional JSON file containing the Visual Design Director projection.",
    )
    parser.add_argument(
        "--content-architect-input",
        help="Optional JSON file containing the approved Content Architect projection.",
    )
    parser.add_argument(
        "--live-model",
        action="store_true",
        help="Use the configured Build Preparation model profile.",
    )
    parser.add_argument(
        "--live-providers",
        action="store_true",
        help="Use live resource providers instead of deterministic fallbacks.",
    )
    parser.add_argument("--model-profile", default="", help="Optional configured model profile.")
    parser.add_argument(
        "--output-dir",
        help="Override the disposable output directory for this validation run.",
    )
    return parser


def _load_json(path_value: str | None, label: str) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Could not read the {label} JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"The {label} JSON file is invalid: {path}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"The {label} JSON file must contain an object: {path}")
    return parsed


async def _run(args: argparse.Namespace) -> None:
    settings = get_settings()
    if args.output_dir:
        settings.build_preparation.fixture_output_dir = args.output_dir
    visual_override = _load_json(args.vdd_input, "Visual Design Director")
    content_override = _load_json(args.content_architect_input, "Content Architect")

    model_client = None
    if args.live_model:
        model_client = build_provider_client(
            "build_preparation",
            settings.models,
            override_profile_name=args.model_profile or settings.build_preparation.model_profile,
        )
        if model_client is None:
            raise ValueError(
                "Live model mode requires a configured Build Preparation model profile and API key."
            )
    try:
        result = await run_fixture(
            settings,
            raw_override=visual_override,
            content_architect_override=content_override,
            live_model=args.live_model,
            live_providers=args.live_providers,
            model_profile=args.model_profile,
            model_client=model_client,
        )
    finally:
        close = getattr(model_client, "aclose", None)
        if close is not None:
            await close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    args = _parser().parse_args()
    try:
        asyncio.run(_run(args))
    except (FixturePreparationError, ValueError) as exc:
        print(f"Build Preparation validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
