# tools/

Infrastructure (per `tools/reconcile-infrastructure`'s own definition:
everything except `config.py`, `model.py`, `drawing_annotations.py`,
`models/**/*.py`, and `generated/`), so this directory is meant to be kept in
sync with this repository's sister projects rather than authored per-project
— though that sync is a manual, on-demand run of the tool below, not
automatic; a sister repo can carry an extra script here until it's rerun.

- **`reconcile-infrastructure <path-to-file-template-cad-checkout>`** —
  overwrites every tracked infrastructure file in this repo with the
  template's live committed version, and removes any infrastructure file the
  template no longer has. Never touches the four customer-owned CAD-authoring
  paths or `generated/`. Invoked by `makeitours-agentic-git-run` (the
  `.github/workflows/makeitours.yml` ticket runner, in the makeitours-agentic
  runner image) before every agent run, so the AI always works against an
  up-to-date template.

The ticket runner itself is not in this directory: it ships in the public
`makeitours-agentic-runner` image the workflow pins by digest. It validates
the provider/model, runs the agent, writes a schema-validated audit run
under `.makeitours/audit/v1/<run_id>/`, commits and pushes only on success,
and comments the outcome or its question on the issue.

If this directory is removed or restructured, this file no longer applies.
