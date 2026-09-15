{
  "meta": {
    "stages_run": [
      "establish_visual_language"
    ],
    "media_basis": "No approved imagery, screenshots, diagrams, or project media are available.",
    "route_count": 1,
    "model_profile": "experiential_luna",
    "prompt_version": "visual_design_director.establish_visual_language.v4",
    "final_operation": "establish_visual_language",
    "resource_handoff": {
      "promoted_resource_ids": [],
      "top_level_registry_complete": true
    },
    "visual_direction_status": "visual_language_established_and_home_page_direction_complete"
  },
  "pages": [
    {
      "path": "/",
      "scenes": [
        {
          "route_id": "home",
          "scene_id": "home-introduction",
          "layer_stack": "Base surface, quiet abstract line or node motif, identity and headline, supporting value proposition, then action links.",
          "content_refs": [
            "home:hero",
            "home:positioning"
          ],
          "layout_intent": "Use a text-dominant asymmetric opening: identity and headline occupy the principal reading area while a restrained abstract lifecycle cue balances the composition without competing with the claim.",
          "motion_intent": {
            "type": "entrance_and_orientation",
            "trigger": "initial render or first meaningful visibility",
            "behavior": "Reveal the identity and headline as a single readable group, with the abstract lifecycle cue settling into place afterward without delaying copy.",
            "duration_character": "brief and calm",
            "essential_information_in_motion": false
          },
          "transition_in": "Enter directly from the page start with no blocking preloader.",
          "viewport_role": "Opening orientation scene with text as the dominant visual element.",
          "narrative_goal": "Establish Maya’s identity, seniority, and dependable endpoint engineering proposition.",
          "transition_out": "Whitespace and a subtle divider lead into positioning and selected work.",
          "performance_risk": "Low if the cue uses lightweight custom vector or CSS-like treatment; avoid raster artwork and blocking animation.",
          "background_intent": "Calm neutral foundation with a barely visible technical structure; no stock imagery or implied interface.",
          "asset_requirements": [],
          "interaction_states": {
            "touch": "Actions remain fully usable without hover.",
            "primary_action": "Clear emphasis leading to #home:selected-work; focus remains visible.",
            "secondary_action": "Quieter but distinct link leading to #home:capabilities."
          },
          "acceptance_criteria": [
            "The hero clearly establishes Maya Bennett and Senior End User Computing Specialist.",
            "The focus on secure, manageable, dependable employee technology is visually prominent.",
            "No image, screenshot, logo, metric, or unapproved contact information is implied.",
            "The scene remains readable on mobile and touch-only devices."
          ],
          "resource_candidates": [
            "hero_asymmetric_text_dominant"
          ],
          "responsive_behavior": "Wide desktop and laptop preserve the asymmetric relationship; tablet reduces the offset and keeps copy dominant; mobile stacks the cue after or beside the introductory copy only if it remains legible; touch-only devices use static emphasis and no hover dependency.",
          "accessibility_intent": "Preserve semantic heading order, keep the headline and value proposition in the reading order, label any abstract cue as decorative or illustrative, and maintain visible keyboard focus.",
          "relative_proportions": "Let text occupy roughly two-thirds of the available wide composition and the abstract cue roughly one-third; collapse to a single readable column on narrow screens.",
          "alignment_relationships": "Align the hero headline, value proposition, and first positioning heading to a shared reading rail. Keep the abstract cue offset from the copy and subordinate in contrast.",
          "reduced_motion_behavior": "Render the complete hero immediately with the abstract cue in its final position; do not animate text or require motion to understand the proposition.",
          "failure_safe_static_state": "Identity, title, value proposition, and both approved anchor actions remain complete and understandable with the abstract cue removed."
        },
        {
          "route_id": "home",
          "scene_id": "home-selected-work",
          "layer_stack": "Structured surface, section heading and intro, project groupings, conceptual lifecycle relationship, compact technology treatments.",
          "content_refs": [
            "home:selected-work"
          ],
          "layout_intent": "Present three related initiatives as an organized sequence or grouped set, with project titles and summaries leading and technology lists treated as supporting metadata.",
          "motion_intent": {
            "type": "progressive_lifecycle_emphasis",
            "trigger": "scene visibility",
            "behavior": "Allow the conceptual endpoint lifecycle to reveal in a short sequence as the scene becomes visible, while project summaries remain immediately available.",
            "duration_character": "brief, sequential, and non-essential",
            "essential_information_in_motion": false
          },
          "transition_in": "The opening action lands with the selected-work heading clearly visible.",
          "viewport_role": "Primary evidence scene with enough visual weight to reward scanning and reading.",
          "narrative_goal": "Make the three approved work themes the page’s clearest professional evidence without overstating outcomes.",
          "transition_out": "A quiet structural divider shifts from project themes into capabilities.",
          "performance_risk": "Moderate if the diagram becomes overly elaborate; keep node count low, use lightweight shapes, and avoid large external media.",
          "background_intent": "A slightly emphasized surface distinguishes selected work from the opening while remaining quiet enough for long technical labels.",
          "asset_requirements": [],
          "interaction_states": {
            "touch": "Press states may emphasize a group but cannot hide or require content.",
            "lifecycle": "Stages have readable labels and a static complete state after any reveal.",
            "project_group": "Hover or focus may modestly raise the active project boundary; summaries and technology labels remain available by default."
          },
          "acceptance_criteria": [
            "All three approved work themes are present and visually distinct.",
            "The diagram remains clearly conceptual and does not resemble a real internal document.",
            "Technology lists support rather than overpower project summaries.",
            "No unsupported metrics, client identities, screenshots, or outcomes appear."
          ],
          "resource_candidates": [
            "diagram_process_flow"
          ],
          "responsive_behavior": "Wide desktop may arrange projects across a broad field with the lifecycle relationship alongside or between them. Laptop and tablet keep summaries comfortable and reduce the number of simultaneous columns if needed. Mobile uses a vertical sequence and a simplified single-column lifecycle; touch-only behavior never depends on hover.",
          "accessibility_intent": "Treat the lifecycle as an illustrative conceptual diagram with a text-equivalent sequence. Keep each project title and summary in normal reading order and do not encode distinctions by color alone.",
          "relative_proportions": "Give summaries most of each project’s visual area; keep technology labels compact and secondary. On mobile, prioritize titles and one-sentence summaries before technologies.",
          "alignment_relationships": "Keep project titles and summaries aligned to a common reading rail while allowing a lifecycle marker or conceptual flow to connect the groups.",
          "reduced_motion_behavior": "Show the complete lifecycle and all project groups in their final static positions with no staged reveal.",
          "failure_safe_static_state": "Three project titles, summaries, and their technologies remain fully readable even if the lifecycle treatment is unavailable."
        },
        {
          "route_id": "home",
          "scene_id": "home-capabilities",
          "layer_stack": "Moderate surface, capability heading, four labeled groups, compact item lists, optional conceptual relationship markers.",
          "content_refs": [
            "home:capabilities"
          ],
          "layout_intent": "Use four clearly labeled capability groups with strong grouping and restrained separators. Let the relationship between endpoint platforms, security, automation, and service operations echo the lifecycle motif.",
          "motion_intent": {
            "type": "orientation_only",
            "trigger": "scene visibility",
            "behavior": "If used, introduce group markers with a restrained visibility transition; item text must not depend on sequential animation.",
            "duration_character": "minimal",
            "essential_information_in_motion": false
          },
          "transition_in": "Selected-work structure relaxes into broader capability groupings.",
          "viewport_role": "Structured scanning scene between selected work and experience.",
          "narrative_goal": "Explain Maya’s technical breadth as connected operating capabilities rather than an exhaustive resume inventory.",
          "transition_out": "A simple divider returns the page to the chronological experience narrative.",
          "performance_risk": "Low, provided the visual relationship remains lightweight and avoids an animated network of many nodes.",
          "background_intent": "Return toward the base surface with subtle tonal grouping, avoiding a dense dashboard appearance.",
          "asset_requirements": [],
          "interaction_states": {
            "touch": "No hover-only expansion; any condensation control must be explicit and optional.",
            "keyboard": "Focus order follows the group order and never traps the visitor.",
            "capability_group": "Groups may receive a modest focus or hover boundary, but all labels and approved items remain visible."
          },
          "acceptance_criteria": [
            "The scene communicates breadth without reproducing an exhaustive resume wall.",
            "The four approved capability categories remain identifiable.",
            "The visual relationship does not imply an unverified architecture or production topology.",
            "Mobile condensation preserves the most relevant capability information."
          ],
          "resource_candidates": [
            "diagram_abstract_topology"
          ],
          "responsive_behavior": "Wide desktop can use a balanced multi-group arrangement; laptop keeps groups readable without forcing long rows; tablet uses fewer columns or a staggered editorial arrangement; mobile stacks groups and shortens lists according to the approved condensation; touch-only devices keep every group inspectable without hover.",
          "accessibility_intent": "Use clear group headings, semantic lists, readable item contrast, and text alternatives if topology markers are included. Do not imply proficiency levels or outcomes through visual scale.",
          "relative_proportions": "Give labels and short introductory framing more emphasis than individual technology names. On mobile, show group labels first and reduce each group to the most relevant items as approved.",
          "alignment_relationships": "Align group labels to a shared grid and keep item lists visually subordinate. Use a connecting rule or marker system only when it clarifies relationships.",
          "reduced_motion_behavior": "Render all group labels and approved visible items immediately, with no animated dependency.",
          "failure_safe_static_state": "The four capability groups and their labels remain understandable as ordinary grouped lists."
        },
        {
          "route_id": "home",
          "scene_id": "home-experience-close",
          "layer_stack": "Quiet base surface, experience heading, current role emphasis, condensed earlier roles, optional credential reserve, optional connection prompt.",
          "content_refs": [
            "home:experience",
            "home:credentials",
            "home:connect"
          ],
          "layout_intent": "Use an editorial timeline-like progression for the three approved experience entries, then place optional credentials and connection content as quiet supporting blocks that can disappear when unresolved.",
          "motion_intent": {
            "type": "soft_completion_transition",
            "trigger": "scene visibility",
            "behavior": "Use only a subtle arrival emphasis for the current role or closing heading; no timeline movement is required.",
            "duration_character": "brief and understated",
            "essential_information_in_motion": false
          },
          "transition_in": "Capabilities resolve into chronological experience through whitespace rather than a dramatic effect.",
          "viewport_role": "Closing editorial scene with lower visual intensity and clear completion.",
          "narrative_goal": "Provide career progression and a measured closing invitation while keeping unresolved credentials and contact details secondary.",
          "transition_out": "End with a quiet page boundary; no invented next route or external destination.",
          "performance_risk": "Low; use text and lightweight separators rather than an animated timeline or media background.",
          "background_intent": "The page settles into its calmest surface here, signaling completion rather than another evidence-heavy section.",
          "asset_requirements": [],
          "interaction_states": {
            "touch": "All available anchors and actions remain directly operable.",
            "connection": "If no approved channel exists, omit the actionable connection treatment and retain only approved low-pressure wording if appropriate.",
            "experience": "Entries remain fully readable; focus may emphasize the current role without changing content."
          },
          "acceptance_criteria": [
            "Experience communicates progression without naming unverified employers.",
            "Current role receives the strongest emphasis.",
            "Credentials remain clearly optional and are not presented as verified.",
            "No private contact details, location, external URLs, or fabricated outcomes appear."
          ],
          "resource_candidates": [],
          "responsive_behavior": "Wide desktop may place the current role beside a compact progression line; laptop and tablet keep a single clear chronology; mobile stacks entries and condenses earlier roles to title, period, and one sentence. Optional credentials and connection content may be omitted on every device until verified. Touch-only use remains fully static and direct.",
          "accessibility_intent": "Use semantic headings and ordered experience structure, keep period and role association clear, and ensure optional content does not appear as verified when it is still pending.",
          "relative_proportions": "Give the current role the most space, earlier roles less, and optional sections the least. Preserve a clear closing action only when an approved channel exists.",
          "alignment_relationships": "Align role, period, and description consistently. Keep the current role visually primary and earlier roles progressively more compact as approved.",
          "reduced_motion_behavior": "Show the complete experience hierarchy immediately with no timeline animation or delayed closing action.",
          "failure_safe_static_state": "The three approved experience entries remain clear, with the current role visibly primary and no dependency on credentials or contact details."
        }
      ],
      "purpose": "Present Maya’s professional positioning, selected endpoint work, technical capabilities, experience, and a safe professional connection prompt.",
      "route_id": "home",
      "compilable": true,
      "storyboard": "Open with identity and value proposition; move into the operating philosophy; make selected work the strongest evidence area; explain capability relationships through grouped content and a conceptual lifecycle; close with experience and optional secondary sections.",
      "asset_briefs": [],
      "closing_action": "Invite review of selected work and, only when an approved channel exists, a low-pressure professional connection. Keep the connection section optional until that channel is cleared.",
      "section_rhythm": "Spacious hero, concise positioning, focused selected-work grouping, a more structured capability zone, then a quieter experience close. Credentials and connection should remain visually subordinate and may be omitted when their content is unavailable.",
      "first_impression": "A text-led, composed introduction establishes Maya’s name and senior title immediately, with a small abstract lifecycle cue providing technical character without pretending to be project evidence.",
      "primary_emphasis": "Maya’s identity, endpoint engineering value proposition, and selected work themes.",
      "visitor_takeaway": "Maya is a senior EUC specialist who connects endpoint engineering, automation, security, and service operations to dependable employee technology.",
      "publication_status": "approved",
      "responsive_summary": "On wide desktop, allow the hero to use an asymmetric text-led composition and give selected work a broad, organized field. On laptop, keep the reading column dominant and reduce decorative offsets. On tablet, bring the lifecycle visual closer to the related copy and preserve grouped project summaries. On mobile, stack content in narrative order, keep the headline and primary action, condense technology lists and earlier experience, and omit optional credentials or connection content when unresolved. On touch-only devices, expose every interactive state through press or static styling rather than hover.",
      "secondary_emphasis": "Technical breadth, endpoint lifecycle thinking, and progression across EUC responsibilities.",
      "acceptance_criteria": [
        "The single approved route is represented verbatim as route_id home and path /.",
        "The page remains a coherent single-page professional portfolio rather than a collection of thin case studies.",
        "Visual emphasis follows the approved content hierarchy.",
        "All conceptual visuals are clearly abstract and never presented as evidence.",
        "Responsive behavior covers wide desktop, laptop, tablet, mobile, and touch-only use."
      ],
      "navigation_behavior": "Top navigation follows the approved four anchors. Opening actions move to selected work and capabilities. Use smooth movement only when permitted, with destination headings and immediate access to content.",
      "resource_candidates": [
        "hero_asymmetric_text_dominant",
        "diagram_process_flow",
        "diagram_abstract_topology"
      ],
      "background_evolution": "Use a calm base at the opening, a slightly more structured surface for selected work, a subtle diagram-friendly transition around capabilities, and a quiet editorial surface for experience and optional closing content.",
      "main_evidence_moment": "The three approved selected-work themes presented as concise professional initiatives with technology relationships, without metrics, screenshots, employer names, or fabricated outcomes.",
      "main_interaction_moment": "A conceptual endpoint lifecycle that connects enrollment, configuration, application delivery, compliance, remediation, and support; it is explanatory rather than evidence of a real internal system.",
      "relationship_to_next_route": "There is no next route; internal anchors provide the page’s primary navigation."
    }
  ],
  "warnings": [
    "No approved media is available, so the direction intentionally relies on typography, surfaces, and conceptual diagrams rather than editorial imagery.",
    "The capabilities and experience content can become dense on narrow screens; mobile condensation and omission of optional sections should be enforced.",
    "The abstract topology resource is optional and should be omitted if it creates dashboard-like density or implies a real internal architecture.",
    "The connection prompt must remain non-actionable or be omitted until an approved professional channel is available."
  ],
  "conflicts": [],
  "stages_run": [
    "establish_visual_language"
  ],
  "source_refs": {
    "route_ids_covered": [
      "home"
    ],
    "content_architect_content_hash": "53569552e14d53ad342058c9b7e9b8894d448ee8de7282e7b358fbe4fd4a7f52",
    "content_architect_session_revision": 14
  },
  "asset_briefs": [],
  "user_summary": "The page uses a calm, technical, human-centered visual language: typography leads, a restrained neutral surface supports focused reading, and one measured accent helps visitors follow the endpoint lifecycle from provisioning through support. Selected work receives the strongest visual emphasis without pretending to show evidence that has not been supplied. The signature moment is a conceptual lifecycle flow that progressively reveals relationships between management, security, automation, and service delivery. The complete visual direction is ready for review.",
  "memory_update": {
    "media_status": "no_approved_media",
    "pages_included": true,
    "single_route_completed": "home",
    "visual_direction_status": "visual_language_established_and_pages_ready",
    "route_topology_preserved": true
  },
  "motion_system": {
    "global_character": "Progressive, brief, and informative. Motion should establish the page's lifecycle metaphor while leaving all content available in the static layout.",
    "signature_moments": [
      {
        "name": "endpoint_lifecycle_reveal",
        "purpose": "Introduce the conceptual relationship between provisioning, configuration, security, remediation, and support as the visitor reaches the selected-work or positioning transition.",
        "behavior": "Lifecycle stages appear in reading order with subtle line or state emphasis; the complete relationship remains visible after the reveal.",
        "reduced_motion_behavior": "Show the entire labeled lifecycle immediately with no movement, using static emphasis and clear reading order.",
        "failure_safe_static_state": "A fully visible labeled conceptual lifecycle remains understandable without animation."
      },
      {
        "name": "section_orientation_shift",
        "purpose": "Provide a quiet sense of progression as the page moves between narrative phases.",
        "behavior": "Use a short opacity or positional transition for section markers and headings only when they enter view; never delay essential copy.",
        "reduced_motion_behavior": "Render headings, markers, and content in their final positions without transition.",
        "failure_safe_static_state": "All headings and section relationships are present in normal document flow."
      }
    ],
    "global_reduced_motion": "Disable nonessential movement, staged reveals, parallax, and animated emphasis when reduced motion is requested; preserve immediate content, anchor navigation, and static lifecycle relationships."
  },
  "must_preserve": [
    "Maya Bennett",
    "Senior End User Computing Specialist",
    "The focus on secure, manageable, dependable employee technology",
    "The distinction between endpoint management, automation, security, and service delivery",
    "Neutral wording for the three selected work themes"
  ],
  "resource_policy": {
    "image_maximum": 6,
    "component_maximum": 6,
    "image_target_count": 5,
    "component_target_count": 4,
    "require_real_local_material": true
  },
  "visual_language": {
    "anti_patterns": [
      "Fabricated dashboards, screenshots, metrics, testimonials, logos, awards, or employer evidence",
      "Resume-wall density or exhaustive ungrouped technology inventories",
      "Generic cybersecurity imagery or stock device photography used as proof",
      "Glassmorphism, dramatic gradients, neon terminal styling, or excessive shadows",
      "Persistent animation, scroll hijacking, hover-only information, and motion that obscures content",
      "A repeated identical card grid for every section",
      "Visual claims that imply verified outcomes, scale, or organizational ownership not present in the approved content"
    ],
    "color_behavior": "Use a quiet neutral foundation with strong text contrast and one controlled accent for actions, active navigation, lifecycle emphasis, and small status cues. Keep the accent sparse so it signals direction rather than decoration. Avoid implying security severity or measured performance through color alone.",
    "spacing_rhythm": "Use generous separation between narrative phases, moderate spacing inside project and capability groups, and compact spacing only for related technology labels. The page should breathe around claims and tighten around taxonomies.",
    "creative_thesis": "Treat reliable employee technology as an engineered service rather than an abstract technical specialty. The page should feel like a clear operating model: establish the person and promise, move through selected work, reveal the capability relationships behind it, and finish with experience and a low-pressure next action.",
    "grid_philosophy": "Use a flexible editorial grid with a strong reading column and occasional asymmetric supporting space. Align section headings, project summaries, capability groups, and lifecycle markers to shared rails so the page feels engineered without becoming a rigid dashboard.",
    "image_treatment": "No image treatment is required because no approved media exists. If later-approved media becomes available, treat it as documentary evidence only when its provenance and publication permission are confirmed; otherwise retain the abstract lifecycle direction.",
    "visual_metaphor": "A dependable endpoint lifecycle: provision, configure, secure, remediate, and support. This motif can appear as restrained lines, state markers, and conceptual connections, never as a fabricated production diagram or screenshot.",
    "motion_character": "Measured and purposeful. Motion should clarify progression or relationship, not create a constantly active interface. Use one signature lifecycle reveal and restrained entrance transitions only where they support orientation.",
    "background_system": "Begin with a calm base surface, introduce subtle tonal shifts at narrative transitions, and use a slightly emphasized surface for selected work and capability groupings. Any line or node pattern remains low contrast and abstract.",
    "contrast_strategy": "Maintain clear separation between primary text, supporting text, surfaces, borders, and interactive states. Do not rely on low-contrast secondary text for essential content, and pair accent cues with labels, position, or shape.",
    "container_behavior": "Keep content within a readable central field that expands modestly on wide displays while preserving comfortable line lengths. Let the hero and selected-work areas use more horizontal breadth than body-copy sections, but keep all content anchored to a consistent outer rhythm.",
    "visual_personality": "Technical, trustworthy, practical, composed, and human-centered. Confidence comes from clarity and disciplined restraint rather than visual spectacle.",
    "alignment_character": "Favor purposeful left alignment for reading and scanning, with selective offset or split alignment for the hero and lifecycle visual. Avoid centered alignment for long explanatory copy.",
    "interaction_character": "Interactions should feel like inspection and navigation: clear focus, modest emphasis on hover or press, and predictable anchor movement. Avoid gamification, parallax-heavy scenes, or hidden information revealed only through motion.",
    "responsive_philosophy": "Preserve the narrative order and meaning across laptop, desktop, wide desktop, tablet, mobile, and touch-only use. Reflow asymmetric compositions into a readable sequence, simplify diagrams rather than shrinking labels, and make every hover-dependent cue available through focus, press, or static styling.",
    "text_density_behavior": "Keep the opening spacious, give selected work concise but substantial summaries, and compress technology inventories into grouped secondary treatments. On narrow screens, preserve the headline, positioning, project titles, and key capability labels before optional credentials or extended detail.",
    "typographic_character": "Use a sturdy, contemporary display voice for the name and principal statements, paired with a highly legible body face for technical explanations and lists. Headlines should read as calm professional assertions, not promotional slogans. Use hierarchy and line length to keep moderate information density approachable.",
    "performance_philosophy": "Prefer CSS-like surfaces, lightweight vector or text-based diagrams, and progressive enhancement. Avoid background video, large raster textures, unnecessary third-party animation, and loading media that has not been approved.",
    "accessibility_principles": "Use semantic reading order, visible keyboard focus, sufficiently large touch targets, descriptive labels for lifecycle relationships, and text alternatives for conceptual diagrams. Never encode project categories or lifecycle states by color alone.",
    "shape_radius_border_shadow": "Use modest corner softening, quiet hairline borders, and shallow or absent shadows. Panels should feel like organized work surfaces rather than floating cards. Reserve stronger enclosure for selected-work grouping and interactive focus states.",
    "iconography_illustration_diagram": "Prefer simple geometric markers, accessible text labels, and conceptual diagrams built from lifecycle stages and relationships already approved in the content. Do not use stock device imagery, invented logos, fake dashboards, or decorative icons that suggest unsupported functionality."
  },
  "compiler_handoff": {
    "pages_compilable": {
      "home": true
    }
  },
  "interaction_system": {
    "focus": "Provide a strong, consistent focus indicator that remains visible against every surface and is not conveyed by color alone.",
    "touch": "Use generous touch targets, avoid hover-dependent disclosures, and keep pressed states brief and nonessential to understanding.",
    "active": "Use a restrained surface or accent change for selected anchors and pressed controls, paired with text or position cues.",
    "anchors": "Use predictable in-page navigation with visible destination headings and no scroll hijacking.",
    "project_groups": "Project groupings may emphasize the title or reveal a compact technology treatment on hover, focus, or touch press, but summaries remain visible without interaction.",
    "capability_groups": "Keep capability labels and grouped items readable in the default state. Any expansion must be explicitly labeled and operable by keyboard and touch.",
    "error_or_missing_media": "If any conceptual visual fails to load, preserve a labeled text representation and the surrounding narrative without an empty media frame."
  },
  "must_not_fabricate": [
    "Metrics or percentage improvements",
    "Employer, client, or project names not verified for publication",
    "Public contact details or location permissions",
    "Repository contents, screenshots, testimonials, awards, or links",
    "Exact visual design choices inferred from the absent light/dark preference",
    "Real internal architecture diagrams, production dashboards, or evidence visuals when only conceptual diagrams are approved",
    "Credentials or education wording before verification",
    "Any team or organizational outcome represented as Maya’s individual achievement"
  ],
  "resource_candidates": [
    {
      "category": "hero_pattern",
      "fallback": "A plain text-led hero with no abstract cue.",
      "priority": "important",
      "confidence": "catalogue_verified",
      "resource_id": "hero_asymmetric_text_dominant",
      "possible_use": "Adapt the text-dominant hero pattern with a restrained abstract lifecycle cue.",
      "lookup_status": "verified",
      "why_it_matches": "The approved headline and positioning are strong, while no approved hero imagery exists; typography can carry the introduction.",
      "adaptation_notes": "Keep Maya’s identity and value proposition primary; avoid adding unsupported imagery or evidence.",
      "where_it_may_help": "home / home-introduction",
      "resource_library_version": "03ce83369dfc"
    },
    {
      "category": "diagram_primitive",
      "fallback": "A static text sequence of lifecycle stages.",
      "priority": "important",
      "confidence": "catalogue_verified",
      "resource_id": "diagram_process_flow",
      "possible_use": "Adapt as a small, labeled conceptual lifecycle connecting the selected-work themes.",
      "lookup_status": "verified",
      "why_it_matches": "The approved storytelling opportunities explicitly support a conceptual endpoint lifecycle from provisioning through support.",
      "adaptation_notes": "Keep the sequence short and legible on mobile; label it illustrative and never imply a real production workflow.",
      "where_it_may_help": "home / home-selected-work",
      "resource_library_version": "03ce83369dfc"
    },
    {
      "category": "diagram_primitive",
      "fallback": "Four grouped lists with lightweight dividers and no diagram.",
      "priority": "optional",
      "confidence": "catalogue_verified",
      "resource_id": "diagram_abstract_topology",
      "possible_use": "Adapt as a sparse relationship cue behind or beside the capability groups.",
      "lookup_status": "verified",
      "why_it_matches": "The approved capability relationship can be expressed as an abstract connection between endpoint platforms, security, automation, and service operations.",
      "adaptation_notes": "Do not present it as an internal architecture document or exact topology; omit it if it increases density.",
      "where_it_may_help": "home / home-capabilities",
      "resource_library_version": "03ce83369dfc"
    }
  ],
  "navigation_direction": {
    "form": "A compact anchor navigation that supports orientation without competing with the professional introduction.",
    "density": "Four concise destinations with a clearly differentiated public CTA treatment only if the approved connection channel becomes available. Do not add a destination for credentials or an unapproved contact route.",
    "placement": "Keep navigation easy to find near the top and optionally persistent after the opening when it does not reduce reading space.",
    "active_state": "Indicate the current reading region through accent, weight, or an adjacent marker, with a non-color cue available.",
    "cta_hierarchy": "Primary opening action points to selected work; secondary action points to capabilities. The connection prompt remains low pressure and must not expose an unavailable channel.",
    "mobile_strategy": "Collapse into a touch-friendly menu or compact anchor control while preserving all four approved destinations and a clear close state. Anchor movement should leave the destination heading visible.",
    "source_of_truth": "Use only the approved navigation destinations: About targets #home:positioning, Selected work targets #home:selected-work, Capabilities targets #home:capabilities, and Experience targets #home:experience.",
    "sticky_behavior": "A sticky treatment is optional and should remain visually quiet; disable or reduce it where it crowds the viewport on mobile or tablet.",
    "hover_focus_state": "Use a restrained text or underline emphasis on hover and a highly visible outline or equivalent focus treatment for keyboard users."
  },
  "shared_visual_systems": {
    "content_priority": "Hero and positioning establish identity; selected work is the principal supporting evidence; capabilities and experience establish breadth; credentials and connection remain optional and secondary.",
    "evidence_framing": "Frame approved project themes as representative areas of work, with title, concise summary, and technologies. Treat them as professional scope, not quantified case-study proof. Label conceptual diagrams as illustrative.",
    "card_panel_treatment": "Use a small number of quiet framed groups. Selected work receives the clearest panel structure; capabilities use lighter grouping; experience remains primarily editorial. Keep borders and surfaces subordinate to the text.",
    "section_divider_language": "Separate narrative phases with whitespace, short rules, or small lifecycle markers rather than heavy bands. Dividers should show progression from positioning to work to breadth to experience.",
    "recurring_background_layers": "Use a stable neutral base, alternating restrained surfaces for hierarchy, and a low-contrast lifecycle line motif that appears selectively rather than behind every section."
  },
  "accessibility_and_performance": {
    "color_contrast": "Use strong text-to-surface contrast for all essential content and reserve the accent for supplemental emphasis paired with labels or position.",
    "reduced_motion": "At system level, remove nonessential movement, staged reveals, parallax, and animated transitions when reduced motion is requested. Static lifecycle and content must remain complete.",
    "content_fallbacks": "Every conceptual visual has a readable text sequence or grouped-list fallback. Missing optional media never creates an empty or misleading evidence panel.",
    "keyboard_and_focus": "All anchors and any interactive grouping controls receive a visible, consistent focus treatment with logical document order and no focus traps.",
    "performance_choices": "Use text, CSS-like surfaces, and lightweight vector or custom diagram treatment. Avoid heavy background video, large raster backgrounds, elaborate network animation, and unapproved external media.",
    "responsive_accessibility": "Do not shrink technical labels below comfortable readability to preserve a diagram. Simplify or stack relationships on tablet and mobile, and support touch-only interaction without hover."
  }
}