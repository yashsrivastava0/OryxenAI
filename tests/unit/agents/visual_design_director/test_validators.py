"""Unit tests for Visual Design Director output validators (transport contract only)."""

from __future__ import annotations

from oryxenai.agents.visual_design_director.validators import validate_stage_output


def _route(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "route_id": "home",
        "path": "/",
        "purpose": "Home page",
        "publication_status": "approved",
    }
    base.update(overrides)
    return base


def _scene(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "scene_id": "hero_scene",
        "route_id": "home",
        "responsive_behavior": "stacks to a single column on mobile",
    }
    base.update(overrides)
    return base


def _page(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "route_id": "home",
        "path": "/",
        "scenes": [_scene()],
    }
    base.update(overrides)
    return base


def _asset(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "asset_id": "hero_visual",
        "importance": "optional",
    }
    base.update(overrides)
    return base


def _resource(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {"resource_id": "hero_asymmetric_text_dominant"}
    base.update(overrides)
    return base


def _establish_with_pages(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "mode": "VISUAL_LANGUAGE_AND_PAGES",
        "pages_included": True,
        "visual_language": {"creative_thesis": "x"},
        "shared_visual_systems": {"card_treatment": "flat"},
        "pages": [_page()],
    }
    base.update(overrides)
    return base


class TestValidateEstablishVisualLanguage:
    def test_valid_with_pages_included(self):
        outcome = validate_stage_output(
            _establish_with_pages(), "establish_visual_language", known_route_plan=[_route()]
        )
        assert outcome.is_valid
        assert outcome.errors == []

    def test_valid_without_pages(self):
        outcome = validate_stage_output(
            {
                "mode": "VISUAL_LANGUAGE_ONLY",
                "pages_included": False,
                "visual_language": {"creative_thesis": "x"},
                "shared_visual_systems": {"card_treatment": "flat"},
            },
            "establish_visual_language",
        )
        assert outcome.is_valid

    def test_premature_compiler_handoff_rejected(self):
        """Regression guard: only integrate_site_experience may populate
        compiler_handoff. A live model was observed writing premature
        compiler guidance here that went stale the moment a later stage
        actually produced the pages it described as not yet produced."""
        outcome = validate_stage_output(
            {
                **_establish_with_pages(),
                "compiler_handoff": {"route_authority": "do not compile route:home yet"},
            },
            "establish_visual_language",
        )
        assert not outcome.is_valid
        assert any("'compiler_handoff' must be empty" in error for error in outcome.errors)

    def test_mode_must_match_operation(self):
        outcome = validate_stage_output(
            {**_establish_with_pages(), "mode": "PAGES_READY"}, "establish_visual_language"
        )
        assert not outcome.is_valid
        assert any("'mode' must be one of" in error for error in outcome.errors)

    def test_pages_included_inconsistent_with_mode(self):
        outcome = validate_stage_output(
            {**_establish_with_pages(), "mode": "VISUAL_LANGUAGE_ONLY"},
            "establish_visual_language",
        )
        assert not outcome.is_valid
        assert any("inconsistent with pages_included" in error for error in outcome.errors)

    def test_empty_visual_language_rejected(self):
        outcome = validate_stage_output(
            {**_establish_with_pages(), "visual_language": {}}, "establish_visual_language"
        )
        assert not outcome.is_valid
        assert any("'visual_language' must not be empty" in error for error in outcome.errors)

    def test_empty_shared_visual_systems_rejected(self):
        outcome = validate_stage_output(
            {**_establish_with_pages(), "shared_visual_systems": {}}, "establish_visual_language"
        )
        assert not outcome.is_valid
        assert any("'shared_visual_systems' must not be empty" in error for error in outcome.errors)

    def test_empty_pages_allowed_when_pages_not_included(self):
        outcome = validate_stage_output(
            {
                "mode": "VISUAL_LANGUAGE_ONLY",
                "pages_included": False,
                "visual_language": {"creative_thesis": "x"},
                "shared_visual_systems": {"card_treatment": "flat"},
                "pages": [],
            },
            "establish_visual_language",
        )
        assert outcome.is_valid

    def test_empty_pages_rejected_when_pages_included(self):
        outcome = validate_stage_output(
            {**_establish_with_pages(), "pages": []}, "establish_visual_language"
        )
        assert not outcome.is_valid
        assert any("'pages' must not be empty" in error for error in outcome.errors)

    def test_asset_briefs_and_resource_candidates_never_required(self):
        """A legitimate text/diagram-only site can have zero real assets and
        zero catalogue resources — this is a celebrated outcome, not
        incompleteness (deliberate deviation from Content Architect, which
        requires page_content_packs and public_content_manifest together)."""
        outcome = validate_stage_output(
            {**_establish_with_pages(), "asset_briefs": [], "resource_candidates": []},
            "establish_visual_language",
        )
        assert outcome.is_valid


class TestValidateDirectPageExperience:
    def test_premature_compiler_handoff_rejected(self):
        payload = {
            "mode": "PAGES_READY",
            "pages_included": True,
            "pages": [_page()],
            "compiler_handoff": {"asset_boundary": "no assets approved"},
        }
        outcome = validate_stage_output(payload, "direct_page_experience")
        assert not outcome.is_valid
        assert any("'compiler_handoff' must be empty" in error for error in outcome.errors)

    def _valid_payload(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "mode": "PAGES_READY",
            "pages_included": True,
            "pages": [_page()],
        }
        base.update(overrides)
        return base

    def test_valid(self):
        outcome = validate_stage_output(
            self._valid_payload(), "direct_page_experience", known_route_plan=[_route()]
        )
        assert outcome.is_valid

    def test_empty_pages_rejected(self):
        outcome = validate_stage_output(self._valid_payload(pages=[]), "direct_page_experience")
        assert not outcome.is_valid
        assert any("'pages' must not be empty" in error for error in outcome.errors)

    def test_page_with_no_route_id_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(pages=[_page(route_id="")]), "direct_page_experience"
        )
        assert not outcome.is_valid
        assert any("has no route_id" in error for error in outcome.errors)

    def test_duplicate_page_route_id_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(pages=[_page(), _page()]), "direct_page_experience"
        )
        assert not outcome.is_valid
        assert any("Duplicate page route_id" in error for error in outcome.errors)

    def test_unknown_route_id_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(pages=[_page(route_id="ghost")]),
            "direct_page_experience",
            known_route_plan=[_route()],
        )
        assert not outcome.is_valid
        assert any("references unknown route_id" in error for error in outcome.errors)

    def test_blocked_route_id_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(pages=[_page(route_id="secret")]),
            "direct_page_experience",
            known_route_plan=[_route(route_id="secret", publication_status="blocked")],
        )
        assert not outcome.is_valid
        assert any("references blocked route_id" in error for error in outcome.errors)

    def test_missing_route_coverage_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(pages=[_page(route_id="home")]),
            "direct_page_experience",
            known_route_plan=[_route(route_id="home"), _route(route_id="about", path="/about")],
        )
        assert not outcome.is_valid
        assert any("about" in error and "no visual direction" in error for error in outcome.errors)

    def test_blocked_route_not_required_for_coverage(self):
        outcome = validate_stage_output(
            self._valid_payload(pages=[_page(route_id="home")]),
            "direct_page_experience",
            known_route_plan=[
                _route(route_id="home"),
                _route(route_id="secret", publication_status="blocked"),
            ],
        )
        assert outcome.is_valid

    def test_scene_missing_responsive_behavior_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(pages=[_page(scenes=[_scene(responsive_behavior="")])]),
            "direct_page_experience",
        )
        assert not outcome.is_valid
        assert any("has no responsive_behavior" in error for error in outcome.errors)

    def test_motion_without_reduced_motion_behavior_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(
                pages=[
                    _page(scenes=[_scene(motion_intent={"purpose": "draw attention to evidence"})])
                ]
            ),
            "direct_page_experience",
        )
        assert not outcome.is_valid
        assert any("no reduced_motion_behavior" in error for error in outcome.errors)

    def test_motion_with_reduced_motion_behavior_allowed(self):
        outcome = validate_stage_output(
            self._valid_payload(
                pages=[
                    _page(
                        scenes=[
                            _scene(
                                motion_intent={"purpose": "draw attention"},
                                reduced_motion_behavior="static, fully visible state",
                            )
                        ]
                    )
                ]
            ),
            "direct_page_experience",
        )
        assert outcome.is_valid

    def test_duplicate_scene_id_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(
                pages=[
                    _page(route_id="home", scenes=[_scene(scene_id="hero_scene")]),
                    _page(
                        route_id="about",
                        path="/about",
                        scenes=[_scene(scene_id="hero_scene", route_id="about")],
                    ),
                ]
            ),
            "direct_page_experience",
        )
        assert not outcome.is_valid
        assert any("Duplicate scene_id" in error for error in outcome.errors)

    def test_critical_asset_missing_source_status_and_fallback_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(
                asset_briefs=[_asset(importance="critical", source_status="", fallback_strategy="")]
            ),
            "direct_page_experience",
        )
        assert not outcome.is_valid
        assert any("no source_status" in error for error in outcome.errors)
        assert any("no fallback_strategy" in error for error in outcome.errors)

    def test_optional_asset_without_source_status_or_fallback_allowed(self):
        outcome = validate_stage_output(
            self._valid_payload(asset_briefs=[_asset(importance="optional")]),
            "direct_page_experience",
        )
        assert outcome.is_valid

    def test_critical_asset_with_source_status_and_fallback_allowed(self):
        outcome = validate_stage_output(
            self._valid_payload(
                asset_briefs=[
                    _asset(
                        importance="critical",
                        source_status="approved_existing",
                        fallback_strategy="typographic treatment if unavailable",
                    )
                ]
            ),
            "direct_page_experience",
        )
        assert outcome.is_valid

    def test_duplicate_asset_id_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(asset_briefs=[_asset(), _asset()]), "direct_page_experience"
        )
        assert not outcome.is_valid
        assert any("Duplicate asset_id" in error for error in outcome.errors)

    def test_unknown_resource_id_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(resource_candidates=[_resource(resource_id="not_in_shortlist")]),
            "direct_page_experience",
            known_resource_ids={"hero_asymmetric_text_dominant"},
        )
        assert not outcome.is_valid
        assert any("catalogue shortlist" in error for error in outcome.errors)

    def test_known_resource_id_allowed(self):
        outcome = validate_stage_output(
            self._valid_payload(resource_candidates=[_resource()]),
            "direct_page_experience",
            known_resource_ids={"hero_asymmetric_text_dominant"},
        )
        assert outcome.is_valid

    def test_scene_resource_reference_checked_against_known_set(self):
        outcome = validate_stage_output(
            self._valid_payload(
                pages=[_page(scenes=[_scene(resource_candidates=["not_in_shortlist"])])]
            ),
            "direct_page_experience",
            known_resource_ids={"hero_asymmetric_text_dominant"},
        )
        assert not outcome.is_valid
        assert any("catalogue shortlist" in error for error in outcome.errors)

    def test_duplicate_resource_id_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(resource_candidates=[_resource(), _resource()]),
            "direct_page_experience",
        )
        assert not outcome.is_valid
        assert any("Duplicate resource_id" in error for error in outcome.errors)


