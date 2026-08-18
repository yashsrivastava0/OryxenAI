# Selected Build Preparation output for Code Generator

Status: selected on 2026-08-18 after live provider acceptance.

This is the Build Preparation pack to use while working on the Code Generator
agent. Select it by its immutable identity and SHA-256, not by whichever local
folder happens to sort first.

## Selection

Selected pack:

```text
run_id:       64801150-cb6d-4052-ae1e-2a30ab55fb20
pack_version: build-preparation-pack-v3
pack_sha256:  087fb5793e901d129ba91e6c5beabb9f97fa062598c2da6b25ebdd36e960f1d4
scope_hash:   b511ab603400c48a8d0bae4e998ec3f6a01322b77b3bf0dbba0fc70c5e5bf62f
expires_at:   2026-08-21T18:00:26.335827+00:00
zip_size:     1,214,932 bytes
manifest:     45 files
```

Development mirror paths:

```text
output/live-build-preparation/build-preparation/23-30-18-08-64801150/
output/live-build-preparation/build-preparation/23-30-18-08-64801150/build-pack.zip
output/live-build-preparation/build-preparation/23-30-18-08-64801150/build-context/
```

The local directory is only a debug mirror. In the production session flow,
the same immutable ZIP is read from the R2 object reference recorded by Build
Preparation. The R2 object key, version/ETag, size, expiry, and SHA-256 belong
to the artifact/state handoff; they are not inferred from this folder name.
Code Generator must download the R2 object, verify the recorded SHA-256, and
then apply the same pack-v3 admission and extraction rules used by the
development mirror.

## Why this is the selected output

This is the newest live-accepted pack and the only eligible pack currently
available in the local mirror:

- `handoff_eligible: true`
- `code_generator_eligible: true`
- zero execution gaps and zero unresolved visual roles;
- six semantic image needs, all six materialized locally;
- three semantic component needs, all three materialized locally;
- one local Space Grotesk font family with four weights;
- no total-enrichment or partial-enrichment failure;
- 13 provider calls, with three handled rate-limit events;
- complete provenance, license, checksum, route, target, and execution
  projections; and
- ZIP creation, artifact verification/read-back, and local Code Generator
  admission all passed.

The other available pack,
`output/live-build-preparation/build-preparation/21-09-18-08-8fb44e9e`, is
not a candidate: its handoff is ineligible and it contains two execution gaps.
Do not use it for Code Generator work.

## Approved public route

The selected input contains one approved public route:

```text
route_id: route:home
path:     /
storage:  routes/route-home-6c743f5342c5
```

Its six approved sections, in order, are:

1. `home:hero` — professional positioning and entry point;
2. `home:capabilities` — backend, data, delivery, and product-surface
   capabilities;
3. `home:experience` — two neutral engineering experience entries;
4. `home:selected-work` — three technical project stories;
5. `home:education` — concise academic context; and
6. `home:connect` — LinkedIn primary CTA and GitHub secondary CTA.

The single route is the approved public scope for this input, not a generic
portfolio rule. Code Generator must cover this route and these semantic
sections, but it may choose the visual composition, number of internal scenes,
responsive grouping, interaction surfaces, and component usage. A different
public screen or route count requires new upstream Content Architect and Visual
Design Director approval.

The five route acceptance criteria are:

- all six sections appear in the approved narrative order;
- the page remains readable, moderate-density, and text-led;
- visuals remain abstract and representative rather than personal/project
  evidence;
- LinkedIn is the primary CTA and GitHub is secondary; and
- experience and selected work are the strongest proof regions without
  fabricated evidence.

## Prepared visual resources

Every row below is an executable local binding, not a remote URL that the
generated portfolio may fetch at runtime. The `import_path`, local path, hash,
license, placement, and fallback are authoritative in
`build-context/execution/contract.json`.

### Images

| Placement | Resource ID | Provider and asset | Local path | Final dimensions | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| hero | `resource-pexels-2e7ed5a84d64c39aa5b1` | Pexels `1779825` | `resources/images/resource-pexels-2e7ed5a84d64c39aa5b1.jpg` | 1880×1057 | `e624ea9669e2dbdc63400ffd29a79ec4363eec56b2bb9d85cf42607850c26100` |
| capabilities | `resource-pexels-3879c71bff387f9a8b6d` | Pexels `17483871` | `resources/images/resource-pexels-3879c71bff387f9a8b6d.jpg` | 1587×1058 | `dabdb6a75f5dcb3651c0d7bd3f3fed6a2f7308537e7c56da47f9e102f2405d1c` |
| experience | `resource-pexels-eb0ef4e1d18b83ef1b59` | Pexels `34037163` | `resources/images/resource-pexels-eb0ef4e1d18b83ef1b59.jpg` | 1820×1300 | `fba941fbbb2137ffef5a24592159e3d42d1806ba7df75a7108b9ca1e387388e4` |
| selected work | `resource-pexels-1dbd872cafbdcf865721` | Pexels `17483874` | `resources/images/resource-pexels-1dbd872cafbdcf865721.jpg` | 1410×1058 | `cb54ca51e26e1df240822e6f3583abc95229bbf431a3fe28b55026b9ac9d935f` |
| education | `resource-pexels-62a7789afb3913928548` | Pexels `846793` | `resources/images/resource-pexels-62a7789afb3913928548.jpg` | 1880×1258 | `a6bfdeed41742eb6f26680b594679a2abb89e2bf5e57d91ab5f73ecf324cd27f` |
| connect | `resource-pixabay-db432b0dffb02efa44c1` | Pixabay `4814456` | `resources/images/resource-pixabay-db432b0dffb02efa44c1.jpg` | 1280×720 | `6e5e2cffc47907c51bf909d58a9e57eac996607453c19aa4cf169b8a7efc0426` |

