from __future__ import annotations

import io

import pytest
from PIL import Image
from tests.unit.agents.code_generator.test_acquisition_validators import _request

from oryxenai.agents.code_generator.core.acquisition_validators import AcquisitionValidationError
from oryxenai.agents.code_generator.core.development_schemas import ResourceCandidate
from oryxenai.agents.code_generator.core.resource_adapters import (
    ComponentSourceAdapter,
    FontAdapter,
    IconAdapter,
    ImageAdapter,
    OfflineResourceProviderRegistry,
    StylePrimitiveAdapter,
)
from oryxenai.core.settings import Settings


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), (30, 60, 90)).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_offline_image_search_and_materialization_are_content_addressed(tmp_path) -> None:
    registry = OfflineResourceProviderRegistry()
    registry.register(
        ResourceCandidate(
            candidate_id="fixture-image",
            provider_key="fixture",
            provider_resource_id="fixture-image",
            category="image",
            title="Editorial fixture",
            tags=["editorial"],
            canonical_source="fixture://image",
            licence="Fixture License",
            attribution="Fixture",
            vendoring_policy="download and vendor",
        ),
        _png(),
    )
    settings = Settings()
    request = _request()
    adapter = ImageAdapter(registry)
    candidates = await adapter.search(request, settings=settings)
    materialized = await adapter.materialize(
        candidates[0], request, storage_root=tmp_path / "materials", settings=settings
    )
    assert materialized.local_path.endswith(".png")
    assert (tmp_path / "materials" / materialized.local_path).is_file()
    assert (tmp_path / "materials" / materialized.inspection["licence_path"]).is_file()


@pytest.mark.asyncio
async def test_offline_component_source_search_is_separate_from_build_preparation(tmp_path) -> None:
    registry = OfflineResourceProviderRegistry()
    registry.register(
        ResourceCandidate(
            candidate_id="fixture-component",
            provider_key="fixture",
            provider_resource_id="fixture-component",
            category="component_source",
            title="Card",
            canonical_source="fixture://component",
            licence="MIT",
            vendoring_policy="vendor source",
            dependency_metadata={"lucide-react": ["Heart"]},
        ),
        b"export function Card() { return null; }",
    )
    settings = Settings()
    request = _request(category="component_source")
    adapter = ComponentSourceAdapter(registry)
    candidates = await adapter.search(request, settings=settings)
    assert candidates[0].dependency_metadata == {"lucide-react": ["Heart"]}
    materialized = await adapter.materialize(
        candidates[0], request, storage_root=tmp_path / "materials", settings=settings
    )
    assert materialized.media_type == "text/plain"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adapter_type", "category", "payload", "media_type"),
    [
        (FontAdapter, "font", b"wOF2" + b"0" * 20, "font/woff2"),
        (
            IconAdapter,
            "icon",
            b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0" /></svg>',
            "image/svg+xml",
        ),
        (StylePrimitiveAdapter, "style_primitive", b".pattern { color: red; }", "text/plain"),
    ],
)
async def test_each_non_image_adapter_materializes_local_source(
    adapter_type, category, payload, media_type, tmp_path
) -> None:
    registry = OfflineResourceProviderRegistry()
    registry.register(
        ResourceCandidate(
            candidate_id=f"fixture-{category}",
            provider_key="fixture",
            provider_resource_id=f"fixture-{category}",
            category=category,
            title=f"{category} fixture",
            canonical_source=f"fixture://{category}",
            licence="MIT",
            attribution="Fixture",
            vendoring_policy="download and vendor",
        ),
        payload,
    )
    request = _request(category=category)
    settings = Settings()
    adapter = adapter_type(registry)
    candidates = await adapter.search(request, settings=settings)
    materialized = await adapter.materialize(
        candidates[0], request, storage_root=tmp_path / "materials", settings=settings
    )
    assert materialized.media_type == media_type


@pytest.mark.asyncio
async def test_component_path_and_remote_source_are_rejected(tmp_path) -> None:
    registry = OfflineResourceProviderRegistry()
    registry.register(
        ResourceCandidate(
            candidate_id="unsafe-component",
            provider_key="fixture",
            provider_resource_id="unsafe-component",
            category="component_source",
            title="Unsafe",
            canonical_source="fixture://unsafe",
            licence="MIT",
            vendoring_policy="vendor source",
            technical_metadata={"file_paths": ["../escape.tsx"]},
        ),
        b"import x from 'https://example.invalid/remote.js';",
    )
    candidate = (
        await ComponentSourceAdapter(registry).search(
            _request(category="component_source"), settings=Settings()
        )
    )[0]
    with pytest.raises(AcquisitionValidationError, match="unsafe"):
        await ComponentSourceAdapter(registry).materialize(
            candidate,
            _request(category="component_source"),
            storage_root=tmp_path / "materials",
            settings=Settings(),
        )
