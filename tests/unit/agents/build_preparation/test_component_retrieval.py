from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from oryxenai.agents.shared.component_retrieval import (
    ComponentCandidate,
    McpComponentProvider,
    build_component_retrieval_service,
)
from oryxenai.agents.shared.retrieval_policy import plan_component_retrieval
from oryxenai.core.settings import Settings


def test_component_retrieval_policy_is_required_first_and_route_aware() -> None:
    plan = plan_component_retrieval(
        [
            SimpleNamespace(
                need_id="optional-home",
                required_for_handoff=False,
                importance="optional",
                route_ids=["home"],
                scene_ids=["hero"],
            ),
            SimpleNamespace(
                need_id="required-projects",
                required_for_handoff=True,
                importance="important",
                route_ids=["projects"],
                scene_ids=["grid"],
            ),
            SimpleNamespace(
                need_id="optional-shared",
                required_for_handoff=False,
                importance="supporting",
                route_ids=["home", "projects", "about"],
                scene_ids=["hero", "grid", "bio"],
            ),
        ],
        maximum=2,
    )

    assert plan.selected_ids == ("required-projects", "optional-shared")
    assert plan.deferred_optional_ids == ("optional-home",)
    assert plan.required_over_maximum is False


@pytest.mark.asyncio
async def test_registry_discovery_is_metadata_only_until_selected_fetch() -> None:
    settings = Settings()
    settings.resource_providers.registry_order = ["shadcn"]
    settings.resource_providers.shadcn_catalog_url = "https://registry.test/catalog.json"
    settings.resource_providers.shadcn_item_url_template = "https://registry.test/{name}.json"
    requests: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/catalog.json":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "name": "card",
                            "title": "Editorial card",
                            "description": "A card for editorial workspace content.",
                            "tags": ["editorial", "content"],
                        }
                    ]
                },
                request=request,
            )
        if request.url.path == "/card.json":
            return httpx.Response(
                200,
                json={
                    "files": [{"path": "card.tsx", "content": "export const Card = () => null;"}],
                    "dependencies": ["react"],
                    "registryDependencies": ["button"],
                    "version": "1.2.3",
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "files": [{"path": "button.tsx", "content": "export const Button = () => null;"}],
                "dependencies": ["@radix-ui/react-slot"],
            },
            request=request,
        )

    service = build_component_retrieval_service(settings)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        discovered = await service.discover(
            "editorial content card",
            allowed_providers=["shadcn"],
            client=client,
            settings=settings,
            limit=5,
        )
        assert discovered[0].tags == ("editorial", "content")
        assert requests == ["/catalog.json"]

        fetched = await service.fetch(discovered[0], client=client, settings=settings)

    assert set(fetched.source_files) == {"card.tsx", "button.tsx"}
    assert fetched.dependencies == ("react", "@radix-ui/react-slot")
    assert fetched.source_version == "1.2.3"
    assert requests == ["/catalog.json", "/card.json", "/button.json"]


@pytest.mark.asyncio
async def test_mcp_adapter_fetches_source_and_registry_dependencies_without_http() -> None:
    async def caller(tool_name: str, arguments: dict[str, object]) -> object:
        if tool_name == "searchRegistryItems":
            return {"items": [{"name": "card", "title": "Card", "url": "mcp://card"}]}
        if arguments["name"] == "card":
            return {
                "files": [{"path": "card.tsx", "content": "export const Card = () => null;"}],
                "registryDependencies": ["button"],
            }
        return {
            "source": "export const Button = () => null;",
            "dependencies": ["react"],
        }

    provider = McpComponentProvider("magicui", caller)
    candidate = ComponentCandidate(
        provider="magicui",
        name="card",
        title="Card",
        description="",
        tags=(),
        item_url="mcp://card",
        license="MIT",
        license_reference="https://example.test/LICENSE",
    )
    async with httpx.AsyncClient() as client:
        discovered = await provider.discover("card", client=client, settings=Settings(), limit=5)
        fetched = await provider.fetch(candidate, client=client, settings=Settings())

    assert discovered[0].name == "card"
    assert set(fetched.source_files) == {"card.tsx", "button.tsx"}
    assert fetched.dependencies == ("react",)


@pytest.mark.asyncio
async def test_registry_rate_limit_diagnostics_are_preserved_while_order_continues() -> None:
    settings = Settings()
    settings.resource_providers.registry_order = ["shadcn", "magicui"]
    settings.resource_providers.shadcn_catalog_url = "https://registry.test/shadcn.json"
    settings.resource_providers.shadcn_item_url_template = (
        "https://registry.test/shadcn-{name}.json"
    )
    settings.resource_providers.magicui_catalog_url = "https://registry.test/magic.json"
    settings.resource_providers.magicui_item_url_template = (
        "https://registry.test/magic-{name}.json"
    )
    diagnostics: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/shadcn.json":
            return httpx.Response(429, headers={"Retry-After": "2"}, request=request)
        if request.url.path == "/magic.json":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "name": "accordion",
                            "title": "Accordion",
                            "description": "Disclosure groups",
                            "tags": ["accordion", "disclosure"],
                        }
                    ]
                },
                request=request,
            )
        return httpx.Response(200, json={"files": []}, request=request)

    service = build_component_retrieval_service(settings)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        candidates = await service.discover(
            "accordion disclosure",
            allowed_providers=["shadcn", "magicui"],
            client=client,
            settings=settings,
            diagnostics=diagnostics,
        )

    assert candidates[0].name == "accordion"
    rate_limited = next(item for item in diagnostics if item["provider"] == "shadcn")
    assert rate_limited["http_status"] == 429
    assert rate_limited["rate_limit_event"] is True
    assert rate_limited["error_code"] == "RATE_LIMITED"
