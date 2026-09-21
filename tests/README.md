# tests/

Infrastructure (per `tools/reconcile-infrastructure`'s own definition: everything
except `config.py`, `model.py`, `drawing_annotations.py`, `models/**/*.py`, and
`generated/`) — kept in sync with this repository's sister projects rather than
authored per-project. Verified by hand on every change here; only
`test_git_opencode_audit.py`'s byte-identity is enforced automatically, by
`test_workflow_policy.py::test_sister_repository_contract_parity`.

- **`conftest.py`** — shared fixtures: `repo_root`, project-copying helpers for
  isolated build fixtures, and `identity` (the project's own model id, artifact
  stem, and annotation provider id, read from a real build rather than typed
  as a literal — see "Naming" below).
- **`test_build_artifacts.py`**, **`test_build_cli.py`**,
  **`test_build_determinism.py`**, **`test_build_formats.py`** — the
  `integration`-marked tier: full and partial builds, CLI behavior,
  cross-build determinism, and per-format output. Run with
  `pytest -q -m integration`.
- **`test_git_opencode_audit.py`** — focused transaction tests for
  `tools/run-git-opencode-audit`, using its own throwaway checkouts/remotes.
  Passes unmodified in a project seeded from this template, since it never
  reads this repository's own `.github/`.
- **`test_viewer_e2e.py`** — packaged viewer/site and Playwright Chromium
  tests (`e2e`, `viewer` markers); needs Node/Playwright and is not run by
  default.
- **`test_workflow_policy.py`** — static policy checks on this repository's
  own `.github/workflows/*.yml` and related governance files. Skips entirely
  (module-level `pytestmark`) when `.github/` is absent — true of every
  project seeded from this template, since `GithubReleaseTemplateSource`'s
  `EXCLUDED_PREFIXES` (in `makeitours-data-plane`) strips it. These checks are
  meaningless outside a full template checkout, not merely inapplicable, so
  they must not report a failing exit code there.

**Naming:** several tests read the project's own model id, artifact stem, and
annotation provider id (via the `identity` fixture) instead of hardcoding this
template's `file.template` / `FileTemplate` / `file.template.annotations` — a
project instantiated from this template renames all three, and the tests pass
either way.

If this directory is restructured, this file no longer describes it — don't
try to keep it in sync with a layout that no longer exists.
