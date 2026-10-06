"""Opt-in, uncached sample benchmarks through the configured model routes.

Run explicitly: uv run python scripts/live_performance.py --output
.workspace/performance/baseline.json. Never included in standard pytest runs.
Only repository samples are used; stdout and the report contain no raw content.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from oryxenai.agents.code_generator.validate import validate_page
from oryxenai.agents.content_architect.agent import ContentArchitectAgent
from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.agents.shared.model_runtime import ModelRuntime
from oryxenai.core.settings import get_settings
from oryxenai.themes import get_theme

SAMPLES = {
    "discovery": {
        "sparse": "02_sparse_student_input.json",
        "rich": "01_software_engineer_input.json",
    },
    "content_architect": {
        "sparse": "02_sparse_no_metrics_input.json",
        "rich": "01_strong_profile_input.json",
    },
}


async def benchmark(args: argparse.Namespace) -> bool:
    config = get_settings().models.model_copy(deep=True)
    if args.ca_effort:
        for route in config.routing.operation_profiles["content_architect"].values():
            route.reasoning_effort = args.ca_effort
    runtime = ModelRuntime(config)
    records: list[dict[str, Any]] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        for repeat in range(args.runs):
            for engine in args.engines:
                key = AgentKey(engine)
                for sample_name, filename in SAMPLES[engine].items():
                    sample = json.loads(
                        (Path("src/oryxenai/agents") / engine / "samples" / filename).read_text(
                            encoding="utf-8"
                        )
                    )
                    operations = (
                        ["understand_and_question", "build_or_revise_brief"]
                        if engine == "discovery"
                        else ["build"]
                    )
                    for operation in operations:
                        agent_input = (
                            {"operation": operation, "intake": sample}
                            if engine == "discovery"
                            else sample
                        )
                        if engine == "content_architect":
                            agent_input["intake"]["selected_theme_id"] = args.theme
                        context = build_context(uuid4(), key, {}, agent_input)
                        client = runtime.routed_client(engine)
                        agent_type = (
                            DiscoveryAgent if engine == "discovery" else ContentArchitectAgent
                        )
                        agent = agent_type(client, runtime.policy_profile_name(engine))
                        record: dict[str, Any] = {
                            "engine": engine,
                            "operation": operation,
                            "sample": sample_name,
                            "repeat": repeat + 1,
                        }
                        print(
                            f"Starting {engine}/{operation}/{sample_name}/{repeat + 1}", flush=True
                        )
                        started = time.perf_counter()
                        try:
                            result = await asyncio.wait_for(agent.run(context), timeout=600)
                            record["ok"] = True
                            record["metadata"] = result.model_metadata
                            output = result.output
                            if engine == "content_architect":
                                theme = get_theme(args.theme)
                                content = output["page_content"]
                                report = validate_page(
                                    theme.contract.render_body(content),
                                    content,
                                    theme,  # type: ignore[attr-defined]
                                )
                                record["render_valid"] = report.ok
                                record["render_errors"] = [issue.code for issue in report.errors]
                                record["ok"] = report.ok
                            dossier = output.get("dossier", {})
                            record["fact_count"] = len(dossier.get("facts", []))
                            record["project_count"] = len(dossier.get("projects", []))
                            record["coverage_count"] = len(output.get("coverage_ledger", []))
                            record["claim_count"] = len(output.get("claim_grounding", []))
                            # Local sample-only evidence for human quality review; never committed.
                            review = args.output.parent / (
                                f"{args.output.stem}-{engine}-{operation}-{sample_name}-{repeat + 1}.json"
                            )
                            review.write_text(
                                json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
                            )
                        except Exception as exc:
                            record["ok"] = False
                            record["error_type"] = type(exc).__name__
                            record["error_code"] = getattr(exc, "code", "")
                        record["seconds"] = round(time.perf_counter() - started, 3)
                        records.append(record)
                        args.output.write_text(json.dumps(records, indent=2), encoding="utf-8")
                        print(
                            json.dumps({k: v for k, v in record.items() if k != "metadata"}),
                            flush=True,
                        )
    finally:
        await runtime.aclose()
    groups = {(r["engine"], r["operation"], r["sample"]) for r in records}
    for group in sorted(groups):
        rows = [r for r in records if (r["engine"], r["operation"], r["sample"]) == group]
        print(
            json.dumps(
                {
                    "group": group,
                    "median_seconds": statistics.median(r["seconds"] for r in rows),
                    "passed": sum(r["ok"] for r in rows),
                    "runs": len(rows),
                }
            )
        )
    return all(r["ok"] for r in records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, choices=range(1, 4), default=3)
    parser.add_argument("--engines", nargs="+", choices=list(SAMPLES), default=list(SAMPLES))
    parser.add_argument("--ca-effort", choices=["low", "medium"])
    parser.add_argument("--theme", default="cobalt-atlas/v2")
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(benchmark(args)) else 1)


if __name__ == "__main__":
    main()
