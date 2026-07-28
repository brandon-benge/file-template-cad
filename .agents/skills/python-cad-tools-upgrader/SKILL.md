---
name: python-cad-tools-upgrader
description: Upgrade the published python-cad-tools dependency, regenerate project locks, and choose basic or full testing from the semantic version change. Use for python-cad-tools dependency bumps, package upgrade requests, lock refreshes caused by that package, or deciding whether an upgrade needs E2E testing.
---

# Python CAD Tools Upgrader

Upgrade only the published PyPI package. Never use a local checkout, editable
install, vendored source, or a modification to `site-packages`.

## Classify the request

Read the installed/current version and the requested version before changing
files.

- Treat a change only to the patch component, such as `0.1.4` to `0.1.5`, as a
  patch upgrade.
- Treat a change to the minor or major component as a full upgrade.
- Treat any upgrade as full when the user explicitly requests a full upgrade
  or E2E verification.
- Do not describe `0.1.x` to `0.1.y` as a minor upgrade; it is patch-only under
  semantic versioning.

## Apply the upgrade

1. Update the `python-cad-tools` requirement in `pyproject.toml` as requested.
2. Regenerate every supported native dependency lock using the repository's
   documented `pip-compile` commands.
3. Reject locks containing local paths, editable installs, source checkout
   references, or a version outside the declared requirement.
4. Run the following upgrade smoke sequence from the project root:

```bash
.venv/bin/pip install --upgrade .
.venv/bin/python-cad --version
.venv/bin/python-cad clean
.venv/bin/python-cad serve --build --port 8080
```

Run `serve` as a bounded smoke check: wait for successful startup, make one
local HTTP request, then stop the server cleanly. Do not leave it running.

## Select testing depth

For a patch upgrade, run only:

```bash
.venv/bin/pip check
.venv/bin/python -m pytest -q \
  tests/test_workflow_policy.py
```

Do not run `tests/test_build_artifacts.py`, `tests/test_build_cli.py`, `tests/test_build_determinism.py`, `tests/test_viewer_e2e.py`,
Playwright, determinism tests, or the complete verification matrix for a patch
upgrade unless the user explicitly requests E2E testing.

For a full upgrade, run the repository's complete static, unit, build,
validation, verification, determinism, site, HTTP, and browser checks. The same
E2E coverage is available through the manually dispatched GitHub Actions
workflow `File Template CAD End-to-End`.

## Report

Report old and new versions, classification, changed dependency and lock files,
commands and exit statuses, whether the bounded server smoke passed, testing
depth, skipped E2E checks and reason, and blockers. Never claim E2E coverage
when only basic checks ran. Invoke `save` only after the user explicitly asks
to commit the changes to Git.
