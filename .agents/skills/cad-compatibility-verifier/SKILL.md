---
name: cad-compatibility-verifier
description: Independently verify the current project, pinned PyPI CAD package, environment, declared commands, generated file presence, and structural readability without editing source.
compatibility: opencode
metadata:
  repository: benge-property-cad
  role: verification
---

# CAD Compatibility Verifier Skill

## Purpose

Verify reproducibility and technical compatibility without changing the project.

## Non-modification contract

Never edit:

- source
- tests
- configuration
- dependency locks
- workflows
- generated artifacts
- agent definitions
- skills
- governance files

Never clone, copy, vendor, unpack, or duplicate either repository.

Never install `python-cad-tools` from a local checkout or in editable mode.

Temporary verifier-owned reports or temporary environments may be created
outside authoritative project paths only when required for verification.

## Environment inspection

Record before running checks:

- operating system and architecture
- Python executable and version
- virtual environment state
- selected dependency lock
- installed distribution version
- resolved `python_cad_tools` module path
- `python-cad` executable path and version
- relevant browser/runtime availability

Inspect first. Do not replace the current environment automatically.

## Verification depth

Default to basic testing. Run full build, determinism, site, HTTP, browser, or
other E2E checks only when the user explicitly requests E2E testing or a full
upgrade, or when `python-cad-tools` changes its minor or major version. A change
only to the patch component, such as `0.1.4` to `0.1.5`, never requires E2E.

## Verification sequence

Run only commands supported by the current project.

Typical basic sequence:

```text
ruff check config.py model.py drawing_annotations.py tests/
ruff format --check config.py model.py drawing_annotations.py tests/
mypy config.py model.py drawing_annotations.py tests/
python -m pytest -q tests/test_workflow_policy.py
```

For full verification, additionally run the project-declared build,
validation, verification, determinism, site, HTTP, and browser checks.

### Element-level validation detail

Newer `python-cad-tools` versions include each failing `element_id` directly
in `python-cad validate`'s CLI message (`code[element_id]: message`). If the
installed version predates that and the message shows only `code: message`,
get full per-issue detail, including `element_id`, through the Python API
instead:

```text
python3 -c "
from pathlib import Path
from python_cad_tools.build import validate_project, ValidationOptions
report = validate_project(ValidationOptions(Path('.'), None))
for issue in report.issues:
    print(issue.severity, issue.code, issue.element_id, issue.message)
"
```

Report full per-issue detail back to `file-design-maintainer`, not just the
CLI's summary.

## Artifact structure checks

For each expected supported output:

- confirm existence
- confirm nonzero size when appropriate
- verify recognizable file signature or parser readability
- confirm manifest registration
- confirm expected companion metadata or report
- capture parser or command errors

Formats may include STEP, IFC, STL, GLB, SVG, DXF, PDF, manifests, reports,
quantities, and site content.

Do not judge semantic correctness of labels, types, dimensions, or geometry;
delegate that to `file-artifact-reviewer`.

## Package blocker diagnosis

When failure appears package-related:

1. capture exact command and error
2. confirm installed version and module path
3. reproduce using project-declared inputs
4. consult public package documentation or remote source only if needed
5. do not clone the repository
6. separate confirmed behavior from inference
7. state expected public API or tool behavior

## Delegation

Invoke `file-design-maintainer` for confirmed failures in editable project
source.

Invoke `file-artifact-reviewer` when files are technically valid but require
semantic, label, metadata, standards, visual, or cross-format review.

Invoke `save` only after the user explicitly asks to commit the changes to Git.

## Machine-readable report

Produce JSON or an equivalent machine-readable report with:

- timestamp
- project root
- environment
- package
- commands
- checks
- artifacts
- skipped checks
- warnings
- blockers
- delegated findings
- final status

Final status must be one of:

- `pass`
- `pass_with_warnings`
- `blocked`
- `fail`