class TestValidateIntegrateSiteExperience:
    def _valid_payload(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "mode": "INTEGRATED",
            "pages_included": True,
            "pages": [_page()],
            "compiler_handoff": {"shared_systems": "typography, spacing"},
        }
        base.update(overrides)
        return base

    def test_valid(self):
        outcome = validate_stage_output(self._valid_payload(), "integrate_site_experience")
        assert outcome.is_valid

    def test_empty_compiler_handoff_rejected(self):
        outcome = validate_stage_output(
            self._valid_payload(compiler_handoff={}), "integrate_site_experience"
        )
        assert not outcome.is_valid
        assert any("'compiler_handoff' must not be empty" in error for error in outcome.errors)


class TestValidateEnvelopeShape:
    def test_non_dict_output_rejected(self):
        outcome = validate_stage_output([], "establish_visual_language")
        assert not outcome.is_valid
        assert "output is not a JSON object" in outcome.errors

    def test_unknown_operation_rejected(self):
        outcome = validate_stage_output({"mode": "X"}, "not_a_real_operation")
        assert not outcome.is_valid
        assert any("unknown operation" in error for error in outcome.errors)

    def test_list_fields_must_be_lists(self):
        outcome = validate_stage_output(
            {**_establish_with_pages(), "warnings": "not a list"}, "establish_visual_language"
        )
        assert not outcome.is_valid
        assert any("'warnings' must be a list" in error for error in outcome.errors)

    def test_memory_update_must_be_dict(self):
        outcome = validate_stage_output(
            {**_establish_with_pages(), "memory_update": "not a dict"},
            "establish_visual_language",
        )
        assert not outcome.is_valid
        assert any("'memory_update' must be a dict" in error for error in outcome.errors)

    def test_pages_included_must_be_boolean(self):
        outcome = validate_stage_output(
            {**_establish_with_pages(), "pages_included": "yes"}, "establish_visual_language"
        )
        assert not outcome.is_valid
        assert any("'pages_included' must be a boolean" in error for error in outcome.errors)
