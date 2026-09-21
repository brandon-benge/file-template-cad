# .makeitours/schema/

Infrastructure (see `tests/README.md`) — explicitly so, unlike its sibling
`.makeitours/audit/` (the per-project Git-triggered run history, which is
runtime output, not template content, and is excluded from reconciliation).

- **`git-opencode-run-v1.schema.json`** — the JSON Schema every Git-triggered
  OpenCode run must validate against before `tools/run-git-opencode-audit`
  will commit it, written to `.makeitours/audit/v1/<run_id>/run.json`. Covers
  the run's source event, OpenCode's own version/model/agent/exit code,
  timing, starting revision, changed paths, validation results, and captured
  events.
