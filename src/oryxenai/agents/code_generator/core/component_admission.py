"""Static and disposable-toolchain admission for optional component source."""

from __future__ import annotations

import contextlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from oryxenai.agents.code_generator.core.dependency_manager import (
    _package_name_from_specifier,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    LocalMaterialFile,
    ResourceCandidate,
    ResourceRequest,
)
from oryxenai.agents.code_generator.core.process_runner import (
    ProcessRunnerError,
    resolve_npm_executable,
    run_command,
)
from oryxenai.agents.code_generator.core.workspace import repository_root

_IMPORT_SPECIFIER_RE = re.compile(
    r"""(?:\bfrom|\bimport)\s+["']([^"']+)["']|
    \bimport\s*\(\s*["']([^"']+)["']\s*\)|
    \brequire\(\s*["']([^"']+)["']\s*\)"""
)
_EXPORT_DECL_RE = re.compile(
    r"\bexport\s+(?:declare\s+)?(?:const|let|var|function|class|type|interface|enum)\s+"
    r"([A-Za-z_$][\w$]*)"
)
_EXPORT_LIST_RE = re.compile(r"\bexport\s*\{([^}]*)\}")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_$][\w$]*$")
_SOURCE_SUFFIXES = {".css", ".js", ".jsx", ".ts", ".tsx"}


