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
  paths or `generated/`. Invoked by `run-git-opencode-audit` before every
  OpenCode edit loop so the AI always works against an up-to-date template.
- **`run-git-opencode-audit`** — the entry point `.github/workflows/opencode.yml`
  invokes when the repository owner opens an issue or comments `/oc`/`/opencode`.
  Drives one full Git-triggered OpenCode transaction: validates the
  provider/model, runs `opencode` through `run-with-inactivity-watchdog`,
  writes a schema-validated audit run under `.makeitours/audit/v1/<run_id>/`,
  and commits/pushes only on success. On failure it leaves history untouched
  and writes redacted evidence for the workflow to upload instead. Not meant
  to run outside that workflow.
- **`run-with-inactivity-watchdog <inactivity_seconds> <command> [args...]`**
  — internal helper `run-git-opencode-audit` uses to run `opencode` itself:
  streams output live while writing a redacted, size-bounded copy for the
  audit trail, and kills the whole process group (exit 124, like GNU
  `timeout`) if it goes quiet for `inactivity_seconds`. Not meant to be
  invoked directly.

If this directory is removed or restructured, this file no longer applies.
