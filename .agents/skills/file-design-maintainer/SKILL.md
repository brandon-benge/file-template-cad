---
name: file-design-maintainer
description: Implement and validate property-specific parametric CAD changes, complex element semantics, labels, metadata, relationships, tests, and supported outputs.
compatibility: opencode
metadata:
  repository: benge-property-cad
  role: implementation
---

# File Design Maintainer Skill

## Purpose

Implement requested changes to the property model while preserving
parametric behavior, deterministic output, stable semantic identity, and
cross-format consistency.

## Editable scope

Edit only:

- `config.py`
- `model.py`
- `drawing_annotations.py`
- `tests/`

Generated content is evidence only and must not be edited.

## Package boundary

Use only documented public APIs from the installed `python_cad_tools` package.

Never:

- inspect or patch package internals
- modify `site-packages`
- vendor or unpack package source
- install from a local checkout
- create a parent-repository workaround that bypasses a missing public API

## Model contract

Every complex element must define and preserve, as applicable:

- deterministic parametric geometry
- stable `complex.*` semantic ID
- complex type
- human-readable label
- annotations
- metadata
- dimensions and units
- materials
- standards mappings
- ownership, hierarchy, adjacency, and connection relationships
- quantity and drawing participation
- export participation

Create or update these properties together. Geometry without required semantic
identity and labels is incomplete.

## Output responsibilities

Generate all project-supported outputs, which may include:

- STEP
- IFC
- STL
- GLB
- SVG
- DXF
- PDF
- drawings
- manifests
- validation reports
- quantities
- generated site content

Only require formats declared by the current project and installed toolchain.

## Standards responsibilities

- Preserve units and coordinate conventions.
- Preserve stable IDs unless migration is intentional.
- Keep labels unique where the project contract requires uniqueness.
- Ensure required metadata exists for each complex type.
- Keep dimensions, materials, hierarchy, bounds, labels, and IDs consistent.
- Ensure drawings and quantities reference the same semantic elements as the
  model.
- Treat missing required IDs, types, labels, or relationships as blockers.
- Do not claim professional engineering, permit, code, survey, or trade
  approval.

## Blocker handling

When required behavior cannot be implemented using the documented public
`python_cad_tools` API:

- Do not inspect, patch, or depend on package internals.
- Do not modify `site-packages`.
- Do not vendor package source into this repository.
- Do not implement a workaround that bypasses the public API.
- Collect evidence showing the missing capability or defect.
- Describe the required upstream capability and expected public API behavior.
- Explain the impact on this project.
- Continue unaffected work where possible.
- Invoke `cad-compatibility-verifier` when independent confirmation is needed.
- Return the unresolved blocker to the caller.

## Debugging repeated validation failures

If the same validation error persists after changes that only adjusted
numeric parameters (position, size, offset), stop tuning numbers — that
pattern means the construction code has a structural bug, not a bad value.
Inspect the helper function building the failing element instead of guessing
another set of numbers.

### `solid-invalid` and other geometry-validity failures

`solid-invalid` means a physical element's `geometry` is not a single
positive-volume `Solid`. A common, non-obvious cause: a boolean `.cut()` (or
`.fuse()`) whose cutter can fully span a shape's cross-section splits that
shape into multiple disconnected solids. The CAD kernel returns that as a
multi-solid compound, which fails validity even though every individual
piece is itself a valid solid.

- Before adding a cut/fuse inside a construction helper, consider whether the
  cutter can bisect the shape along its own length — a wide or long cutter
  through a narrow or short member is the usual trigger.
- After a cut whose result could contain more than one solid, inspect the
  resulting solid count. If it can be more than one, emit one physical
  element per solid, with a distinguishing name suffix (e.g. `_Left`/
  `_Right`, or `_01`/`_02` for more than two pieces), rather than keeping a
  multi-solid result as a single element's geometry.

### Finding which element failed

The validation message you receive (in a local Mac AI session, or from
`python-cad validate`'s CLI output) reports only the issue code and message —
not which element failed. Element stable IDs follow
`complex.<slug(category)>.<slug(name)>`, generated from the `category`/`name`
arguments passed to `add_shape`/`add_box`/`add_cylinder` (or an explicit
`stable_id` override). Use the error code to narrow the search: `solid-invalid`
only applies to `physical=True` elements; `recipe-*` codes only apply to
elements built from a `ConstructionRecipe`. Audit the most recently changed
call sites of that kind first.

When the toolchain is available (CI or a GitHub-triggered run — not a local
Mac AI session), invoke `cad-compatibility-verifier` to get full per-issue
detail, including `element_id`, instead of relying on the CLI's single joined
message.

## Subagent use

Invoke `file-artifact-reviewer` for:

- semantic review
- label and metadata review
- standards review
- drawing and quantity review
- cross-format consistency review
- visual or site review

Invoke `cad-compatibility-verifier` for:

- package installation or version questions
- lock and platform compatibility
- command failures
- output parser or structural validity questions
- full per-element validation detail (element IDs) when the toolchain is
  available
- HTTP, site, or browser verification
- suspected upstream package defects

Invoke `save` only after the user explicitly asks to commit the changes to Git.

## Delegation safeguards

- Make at most one handoff for the same distinct blocker.
- Include affected files or artifacts, stable IDs, evidence, expected result,
  and acceptance criteria.
- Do not return the same blocker to the caller without new source changes,
  regenerated artifacts, or new verification evidence.
- Return unresolved blockers instead of repeating a delegation cycle.

## Workflow

1. Parse the request into geometry, semantic, drawing, quantity, and output
   changes.
2. Inspect editable source, tests, manifests, and generated evidence.
3. Identify affected complex IDs, types, labels, metadata, and relationships.
4. Implement the smallest coherent parametric change.
5. Update or add focused tests only when a change affects build, viewer, or workflow-policy behavior. Do not create or update design-input validation tests (they have been removed). Never update model-specific test assertions (IFC mappings, element IDs, annotation content, dimensions, positions, materials) in any test file — those are manual-reference snapshots.
6. In a local Mac AI session, do not select or run a verification tier
   yourself — the toolchain (`ruff`, `mypy`, `pytest`, `python-cad`) is
   intentionally not on PATH for that session type; treat this as permanent,
   not a gap to search around.
7. The tiers described in `AGENTS.md` (focused, export-sensitive, full/E2E)
   describe what CI and GitHub-triggered runs execute — not commands to run
   in a local Mac AI session.
8. AI CAD's own build step regenerates affected outputs and runs
   `python-cad validate`/`build` automatically after this session finishes.
9. Inspect generated evidence only when it is already available from a prior
   build; do not trigger a build yourself to produce it.
10. Delegate independent review where appropriate.
11. Resolve findings within the editable scope.
12. Return changed files, affected stable IDs, and any unresolved blockers.

## Completion evidence

In a local Mac AI session, "commands run" and "generated outputs" are
typically empty — validation and output generation happen in AI CAD's own
build step and in CI, not during this session.

Report:

- changed source files
- affected stable IDs and complex types
- labels or metadata added or changed
- tests added or changed
- commands run
- generated outputs
- delegated review results
- unresolved blockers
