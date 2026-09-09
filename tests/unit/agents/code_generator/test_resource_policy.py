from __future__ import annotations

from oryxenai.agents.code_generator.core.resource_policy import (
    is_component_category,
    is_image_category,
    normalize_resource_category,
)


def test_build_preparation_categories_keep_components_out_of_image_flow() -> None:
    assert normalize_resource_category("editorial_photo") == "image"
    assert normalize_resource_category("abstract systems illustration") == "illustration"
    assert is_image_category("abstract systems illustration")
    assert normalize_resource_category("visual_component") == "component_source"
    assert is_component_category("visual_component")
    assert not is_image_category("visual_component")


def test_unknown_category_fails_closed_to_stable_identifier() -> None:
    assert normalize_resource_category("future visual artifact") == "future_visual_artifact"