class ComponentAdmissionError(ValueError):
    """A component candidate cannot safely enter the executable source tree."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _normalized_material_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    path = Path(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or any(part in {"", "."} for part in path.parts)
        or path.suffix.casefold() not in _SOURCE_SUFFIXES
    ):
        raise ComponentAdmissionError(
            "COMPONENT_SOURCE_PATH_INVALID",
            f"Component source path {value!r} is outside the admitted source types.",
        )
    return normalized


def _read_material_files(
    material_files: list[LocalMaterialFile], *, storage_root: Path
) -> dict[str, str]:
    files: dict[str, str] = {}
    root = storage_root.resolve()
    for item in material_files:
        relative = _normalized_material_path(item.local_path)
        if relative in files:
            raise ComponentAdmissionError(
                "COMPONENT_SOURCE_DUPLICATE_PATH",
                f"Component source contains duplicate path {relative!r}.",
            )
        source = (root / relative).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ComponentAdmissionError(
                "COMPONENT_SOURCE_MISSING",
                f"Component source file {relative!r} is unavailable in the material store.",
            )
        try:
            files[relative] = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ComponentAdmissionError(
                "COMPONENT_SOURCE_ENCODING_INVALID",
                f"Component source file {relative!r} is not readable UTF-8.",
            ) from exc
    if not files:
        raise ComponentAdmissionError(
            "COMPONENT_SOURCE_MISSING", "The component candidate returned no source files."
        )
    return files


def _candidate_path_matches(value: str, files: dict[str, str]) -> bool:
    normalized = value.replace("\\", "/").strip("/")
    candidates = [normalized]
    if not Path(normalized).suffix:
        candidates.extend(
            f"{normalized}{suffix}" for suffix in (".ts", ".tsx", ".js", ".jsx", ".css")
        )
        candidates.extend(
            f"{normalized}/index{suffix}" for suffix in (".ts", ".tsx", ".js", ".jsx")
        )
    return any(
        candidate in files or any(path.endswith(f"/{candidate}") for path in files)
        for candidate in candidates
    )


def _scaffold_source_root(settings: Any) -> Path | None:
    config = getattr(settings, "code_generator_generation", None)
    if config is None:
        return None
    root = Path(str(getattr(config, "scaffold_root", "")))
    if not root.is_absolute():
        root = (repository_root() / root).resolve()
    source = (root / str(getattr(config, "scaffold_profile", "")) / "src").resolve()
    return source if source.is_dir() and source.is_relative_to(root) else None


def _local_import_is_available(
    specifier: str,
    *,
    source_path: str,
    files: dict[str, str],
    repo_dir: Path,
    scaffold_src: Path | None,
) -> bool:
    if specifier.startswith("@/"):
        relative = specifier.removeprefix("@/")
        for root in (repo_dir / "src", scaffold_src):
            if root is None:
                continue
            target = (root / relative).resolve()
            if not target.is_relative_to(root.resolve()):
                continue
            if target.is_file() or any(
                (target.parent / f"{target.name}{suffix}").is_file()
                for suffix in (".ts", ".tsx", ".js", ".jsx", ".css")
            ):
                return True
        return _candidate_path_matches(specifier.removeprefix("@/"), files)
    if not specifier.startswith("."):
        return True
    target_path = (Path(source_path).parent / specifier).as_posix()
    return _candidate_path_matches(target_path, files)


def _declared_exports(files: dict[str, str]) -> set[str]:
    exports: set[str] = set()
    for source in files.values():
        exports.update(_EXPORT_DECL_RE.findall(source))
        if re.search(r"\bexport\s+default\b", source):
            exports.add("default")
        for raw in _EXPORT_LIST_RE.findall(source):
            for item in raw.split(","):
                name = item.strip().split(" as ", 1)[-1].strip()
                if _IDENTIFIER_RE.fullmatch(name):
                    exports.add(name)
    return exports


def _repo_dependency_names(repo_dir: Path) -> set[str]:
    package_json = repo_dir / "package.json"
    if not package_json.is_file():
        return set()
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return set()
    if not isinstance(payload, dict):
        return set()
    names: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        values = payload.get(key, {})
        if isinstance(values, dict):
            names.update(str(name) for name in values)
    return names


def _package_subpath_is_exported(package_name: str, specifier: str, *, repo_dir: Path) -> bool:
    subpath = specifier[len(package_name) :].lstrip("/")
    if not subpath:
        return True
    package_json = repo_dir / "node_modules" / package_name / "package.json"
    if not package_json.is_file():
        # The dependency manager proves the package pin and lock before this
        # check's disposable TypeScript pass. Static admission remains useful
        # for an empty dependency workspace and the configured package allowlist
        # is the safe upper bound until the package is installed.
        return True
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    exports = payload.get("exports")
    if exports is None:
        return True
    if isinstance(exports, str):
        return False
    if isinstance(exports, dict):
        key = f"./{subpath}"
        return key in exports or any(
            pattern.endswith("*") and key.startswith(pattern[:-1]) for pattern in exports
        )
    return False


def validate_component_candidate(
    material_files: list[LocalMaterialFile],
    *,
    storage_root: Path,
    candidate: ResourceCandidate,
    request: ResourceRequest,
    repo_dir: Path,
    settings: Any,
) -> dict[str, Any]:
    """Validate path, alias, export, dependency and CSS compatibility."""

    files = _read_material_files(material_files, storage_root=storage_root)
    scaffold_src = _scaffold_source_root(settings)
    installed_or_declared = _repo_dependency_names(repo_dir)
    supported = set(getattr(settings.code_generator_dependencies, "supported_packages", {}) or {})
    required_exports = set(request.technical_constraints.required_exports)
    missing_exports = sorted(required_exports - _declared_exports(files))
    if missing_exports:
        raise ComponentAdmissionError(
            "COMPONENT_EXPORT_MISSING",
            "The component does not provide required exports: " + ", ".join(missing_exports[:8]),
        )
    for source_path, source in files.items():
        for match in _IMPORT_SPECIFIER_RE.finditer(source):
            specifier = match.group(1) or match.group(2) or match.group(3) or ""
            if specifier.startswith((".", "@/")):
                if not _local_import_is_available(
                    specifier,
                    source_path=source_path,
                    files=files,
                    repo_dir=repo_dir,
                    scaffold_src=scaffold_src,
                ):
                    raise ComponentAdmissionError(
                        "COMPONENT_LOCAL_IMPORT_MISSING",
                        f"The component import {specifier!r} from {source_path!r} has no admitted target.",
                    )
                continue
            package_name = _package_name_from_specifier(specifier)
            if not package_name:
                continue
            if package_name not in installed_or_declared and package_name not in supported:
                raise ComponentAdmissionError(
                    "COMPONENT_DEPENDENCY_UNSUPPORTED",
                    f"The component imports unsupported package {package_name!r}.",
                )
            if not _package_subpath_is_exported(package_name, specifier, repo_dir=repo_dir):
                raise ComponentAdmissionError(
                    "COMPONENT_PACKAGE_EXPORT_UNAVAILABLE",
                    f"Package {package_name!r} does not export import {specifier!r}.",
                )
    metadata = candidate.technical_metadata
    css_required = bool(metadata.get("css_required") or metadata.get("requires_css"))
    if css_required and not any(path.casefold().endswith(".css") for path in files):
        raise ComponentAdmissionError(
            "COMPONENT_CSS_EXPECTATION_UNMET",
            "The component declares CSS support but returned no CSS source file.",
        )
    required_css_paths = {
        str(value).replace("\\", "/").strip("/")
        for value in metadata.get("required_css_paths", [])
        if str(value).strip()
    }
    if required_css_paths and not required_css_paths.issubset(files):
        raise ComponentAdmissionError(
            "COMPONENT_CSS_EXPECTATION_UNMET",
            "The component omitted one or more required CSS source files.",
        )
    return {
        "candidate_id": candidate.candidate_id,
        "source_file_count": len(files),
        "source_paths": sorted(files),
        "exports": sorted(_declared_exports(files)),
        "imports": sorted(
            {
                specifier
                for source in files.values()
                for match in _IMPORT_SPECIFIER_RE.finditer(source)
                for specifier in [match.group(1) or match.group(2) or match.group(3) or ""]
                if specifier
            }
        ),
        "css_present": any(path.casefold().endswith(".css") for path in files),
    }


async def run_component_toolchain_admission(
    material_files: list[LocalMaterialFile],
    *,
    storage_root: Path,
    candidate: ResourceCandidate,
    request: ResourceRequest,
    repo_dir: Path,
    settings: Any,
) -> dict[str, Any]:
    """Type-check a candidate in a temporary source namespace.

    The namespace is deleted in ``finally`` and is never copied to the final
    generation workspace. The package manager and TypeScript command remain
    the configured worker commands, with no shell or unrestricted install.
    """

    static = validate_component_candidate(
        material_files,
        storage_root=storage_root,
        candidate=candidate,
        request=request,
        repo_dir=repo_dir,
        settings=settings,
    )
    if not bool(getattr(settings.code_generator_generation, "use_real_typecheck", False)):
        return {**static, "typecheck": "skipped_by_configuration"}
    # Keep a stable relative layout so relative imports in the fetched source
    # resolve exactly as they did in the static candidate check.
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", candidate.candidate_id).strip("_") or "component"
    admission_root = repo_dir / "src" / "generated" / "__admission__" / safe_id
    admission_root.mkdir(parents=True, exist_ok=True)
    source_root = storage_root.resolve()
    config_path = repo_dir / f"tsconfig.component-admission-{safe_id}.json"
    created_scaffold_files: list[Path] = []
    try:
        scaffold_config = settings.code_generator_generation
        scaffold_root = Path(str(scaffold_config.scaffold_root))
        if not scaffold_root.is_absolute():
            scaffold_root = (repository_root() / scaffold_root).resolve()
        scaffold_src = (scaffold_root / str(scaffold_config.scaffold_profile) / "src").resolve()
        if scaffold_src.is_dir() and scaffold_src.is_relative_to(scaffold_root):
            target_root = repo_dir / "src"
            for source in scaffold_src.rglob("*"):
                if not source.is_file():
                    continue
                target = target_root / source.relative_to(scaffold_src)
                if target.exists():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                created_scaffold_files.append(target)
        paths: list[str] = []
        raw_paths = [_normalized_material_path(item.local_path) for item in material_files]
        path_parts = [Path(value).parts for value in raw_paths]
        common_parts: list[str] = []
        for parts in zip(*path_parts, strict=False):
            if len(set(parts)) != 1:
                break
            common_parts.append(parts[0])
        if len(common_parts) == len(path_parts[0]):
            common_parts.pop()
        component_prefix = Path(*common_parts) if common_parts else Path()
        for item in material_files:
            relative = _normalized_material_path(item.local_path)
            source = (source_root / relative).resolve()
            source_relative = Path(relative)
            if component_prefix.parts:
                source_relative = source_relative.relative_to(component_prefix)
            target = (admission_root / source_relative).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            paths.append(target.relative_to(repo_dir).as_posix())
        config_path.write_text(
            json.dumps(
                {
                    "compilerOptions": {
                        "target": "ES2022",
                        "lib": ["ES2022", "DOM", "DOM.Iterable"],
                        "module": "ESNext",
                        "moduleResolution": "Bundler",
                        "jsx": "react-jsx",
                        "strict": True,
                        "skipLibCheck": True,
                        "esModuleInterop": True,
                        "allowSyntheticDefaultImports": True,
                        "baseUrl": ".",
                        "paths": {"@/*": ["./src/*"]},
                        "noEmit": True,
                    },
                    "include": paths,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        npm = resolve_npm_executable(settings)
        if not npm:
            raise ComponentAdmissionError(
                "COMPONENT_TOOLCHAIN_UNAVAILABLE", "The configured npm executable is unavailable."
            )
        if not (repo_dir / "node_modules" / "typescript").is_dir():
            from oryxenai.agents.code_generator.core.check_runner import prepare_toolchain

            issue = await prepare_toolchain(repo_dir, settings=settings)
            if issue is not None:
                raise ComponentAdmissionError(
                    "COMPONENT_TOOLCHAIN_UNAVAILABLE", issue.normalized_message
                )
        try:
            result = await run_command(
                [npm, "exec", "--", "tsc", "--noEmit", "-p", config_path.name],
                cwd=repo_dir,
                timeout_seconds=float(settings.code_generator_generation.typecheck_timeout_seconds),
            )
        except ProcessRunnerError as exc:
            raise ComponentAdmissionError("COMPONENT_TYPECHECK_START_FAILED", exc.message) from exc
        if result.timed_out or result.returncode != 0:
            raise ComponentAdmissionError(
                "COMPONENT_TYPECHECK_FAILED",
                "The optional component failed the disposable TypeScript admission check: "
                + " ".join(result.combined_output.split())[:400],
            )
        return {**static, "typecheck": "passed"}
    finally:
        try:
            if admission_root.exists():
                shutil.rmtree(admission_root, ignore_errors=True)
            parent = admission_root.parent
            src_root = (repo_dir / "src").resolve()
            while parent.is_relative_to(src_root) and parent != src_root:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
            if config_path.exists():
                config_path.unlink(missing_ok=True)
            for path in sorted(
                created_scaffold_files, key=lambda item: len(item.parts), reverse=True
            ):
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)
        except OSError:
            pass


__all__ = [
    "ComponentAdmissionError",
    "run_component_toolchain_admission",
    "validate_component_candidate",
]
