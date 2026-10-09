# tools/

Infrastructure (per `tools/reconcile-infrastructure`'s own definition:
everything except `config.py`, `model.py`, `drawing_annotations.py`,
`models/**/*.py`, and `generated/`), so this directory is meant to be kept in
sync with this repository's sister projects rather than authored per-project
— though that sync is a manual, on-demand run of the tool below, not
automatic; a sister repo can carry an extra script here until it's rerun.

- **`reconcile-infrastructure [--plan] [--source] <path-to-file-template-cad>`** —
  brings this repo's tracked infrastructure to a template checkout, or, with
  `--source`, to an extracted release archive: overwrites drifted files, adds
  missing ones and removes ones the template no longer has, keeping
  `pyproject.toml`'s own `source-inputs`. `--plan` prints the changes as JSON
  and writes nothing. Never touches the four customer-owned CAD-authoring
  paths, `generated/` or `.makeitours/audit/`, and never removes the release
  identity. Upgrade Project runs it (2026-10-09 approval,
  project-upgrade-button); nothing runs it automatically any more, and the
  ticket runner stops calling it once its next release ships.
- **`release-identity <archive tree> <tag> <commit> <policy output>`** —
  used by `release-template.yml`: writes `.makeitours/template-release.json`
  (the release a project's infrastructure came from) into the archive, and
  `template-policy.json` (the latest release, its `python-cad-tools`, and the
  minimum supported release from `.github/release-policy.json`) beside it.

The ticket runner itself is not in this directory: it ships in the public
`makeitours-agentic-runner` image the workflow pins by digest. It validates
the provider/model, runs the agent, writes a schema-validated audit run
under `.makeitours/audit/v1/<run_id>/`, commits and pushes only on success,
and comments the outcome or its question on the issue.

If this directory is removed or restructured, this file no longer applies.