All six are local, pixel-inspected, attributed, licensed, and configured to
render statically with a decorative/secondary treatment. They must not be
described as the user's projects, workplaces, architecture, or evidence.

### Components

| Role and placement | Resource ID | Provider asset | Local source / import directory | Exports | Dependencies |
| --- | --- | --- | --- | --- | --- |
| capability grouping, `home:capabilities` | `resource-smoothui-12bad50f4b2ec4eb393d` | SmoothUI `basic-accordion` | `resources/components/smoothui/resource-smoothui-12bad50f4b2ec4eb393d/source/index.tsx` / `.../source` | `AccordionItem`, `BasicAccordion`, `BasicAccordionProps` | `motion`, `lucide-react` |
| experience timeline, `home:experience` | `resource-magicui-cd5375353fbb1f2fc3a5` | Magic UI `spinning-text` | `resources/components/magicui/resource-magicui-cd5375353fbb1f2fc3a5/source/registry/magicui/spinning-text.tsx` / `.../source` | `SpinningText` | `motion` |
| selected-work detail, `home:selected-work` | `resource-smoothui-065b3f87b5de8eb4df49` | SmoothUI `expandable-cards` | `resources/components/smoothui/resource-smoothui-065b3f87b5de8eb4df49/source/index.tsx` / `.../source` | `Card`, `ExpandableCards`, `ExpandableCardsProps` | `motion`, `lucide-react` |

Component source hashes are, in the same order:

```text
ef0f685060fde49a375f6c28dc672d563a568c09ac7982d714cdae87eead135c
55726f972d09705b0cd10e8739e74afe8d11b7164537554f99905267e456dafa
9d46b5ae4c2ec8fb5d1f7010b41e0ad084642f7a24b551c3982140d1d22deede
```

The Magic UI source is valid local material, but its name is not a semantic
timeline implementation. The declared fallback is the preferred flow:
render a static, ordered experience timeline with headings, dates, visible
structure, keyboard access, and reduced-motion safety. Do not force spinning
text into the experience section merely because that source is available.

### Font and package binding

- Fontsource `space-grotesk`, resource ID
  `resource-fontsource-b69f66a0c66ec46921e7`, is local under
  `resources/fonts/resource-fontsource-b69f66a0c66ec46921e7/` with weights
  400, 500, 600, and 700. It is licensed under OFL-1.1.
- The icon slot is a target-package binding for `lucide-react` with
  `ArrowUpRight`, `Menu`, and `X` exports. It is not a local component folder.
- Six typed local recipes cover the approved typography, composition, diagram,
  and static visual fallbacks. Recipes are not substitutes for the six images
  or three component roles.

## Pack files Code Generator must use

The authoritative read order is:

1. `manifest.json` — file list, sizes, pack identity, expiry, and source
   reference;
2. `handoff-report.json` — eligibility, gaps, role classifications, selected
   resource IDs, provider diagnostics, and projection hashes;
3. `site/contract.json` — exact route, section, content, criteria, and route
   file references;
4. `design/visual-direction.json` — visual language and experience outcomes;
5. `execution/contract.json` — one route/scene/section-scoped resolution for
   every known slot;
6. `resources/projection.json` and `resources/ledger.json` — materialized
   resources and decision history;
7. `provenance/approvals.json`, `targets.json`, `licenses.json`, and
   `checksums.json` — admission and integrity evidence; and
8. `routes/` and `resources/` — local content and source bytes.

`overview.md` is a detailed human/model briefing for orientation. It does not
override these projections and is not a reason to invent routes, components,
facts, dependencies, or remote runtime assets.

## Projection hashes

The selected handoff report records these hashes. A consumer should verify
them after reading the ZIP and bind subsequent planning, generation, and
preview receipts to the admitted pack identity:

```text
site:      3f4111f9de315c152a22eb2e5ea4dd8ce7bfd81b663da134d63168290c04d7b9
visual:    8d82bdaa52508c5c8906567cd72a1859aafc7ddc7f84a2b508ab77cb0885ab54
approvals: 73b89880a8cc03a75730e1b400ff4c8596e9e67c42d6d205628f0ee089ef014f
targets:   0856cf30a71a4c3e3d819ef49b90024c1a2451ad266a9c6eb48373d34b94c2c4
resources: bd7d6b5a27c1d9665f635c737b1a8ef918b03ef6469e25fa671fb1c8b9c8793d
ledger:    1c25615062d0a508d1c68ca27f7ea1bbf09db697671c66b76aafb4e2bc6b516b
execution: 0870b2b296936dcc2b2d9549c36ee717fc46fbc64b9c7da76e4e53f032118b54
recipes:   7edf66170a28060ba2f6482b5dfec5ed0424f607d2764ab2904d5fd8ce54dbf8
```

This document is a selection pointer and working context. The ZIP and its
hash-covered projections remain the authoritative handoff.
