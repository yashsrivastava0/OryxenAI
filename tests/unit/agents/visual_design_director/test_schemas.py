"""Unit tests for Visual Design Director domain schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from oryxenai.agents.visual_design_director.schemas import (
    AssetBrief,
    AssetImportance,
    AssetSourcePolicy,
    AssetSourceStatus,
    PagePublicationStatus,
    PageVisualDirection,
    ResourceCandidate,
    SceneDirection,
    VisualDesignDirectorIntake,
    VisualDesignDirectorOutput,
    VisualDesignDirectorPreferences,
    VisualDesignDirectorSourceRef,
    VisualDesignDirectorState,
    VisualDesignDirectorStatus,
    VisualPlanMode,
)


class TestVisualDesignDirectorIntake:
    def test_empty_intake(self):
        intake = VisualDesignDirectorIntake()
        assert intake.presentation_mode == ""
        assert intake.route_plan == []
        assert intake.visual_director_handoff == {}

    def test_does_not_duplicate_must_preserve_fields(self):
        """must_preserve/never_fabricate live inside visual_director_handoff
        (Content Architect's real handoff field) — not reinvented as
        separate top-level intake fields, avoiding two sources of truth."""
        assert "must_preserve" not in VisualDesignDirectorIntake.model_fields
        assert "must_not_fabricate" not in VisualDesignDirectorIntake.model_fields

    def test_accepts_any_input(self):
        intake = VisualDesignDirectorIntake(
            presentation_mode="single_page",
            visual_director_handoff={"must_preserve": ["x"]},
        )
        assert intake.visual_director_handoff["must_preserve"] == ["x"]

    def test_unknown_fields_accepted(self):
        intake = VisualDesignDirectorIntake(presentation_mode="hybrid", something_else={"a": 1})
        assert intake.something_else == {"a": 1}


class TestVisualDesignDirectorPreferences:
    def test_defaults_empty(self):
        prefs = VisualDesignDirectorPreferences()
        assert prefs.visual_tone == ""
        assert prefs.motion_preference == ""

    def test_unknown_fields_accepted(self):
        prefs = VisualDesignDirectorPreferences(visual_tone="minimal", extra_pref="x")
        assert prefs.extra_pref == "x"


class TestSceneDirection:
    def test_minimal_scene(self):
        scene = SceneDirection(scene_id="hero_scene", route_id="home")
        assert scene.content_refs == []
        assert scene.motion_intent == {}
        assert scene.responsive_behavior == ""

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            SceneDirection(scene_id="s1", route_id="home", unknown="bad")


class TestAssetBrief:
    def test_defaults(self):
        asset = AssetBrief(asset_id="hero_visual")
        assert asset.importance == AssetImportance.OPTIONAL
        assert asset.source_status == AssetSourceStatus.UNAVAILABLE
        assert asset.source_policy == AssetSourcePolicy.CURATED_LOCAL

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            AssetBrief(asset_id="a1", unknown="bad")

    def test_importance_source_status_and_source_policy_are_independent(self):
        asset = AssetBrief(
            asset_id="a1",
            importance=AssetImportance.CRITICAL,
            source_status=AssetSourceStatus.NEEDS_ACQUISITION,
            source_policy=AssetSourcePolicy.OPTIONAL_EXTERNAL_ACQUISITION,
            fallback_strategy="fall back to a typographic treatment",
        )
        assert asset.importance == AssetImportance.CRITICAL
        assert asset.source_status == AssetSourceStatus.NEEDS_ACQUISITION
        assert asset.source_policy == AssetSourcePolicy.OPTIONAL_EXTERNAL_ACQUISITION

    def test_invalid_importance_rejected(self):
        with pytest.raises(PydanticValidationError):
            AssetBrief(asset_id="a1", importance="urgent")

    def test_semantic_search_intent_fields_default_empty(self):
        asset = AssetBrief(asset_id="a1")
        assert asset.subject == ""
        assert asset.mood == ""
        assert asset.aspect_ratio_need == ""
        assert asset.color_relationship == ""
        assert asset.negative_concepts == []

    def test_semantic_search_intent_fields_accept_values(self):
        asset = AssetBrief(
            asset_id="a1",
            subject="a durable job queue dashboard, abstract",
            mood="calm, technical",
            aspect_ratio_need="wide",
            color_relationship="neutral, complements a dark surface",
            negative_concepts=["real screenshots", "stock office photos"],
        )
        assert asset.subject == "a durable job queue dashboard, abstract"
        assert asset.negative_concepts == ["real screenshots", "stock office photos"]


class TestResourceCandidate:
    def test_minimal(self):
        resource = ResourceCandidate(resource_id="hero_asymmetric_text_dominant")
        assert resource.why_it_matches == ""
        assert resource.confidence == ""
        assert resource.category == ""
        assert resource.resource_library_version == ""
        assert resource.lookup_status == ""

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            ResourceCandidate(resource_id="r1", unknown="bad")

    def test_provenance_fields_accept_values(self):
        resource = ResourceCandidate(
            resource_id="diagram_process_flow",
            category="diagram_primitive",
            resource_library_version="65c4f40e5084",
            lookup_status="verified",
        )
        assert resource.category == "diagram_primitive"
        assert resource.lookup_status == "verified"


class TestPageVisualDirection:
    def test_minimal_page(self):
        page = PageVisualDirection(route_id="home", path="/")
        assert page.scenes == []
        assert page.asset_briefs == []
        assert page.resource_candidates == []

    def test_publication_status_and_compilable_default(self):
        page = PageVisualDirection(route_id="home", path="/")
        assert page.publication_status == PagePublicationStatus.APPROVED
        assert page.compilable is True

    def test_pending_publication_status(self):
        page = PageVisualDirection(route_id="home", publication_status="pending", compilable=False)
        assert page.publication_status == PagePublicationStatus.PENDING
        assert page.compilable is False

    def test_scenes_and_ids_are_separate(self):
        page = PageVisualDirection(
            route_id="home",
            scenes=[SceneDirection(scene_id="hero_scene", route_id="home")],
            asset_briefs=["hero_visual"],
            resource_candidates=["hero_asymmetric_text_dominant"],
        )
        assert page.scenes[0].scene_id == "hero_scene"
        assert page.asset_briefs == ["hero_visual"]
        assert page.resource_candidates == ["hero_asymmetric_text_dominant"]

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            PageVisualDirection(route_id="home", unknown="bad")


class TestVisualPlanMode:
    def test_four_modes_round_trip(self):
        assert VisualPlanMode.VISUAL_LANGUAGE_ONLY.value == "VISUAL_LANGUAGE_ONLY"
        assert VisualPlanMode.VISUAL_LANGUAGE_AND_PAGES.value == "VISUAL_LANGUAGE_AND_PAGES"
        assert VisualPlanMode.PAGES_READY.value == "PAGES_READY"
        assert VisualPlanMode.INTEGRATED.value == "INTEGRATED"


class TestAssetImportance:
    def test_three_levels(self):
        assert {m.value for m in AssetImportance} == {"critical", "important", "optional"}


class TestVisualDesignDirectorOutput:
    def test_minimal_output(self):
        output = VisualDesignDirectorOutput(mode=VisualPlanMode.VISUAL_LANGUAGE_ONLY)
        assert output.pages_included is False
        assert output.pages == []
        assert output.asset_briefs == []
        assert output.resource_candidates == []

    def test_mode_required(self):
        with pytest.raises(PydanticValidationError):
            VisualDesignDirectorOutput()

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            VisualDesignDirectorOutput(mode=VisualPlanMode.VISUAL_LANGUAGE_ONLY, unknown="bad")

    def test_full_output_shape(self):
        output = VisualDesignDirectorOutput(
            mode=VisualPlanMode.VISUAL_LANGUAGE_AND_PAGES,
            pages_included=True,
            visual_language={"creative_thesis": "x"},
            pages=[
                PageVisualDirection(
                    route_id="home",
                    scenes=[
                        SceneDirection(
                            scene_id="hero_scene",
                            route_id="home",
                            responsive_behavior="stacks on mobile",
                        )
                    ],
                )
            ],
            asset_briefs=[AssetBrief(asset_id="a1")],
            resource_candidates=[ResourceCandidate(resource_id="r1")],
        )
        assert output.pages[0].route_id == "home"
        assert output.pages[0].scenes[0].scene_id == "hero_scene"
        assert output.asset_briefs[0].asset_id == "a1"
        assert output.resource_candidates[0].resource_id == "r1"


class TestVisualDesignDirectorState:
    def test_default_state(self):
        state = VisualDesignDirectorState()
        assert state.status == VisualDesignDirectorStatus.NOT_STARTED
        assert state.max_attempts == 3
        assert state.approved is None
        assert state.pages == []
        assert state.asset_briefs == []

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            VisualDesignDirectorState(status=VisualDesignDirectorStatus.NOT_STARTED, unknown="bad")

    def test_round_trips_through_json(self):
        state = VisualDesignDirectorState(
            status=VisualDesignDirectorStatus.DESIGN_REVIEW,
            pages=[PageVisualDirection(route_id="home", path="/")],
            asset_briefs=[AssetBrief(asset_id="a1")],
            resource_candidates=[ResourceCandidate(resource_id="r1")],
        )
        dumped = state.model_dump(mode="json")
        restored = VisualDesignDirectorState.model_validate(dumped)
        assert restored == state


class TestVisualDesignDirectorSourceRef:
    def test_route_publication_hash_defaults_empty(self):
        ref = VisualDesignDirectorSourceRef()
        assert ref.route_publication_hash == ""

    def test_route_publication_hash_accepts_value(self):
        ref = VisualDesignDirectorSourceRef(route_publication_hash="abc123")
        assert ref.route_publication_hash == "abc123"
