# Canonical Build Preparation fixture for Code Generator

This document points at the privacy-safe fixture used by the Code Generator
runbook. The checked-in projections and ZIP are authoritative; this pointer
must not be treated as a substitute for immutable artifact admission.

**This specific checked-in pack predates D-060** and was materialized before
Build Preparation deferred image/font/component bytes to Code Generator's
own acquisition phase -- its image/component resolutions below are genuinely
`local_materialized` (real bytes already in the ZIP), not
`deferred_materialized`. A pack generated after D-060 expresses the same
kind of decision (one exact provider + candidate, already verified) but
without embedding the bytes; see `README.md`'s "Build Preparation pack v3"
section for the current contract. The facts below remain an accurate
description of this exact fixture's real, checked-in content.

## Selection

Canonical local fixture:

```text
runbook path:  prebuild-output/build-preparation/15-36-25-08-8acdcb12/
run_id:       8acdcb12-11f5-4f05-8013-726575efaba9
pack_version: build-preparation-pack-v3
pack_sha256:  8fef409f337596c94941fdf3d05f7aea291b2bbad404c0c2637e638a718e7de0
scope_hash:   5324e4fc1af38622a0f00faff326079d0f6f14cfc01dbfb374ed1e5acde3df11
expires_at:   2026-08-28T10:06:34.576853+00:00
zip_size:     1,129,071 bytes
manifest:     39 files
```

The ZIP and extracted context are available at:

```text
prebuild-output/build-preparation/15-36-25-08-8acdcb12/build-pack.zip
prebuild-output/build-preparation/15-36-25-08-8acdcb12/build-context/
```

This captured artifact is now expired and must be regenerated before a live
Code Generator run. The path is a deterministic development reference, not a
license to select whichever folder is newest. In the production session flow,
Code Generator reads the immutable object reference recorded by Build
Preparation, verifies object metadata and SHA-256, and applies the same pack
admission rules. The current configuration is the source of truth for accepted
pack versions, including the V4 delegated-pack contract.

## Handoff status at capture

The captured `handoff-report.json` recorded:

- `handoff_eligible: true` and `code_generator_eligible: true`;
- one approved public route;
- five of five targeted image roles materialized locally;
- two component sources materialized from the four-role target;
- one local Space Grotesk family with four weights;
- one unresolved optional image role (`home:about-connect`), which must remain
  unillustrated unless upstream direction is revised; and
- no blocking execution gap in the report's top-level status.

Eligibility is time-sensitive. A current run must still pass expiry, object,
approval, hash, scope, and execution checks at admission.

## Approved public route

The canonical input contains one approved public route:

```text
route_id: route:home
path:     /
storage:  routes/home-4ea140588150
```

Its approved sections, in order, are:

1. `home:hero` — positioning and the primary portfolio action;
2. `home:selected-work` — payments, commerce, logistics, and healthcare work;
3. `home:approach` — the research-to-systems design process;
4. `home:experience` — two concise professional entries;
5. `home:design-systems` — systems, craft, tools, and implementation awareness;
6. `home:about-connect` — concise personal context, education, and approved links.

The single route is the approved public scope for this input, not a generic
portfolio rule. Code Generator may choose the visual composition, internal
scenes, responsive grouping, and interaction surfaces, but it may not invent a
second public route, stronger claims, or unavailable evidence.

The route contract requires a text-led, moderate-density presentation; clear
emphasis on selected work and the research-to-systems narrative; the supplied
LinkedIn URL; and neutral, non-evidentiary treatment of decorative imagery.
It forbids fabricated metrics, screenshots, testimonials, awards, client
details, team or timeline claims, and a phone contact method.

## Prepared visual resources

Every binding below is local or a declared target-package dependency. Generated
sites must not fetch these resources from providers at runtime. The exact
placement, fallback, import path, license, and hash come from
`build-context/execution/contract.json`, `resources/projection.json`, and the
manifest.

### Images

The five materialized image bindings are:

```text
resource-pixabay-d85095d80f5f23be1e95
resource-pixabay-2bf5c084e29d1ae09db4
resource-pexels-ee43d84747dcbbaf047e
resource-pexels-042df95aaefc38bf9ad3
resource-pexels-69c4f6fcbe2a01753e39
```

They live under `resources/images/` in the pack. They are decorative and
representative only; they must not be described as the user's projects,
workplaces, architecture, or evidence. The unresolved `home:about-connect`
image role has no local binding and should be implemented without an image.

### Components and font

- `resource-smoothui-d7a42b9814bfe7c97f23` is the local SmoothUI
  expandable-cards source under
  `resources/components/smoothui/.../source/index.tsx`.
- `resource-magicui-0bcd9511bdad151cae2f` is the local Magic UI animated-beam
  source under `resources/components/magicui/.../source/registry/animated-beam.tsx`.
  Its name is not a semantic experience-timeline contract; use the declared
  accessible static fallback when the experience section needs chronology.
- `resource-fontsource-b69f66a0c66ec46921e7` is the local Space Grotesk family
  under `resources/fonts/`, with weights 400, 500, 600, and 700, licensed under
  OFL-1.1.
- The target package supplies the approved `lucide-react` icon dependency and
  the starter React/Vite/Tailwind target. Code Generator must generate the
  final lockfile from the chosen dependency subset.

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

`overview.md` is a human/model briefing for orientation. It does not override
these projections and is not a reason to invent routes, components, facts,
dependencies, or remote runtime assets.

## Projection hashes

These are the SHA-256 values of the canonical extracted projections and ZIP.
Consumers should recompute them and bind planning, generation, and preview
receipts to the admitted pack identity:

```text
zip:        8fef409f337596c94941fdf3d05f7aea291b2bbad404c0c2637e638a718e7de0
manifest:   9997d39155c4a3fb093232496bd57b0e885327f46999c02a6fba95ef816b6136
site:       5e850f2886d3dff9e7d86df7c81046e1ce369fa4c96e11be2876aa73d94b6694
visual:     6a476843a121107f8e9174a047cdf28559a50e6b6cc60a8ed1b533e260132e4d
approvals:  e0c927a321efc3f4fc4e5217ff49a7358e63f76dfe504e88936550dea97c7c26
targets:    aadbcfdb71f6f8ddb61ad7b5793ab101318994e6a69e846aaf7cce40bbe1f186
resources:  752f1a4b6cca7178000cb8984e90a2fbb2d0b6163c86be94214010c490adf622
ledger:     cbb39c543fe92fa9281afe050c9baa855ec720738bed0563882117c4edacb221
execution:  2e756a7c19f6359d4b5ba997fe2ca06a46fe081c3f93c23abd85e218dab5ae2b
recipes:    8395e9f0c43839c75b3d362596ef94fe352bccc527e3b5df5d1bfc74ea5006c9
```

The ZIP and its hash-covered projections remain authoritative over this
selection pointer.
