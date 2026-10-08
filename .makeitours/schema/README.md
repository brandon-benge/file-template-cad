# .makeitours/schema/

Infrastructure (see `tests/README.md`) — explicitly so, unlike its sibling
`.makeitours/audit/` (the per-project Git-triggered run history, which is
runtime output, not template content, and is excluded from reconciliation).

- **`makeitours-run-v2.schema.json`** — the JSON Schema every Git-triggered
  makeitours-agentic run's `.makeitours/audit/v1/<run_id>/run.json` follows
  (`schema_version: 2`). Covers the run's source event, the agent's
  version/provider/model/exit code, timing, starting revision, changed paths,
  validation results, and captured events.
- **`git-opencode-run-v1.schema.json`** — the earlier OpenCode runs'
  schema (`schema_version: 1`), kept because older runs stay in history and
  the MakeItOurs app still reads them.
