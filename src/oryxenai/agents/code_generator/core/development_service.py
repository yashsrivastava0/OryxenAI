"""Standalone Code Generator Phase 1 run creation and read projections."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_schemas import (
    AdmittedInputReference,
    DevelopmentEvent,
    DevelopmentRunProjection,
    DevelopmentRunStatus,
)
from oryxenai.agents.code_generator.core.provider_preflight import (
    ProviderPreflightError,
    run_provider_preflight,
)
from oryxenai.agents.code_generator.core.workspace import repository_root
from oryxenai.db.models.code_generator_development import CodeGeneratorDevelopmentRun
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.jobs.service import JobService

_PLAN_JOB_KIND = "code_generator.plan"
_ACQUIRE_JOB_KIND = "code_generator.acquire"
_GENERATE_JOB_KIND = "code_generator.generate"
_VERIFY_JOB_KIND = "code_generator.verify_and_preview"
_ACQUIRE_SCOPE = "code_generator.acquire"
_GENERATE_SCOPE = "code_generator.generate"
_VERIFY_SCOPE = "code_generator.verify_and_preview"


class DevelopmentRunError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 422,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class CodeGeneratorDevelopmentService:
    def __init__(
        self, repository: CodeGeneratorDevelopmentRepository, jobs: JobService, settings: Any
    ) -> None:
        self._repo = repository
        self._jobs = jobs
        self._settings = settings
        self._inputs = DevelopmentInputAdapter(settings)

    def fixtures(self) -> list[dict[str, str]]:
        return self._inputs.fixtures()

    async def provider_preflight(self) -> dict[str, Any]:
        """Run the same no-context provider check used by production starts."""

        profile_names = [
            self._settings.code_generator_development.director_profile,
            self._settings.code_generator_development.planner_profile,
            self._settings.code_generator_generation.foundation_profile,
            self._settings.code_generator_generation.route_profile,
            self._settings.code_generator_generation.compose_profile,
            self._settings.code_generator_generation.integration_profile,
            self._settings.code_generator_generation.repair_profile,
        ]
        try:
            result = await run_provider_preflight(self._settings, profile_names)
        except ProviderPreflightError as exc:
            raise DevelopmentRunError(
                exc.code,
                exc.message,
                status_code=503,
                details=exc.details,
            ) from exc
        return result

    def readiness(self) -> dict[str, Any]:
        """Return non-secret prerequisites so the developer UI never implies readiness."""

        profile_names = {
            "director": self._settings.code_generator_development.director_profile,
            "planner": self._settings.code_generator_development.planner_profile,
            "foundation": self._settings.code_generator_generation.foundation_profile,
            "route": self._settings.code_generator_generation.route_profile,
            "compose": self._settings.code_generator_generation.compose_profile,
            "integration": self._settings.code_generator_generation.integration_profile,
            "repair": self._settings.code_generator_generation.repair_profile,
        }
        profiles: dict[str, bool] = {}
        for operation, profile_name in profile_names.items():
            profile = self._settings.models.get_profile(str(profile_name))
            profiles[operation] = bool(
                profile
                and profile.model.strip()
                and profile.api_key_env.strip()
                and bool(os.environ.get(profile.api_key_env))
                and profile.capabilities
                and profile.capabilities.json_schema_mode
            )
        npm = str(self._settings.code_generator_dependencies.npm_executable or "")
        npm_available = bool(npm and shutil.which(npm))
        packs = self.build_preparation_packs()
        latest_pack = next((pack for pack in packs if pack.get("eligible")), None)
        best_pack = max(
            (pack for pack in packs if pack.get("eligible")),
            key=lambda pack: tuple(pack.get("selection_rank", []) or []),
            default=None,
        )
        browser_available = browser_ready(self._settings.code_generator_verification)
        generation_ready = all(
            profiles[operation]
            for operation in ("foundation", "route", "compose", "integration", "repair")
        )
        readiness_blockers = [
            blocker
            for blocker, ready in (
                ("planner", profiles["planner"]),
                ("generation_profiles", generation_ready),
                ("npm", npm_available),
                ("verification_browser", browser_available),
                ("build_preparation_pack", best_pack is not None),
            )
            if not ready
        ]
        return {
            "planning_ready": profiles["director"] and profiles["planner"],
            "generation_ready": generation_ready,
            "package_manager_ready": npm_available,
            "profiles": profiles,
            "offline_install_policy": not bool(
                self._settings.code_generator_dependencies.allow_network_install
            ),
            "fixture_ids": [item["fixture_id"] for item in self.fixtures()],
            "build_preparation_pack_ready": latest_pack is not None,
            "build_preparation_latest": latest_pack,
            "build_preparation_best": best_pack,
            "browser_ready": browser_available,
            "provider_preflight": {
                "status": "required",
                "checked": False,
                "private_context_sent": False,
            },
            "can_start_latest": not readiness_blockers,
            "can_start_best": not readiness_blockers,
            "readiness_blockers": readiness_blockers,
        }

    async def create_fixture(
        self, fixture_id: str, *, idempotency_key: str
    ) -> DevelopmentRunProjection:
        return await self._create(
            self._inputs.from_fixture(fixture_id), idempotency_key=idempotency_key
        )

    def build_preparation_packs(self) -> list[dict[str, Any]]:
        return self._inputs.list_build_preparation_packs()

    async def create_from_build_preparation(
        self, pack: str, *, idempotency_key: str
    ) -> DevelopmentRunProjection:
        return await self._create(
            self._inputs.from_build_preparation_mirror(pack),
            idempotency_key=idempotency_key,
            pack_selection="best" if pack in {"best", "latest"} else "explicit",
            requested_pack=pack,
        )

    async def create_upload(
        self, *, filename: str, mime_type: str, data: bytes, idempotency_key: str
    ) -> DevelopmentRunProjection:
        return await self._create(
            self._inputs.from_upload(filename=filename, mime_type=mime_type, data=data),
            idempotency_key=idempotency_key,
        )

    async def _create(
        self,
        reference: AdmittedInputReference,
        *,
        idempotency_key: str,
        pack_selection: str = "",
        requested_pack: str = "",
    ) -> DevelopmentRunProjection:
        if not idempotency_key.strip():
            raise DevelopmentRunError(
                "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", status_code=400
            )
        existing = await self._repo.find_idempotent(idempotency_key)
        if existing is not None:
            if existing.input_reference.get("source_sha256") != reference.source_sha256:
                raise DevelopmentRunError(
                    "IDEMPOTENCY_KEY_CONFLICT",
                    "Idempotency-Key was already used for a different immutable input.",
                    status_code=409,
                )
            return _projection(existing)
        run = await self._repo.create(
            input_reference=reference.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            auto_advance=True,
        )
        selected_pack_receipt = None
        if reference.mode == "build_preparation_mirror":
            selected_pack_receipt = {
                "source_id": reference.source_id,
                "source_sha256": reference.source_sha256,
                "selection": pack_selection or "explicit",
                "requested_pack": requested_pack or reference.source_id,
                "selected_at": run.created_at.isoformat(),
            }
            run = (
                await self._repo.compare_and_swap(
                    run.id,
                    expected_revision=run.revision,
                    values={"selected_pack_receipt": selected_pack_receipt},
                )
                or run
            )
        await self._repo.append_event(
            run.id,
            event_type="created",
            level="info",
            message="Development planning run created.",
        )
        job = await self._jobs.enqueue(
            _PLAN_JOB_KIND,
            {"development_run_id": str(run.id)},
            idempotency_scope="code_generator.plan",
            idempotency_key=f"{run.id}:{reference.source_sha256}",
        )
        updated = await self._repo.compare_and_swap(
            run.id,
            expected_revision=run.revision,
            values={"status": DevelopmentRunStatus.QUEUED.value, "background_job_id": job.id},
        )
        if updated is None:
            raise DevelopmentRunError(
                "RUN_REVISION_CONFLICT",
                "The development run changed while it was queued.",
                status_code=409,
            )
        await self._repo.append_event(
            run.id,
            event_type="queued",
            level="info",
            message="Admission and planning job queued.",
            details={"job_id": str(job.id)},
        )
        return _projection(updated)

    async def get(self, run_id: UUID) -> DevelopmentRunProjection:
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        return _projection(run)

    async def events(self, run_id: UUID, *, after: int, limit: int) -> list[DevelopmentEvent]:
        if await self._repo.get(run_id) is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        limit = min(
            max(1, limit), int(self._settings.code_generator_development.max_events_page_size)
        )
        return [
            DevelopmentEvent.model_validate(
                {
                    "sequence": event.sequence,
                    "event_type": event.event_type,
                    "level": event.level,
                    "message": event.message,
                    "details": event.details,
                    "created_at": event.created_at.isoformat(),
                }
            )
            for event in await self._repo.events(run_id, after=after, limit=limit)
        ]

    async def plan(self, run_id: UUID) -> dict[str, Any]:
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if (
            run.status
            not in {
                DevelopmentRunStatus.PLANNED.value,
                DevelopmentRunStatus.ACQUIRING.value,
                DevelopmentRunStatus.ACQUIRED.value,
                DevelopmentRunStatus.QUEUED.value,
                DevelopmentRunStatus.GENERATING_FOUNDATION.value,
                DevelopmentRunStatus.GENERATING_ROUTES.value,
                DevelopmentRunStatus.INTEGRATING.value,
                DevelopmentRunStatus.SOURCE_READY.value,
                DevelopmentRunStatus.BUILDING.value,
                DevelopmentRunStatus.SMOKE_TESTING.value,
                DevelopmentRunStatus.REPAIRING.value,
                DevelopmentRunStatus.READY.value,
            }
            or run.plan is None
        ):
            raise DevelopmentRunError(
                "PLAN_NOT_READY", "A validated SitePlan is not available yet.", status_code=409
            )
        return dict(run.plan)

    async def acquire(self, run_id: UUID, *, idempotency_key: str) -> DevelopmentRunProjection:
        if not idempotency_key.strip():
            raise DevelopmentRunError(
                "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", status_code=400
            )
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if run.plan is None or run.planner_receipt is None:
            raise DevelopmentRunError(
                "RUN_NOT_PLANNED",
                "Only a planned development run can acquire resources.",
                status_code=409,
            )
        plan_hash = str(run.planner_receipt.get("plan_hash", ""))
        if not plan_hash:
            raise DevelopmentRunError(
                "RUN_NOT_PLANNED",
                "The planned run has no receipt-bound plan hash.",
                status_code=409,
            )
        job_key = f"{run.id}:{plan_hash}"
        if run.status == DevelopmentRunStatus.NEEDS_ATTENTION.value:
            job_key = f"{job_key}:retry:{run.current_attempt + 1}"
        existing_job = await self._jobs.find_idempotent(_ACQUIRE_SCOPE, job_key)
        if run.status in {
            DevelopmentRunStatus.ACQUIRING.value,
            DevelopmentRunStatus.ACQUIRED.value,
        }:
            if existing_job is not None or run.status == DevelopmentRunStatus.ACQUIRED.value:
                return _projection(run)
            raise DevelopmentRunError(
                "RUN_ALREADY_IN_PROGRESS",
                "Resource acquisition is already in progress.",
                status_code=409,
            )
        if run.status not in {
            DevelopmentRunStatus.PLANNED.value,
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
        }:
            raise DevelopmentRunError(
                "RUN_NOT_PLANNED",
                "Only a planned development run can acquire resources.",
                status_code=409,
            )
        job = await self._jobs.enqueue(
            _ACQUIRE_JOB_KIND,
            {"development_run_id": str(run.id)},
            idempotency_scope=_ACQUIRE_SCOPE,
            idempotency_key=job_key,
        )
        values: dict[str, object] = {
            "status": DevelopmentRunStatus.ACQUIRING.value,
            "acquire_job_id": job.id,
            "issues": [],
        }
        updated = await self._repo.compare_and_swap(
            run.id,
            expected_revision=run.revision,
            values=values,
        )
        if updated is None:
            raise DevelopmentRunError(
                "RUN_REVISION_CONFLICT",
                "The development run changed while acquisition was queued.",
                status_code=409,
            )
        await self._repo.append_event(
            run.id,
            event_type="queued_acquire",
            level="info",
            message="Initial resource and dependency acquisition queued.",
            details={"job_id": str(job.id)},
        )
        return _projection(updated)

    async def acquisition(self, run_id: UUID) -> dict[str, Any]:
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if run.status != DevelopmentRunStatus.ACQUIRED.value or not run.resource_ledger:
            raise DevelopmentRunError(
                "ACQUIRE_NOT_READY", "Resource acquisition is not available yet.", status_code=409
            )
        ledger = dict(run.resource_ledger)
        return {
            "summary": dict(run.acquire_summary or {}),
            "requests": list(cast(list[object], ledger.get("requests", []))),
            "receipts": list(cast(list[object], ledger.get("receipts", []))),
            "bindings": list(cast(list[object], ledger.get("active_bindings", []))),
            "plan_deltas": list(cast(list[object], ledger.get("plan_deltas", []))),
        }

    async def dependencies(self, run_id: UUID) -> dict[str, Any]:
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if run.status != DevelopmentRunStatus.ACQUIRED.value or not run.dependency_ledger:
            raise DevelopmentRunError(
                "ACQUIRE_NOT_READY", "Dependency acquisition is not available yet.", status_code=409
            )
        return dict(run.dependency_ledger)

    async def plan_deltas(self, run_id: UUID) -> dict[str, Any]:
        acquisition = await self.acquisition(run_id)
        deltas = acquisition.get("plan_deltas", [])
        return {"count": len(deltas), "deltas": deltas}

    async def generate(self, run_id: UUID, *, idempotency_key: str) -> DevelopmentRunProjection:
        if not idempotency_key.strip():
            raise DevelopmentRunError(
                "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", status_code=400
            )
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if run.plan is None or run.planner_receipt is None:
            raise DevelopmentRunError(
                "RUN_NOT_PLANNED",
                "A validated plan is required before generation.",
                status_code=409,
            )
        if run.status not in {
            DevelopmentRunStatus.ACQUIRED.value,
            DevelopmentRunStatus.NEEDS_ATTENTION.value,
            DevelopmentRunStatus.SOURCE_READY.value,
        }:
            raise DevelopmentRunError(
                "RUN_NOT_ACQUIRED",
                "Initial resource acquisition must complete before source generation.",
                status_code=409,
            )
        if run.status == DevelopmentRunStatus.SOURCE_READY.value:
            return _projection(run)
        plan_hash = str(run.planner_receipt.get("plan_hash", ""))
        resource_hash = str((run.resource_ledger or {}).get("ledger_hash", ""))
        dependency_hash = str((run.dependency_ledger or {}).get("dependency_ledger_hash", ""))
        attempt_key = (
            f"{run.id}:{plan_hash}:{resource_hash}:{dependency_hash}:{run.current_attempt + 1}"
        )
        existing_job = await self._jobs.find_idempotent(_GENERATE_SCOPE, attempt_key)
        if run.status in {
            DevelopmentRunStatus.GENERATING_FOUNDATION.value,
            DevelopmentRunStatus.GENERATING_ROUTES.value,
            DevelopmentRunStatus.INTEGRATING.value,
        }:
            if existing_job is not None or run.generation_job_id is not None:
                return _projection(run)
            raise DevelopmentRunError(
                "RUN_ALREADY_IN_PROGRESS",
                "Source generation is already in progress.",
                status_code=409,
            )
        job = await self._jobs.enqueue(
            _GENERATE_JOB_KIND,
            {"development_run_id": str(run.id)},
            idempotency_scope=_GENERATE_SCOPE,
            idempotency_key=attempt_key,
        )
        updated = await self._repo.compare_and_swap(
            run.id,
            expected_revision=run.revision,
            values={
                "status": DevelopmentRunStatus.QUEUED.value,
                "generation_job_id": job.id,
                "generation_projection": None,
                "source_checkpoint": None,
                "source_summary": {},
                "issues": [],
            },
        )
        if updated is None:
            raise DevelopmentRunError(
                "RUN_REVISION_CONFLICT",
                "The development run changed while generation was queued.",
                status_code=409,
            )
        await self._repo.append_event(
            run.id,
            event_type="queued_generate",
            level="info",
            message="Progressive source generation queued.",
            details={"job_id": str(job.id)},
        )
        return _projection(updated)

    async def generation(self, run_id: UUID) -> dict[str, Any]:
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if not run.generation_projection:
            raise DevelopmentRunError(
                "GENERATION_NOT_READY", "Source generation has not started yet.", status_code=409
            )
        return dict(run.generation_projection)

    async def verify(self, run_id: UUID, *, idempotency_key: str) -> DevelopmentRunProjection:
        if not idempotency_key.strip():
            raise DevelopmentRunError(
                "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", status_code=400
            )
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if run.source_checkpoint is None or run.generation_projection is None:
            raise DevelopmentRunError(
                "SOURCE_NOT_READY",
                "An accepted source checkpoint is required before verification.",
                status_code=409,
            )
        if run.status in {
            DevelopmentRunStatus.BUILDING.value,
            DevelopmentRunStatus.SMOKE_TESTING.value,
            DevelopmentRunStatus.REPAIRING.value,
        }:
            if run.verification_job_id is not None:
                return _projection(run)
            raise DevelopmentRunError(
                "RUN_ALREADY_IN_PROGRESS",
                "Final verification is already in progress.",
                status_code=409,
            )
        candidate_key = str(run.source_checkpoint.get("checkpoint_hash", ""))
        if not candidate_key:
            raise DevelopmentRunError(
                "SOURCE_CHECKPOINT_INVALID",
                "The source checkpoint has no stable identity.",
                status_code=409,
            )
        # Revision (bumped by every terminal write) keeps each retry a new
        # attempt while staying stable while one attempt is in flight, so
        # repeated POSTs can never silently reuse a completed job.
        attempt_key = f"{run.id}:{candidate_key}:{run.revision}"
        existing_job = await self._jobs.find_idempotent(_VERIFY_SCOPE, attempt_key)
        if (
            existing_job is not None
            and run.verification_job_id is not None
            and str(getattr(existing_job, "status", "")) in {"queued", "running"}
        ):
            return _projection(run)
        job = await self._jobs.enqueue(
            _VERIFY_JOB_KIND,
            {"development_run_id": str(run.id)},
            idempotency_scope=_VERIFY_SCOPE,
            idempotency_key=attempt_key,
        )
        updated = await self._repo.compare_and_swap(
            run.id,
            expected_revision=run.revision,
            values={
                "status": DevelopmentRunStatus.QUEUED.value,
                "verification_job_id": job.id,
                "verification_projection": None,
                "terminal_failure": None,
                "issues": [],
            },
        )
        if updated is None:
            raise DevelopmentRunError(
                "RUN_REVISION_CONFLICT",
                "The development run changed while verification was queued.",
                status_code=409,
            )
        await self._repo.append_event(
            run.id,
            event_type="queued_verify",
            level="info",
            message="Final build and text/DOM verification queued.",
            details={"job_id": str(job.id)},
        )
        return _projection(updated)

    async def verification(self, run_id: UUID) -> dict[str, Any]:
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if not run.verification_projection:
            raise DevelopmentRunError(
                "VERIFICATION_NOT_READY", "Final verification has not started yet.", status_code=409
            )
        return dict(run.verification_projection)

    async def preview(self, run_id: UUID) -> dict[str, Any]:
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        return {
            "status": run.status,
            "active_preview": dict(run.active_preview) if run.active_preview else None,
            "candidate": dict(run.candidate_artifact) if run.candidate_artifact else None,
            "pending_promotion": dict(run.pending_promotion) if run.pending_promotion else None,
        }

    async def source_manifest(self, run_id: UUID) -> dict[str, Any]:
        run = await self._repo.get(run_id)
        if run is None:
            raise DevelopmentRunError(
                "RUN_NOT_FOUND", "Development run was not found.", status_code=404
            )
        if not run.source_checkpoint:
            raise DevelopmentRunError(
                "SOURCE_NOT_READY",
                "An accepted source checkpoint is not available yet.",
                status_code=409,
            )
        manifest_path = str(run.source_checkpoint.get("manifest_path", ""))
        if not manifest_path:
            return {"checkpoint": dict(run.source_checkpoint), "files": []}
        from pathlib import Path

        configured_root = Path(self._settings.code_generator_development.input_root)
        root = (
            configured_root
            if configured_root.is_absolute()
            else (repository_root() / configured_root).resolve()
        )
        path = (root / manifest_path).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise DevelopmentRunError(
                "SOURCE_MANIFEST_MISSING", "The source manifest is unavailable.", status_code=409
            )
        try:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise DevelopmentRunError(
                "SOURCE_MANIFEST_INVALID", "The source manifest could not be read.", status_code=409
            ) from exc
        return {"checkpoint": dict(run.source_checkpoint), "manifest": payload}


def browser_ready(verification: Any) -> bool:
    """Honest cheap probe: Playwright importable and a browser is available.

    Deliberately does not launch the driver — the sync driver's teardown is
    unreliable on Windows; the verification path itself launches async. A
    configured executable is a valid browser installation even when the
    browser was installed by the container OS rather than Playwright.
    """

    try:
        import playwright  # noqa: F401
    except Exception:
        return False
    configured_executable = str(getattr(verification, "browser_executable", "") or "").strip()
    if configured_executable:
        configured_path = Path(configured_executable)
        if configured_path.is_file() and os.access(configured_path, os.X_OK):
            return True
        if shutil.which(configured_executable):
            return True
    root = Path(
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
        or Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ms-playwright"
    )
    if not root.is_dir():
        return False
    return any(root.glob(f"{getattr(verification, 'browser_name', 'chromium')!s}-*"))


def _projection(run: CodeGeneratorDevelopmentRun) -> DevelopmentRunProjection:
    return DevelopmentRunProjection.model_validate(
        {
            "run_id": str(run.id),
            "status": run.status,
            "revision": run.revision,
            "current_attempt": run.current_attempt,
            "run_mode": str(getattr(run, "run_mode", "development") or "development"),
            "portfolio_session_id": str(getattr(run, "portfolio_session_id", "") or ""),
            "auto_advance": bool(getattr(run, "auto_advance", True)),
            "coordinator_stage": str(getattr(run, "coordinator_stage", "plan") or "plan"),
            "pipeline_contract_version": str(
                getattr(run, "pipeline_contract_version", "code-generator-v3")
                or "code-generator-v3"
            ),
            "trace_id": str(getattr(run, "trace_id", "") or ""),
            "active_attempt_id": str(getattr(run, "active_attempt_id", "") or ""),
            "selected_pack_receipt": getattr(run, "selected_pack_receipt", None),
            "build_preparation_source_ref": getattr(run, "build_preparation_source_ref", None),
            "artifact_reference": getattr(run, "artifact_reference", None),
            "artifact_receipt": getattr(run, "artifact_receipt", None),
            "preflight_receipt": getattr(run, "preflight_receipt", None),
            "creative_direction": getattr(run, "creative_direction", None),
            "integration_review": getattr(run, "integration_review", None),
            "job_id": str(run.background_job_id or ""),
            "input": run.input_reference,
            "input_receipt": run.input_receipt,
            "context_receipt": run.context_receipt,
            "planner_receipt": run.planner_receipt,
            "plan_summary": run.plan_summary,
            "acquire_receipt": run.acquire_receipt,
            "resource_ledger": run.resource_ledger,
            "dependency_ledger": run.dependency_ledger,
            "acquire_summary": run.acquire_summary or None,
            "plan_delta_count": run.plan_delta_count,
            "generation_job_id": str(run.generation_job_id or ""),
            "generation": run.generation_projection,
            "source_checkpoint": run.source_checkpoint,
            "source_summary": run.source_summary or {},
            "verification_job_id": str(run.verification_job_id or ""),
            "verification": run.verification_projection,
            "candidate_artifact": run.candidate_artifact,
            "pending_promotion": run.pending_promotion,
            "active_preview": run.active_preview,
            "terminal_failure": run.terminal_failure,
            "issues": run.issues,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
        }
    )
