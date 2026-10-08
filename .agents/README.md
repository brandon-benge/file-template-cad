# .agents/

Infrastructure (see `tests/README.md`): the canonical source for this
project's subagent and skill definitions, readable by any local agent runtime
(for example Claude Code or Codex). Agents never commit: the person saves from
the MakeItOurs app, whose Save runs `makeitours-agentic-commit` directly.

- **`agents/cad-compatibility-verifier.md`** — read-only subagent verifying
  the installed PyPI CAD toolchain and current project (Tier 1/2
  verification — see this repository's own `AGENTS.md`, "CAD Compatibility
  Verifier").
- **`agents/file-artifact-reviewer.md`** — read-only subagent reviewing
  generated CAD artifacts, labels, metadata, drawings, and reports.
- **`agents/file-design-maintainer.md`** — the primary agent: implements and
  validates parametric CAD design changes, semantics, labels, metadata,
  relationships, tests, and outputs.
- **`skills/cad-compatibility-verifier/`**, **`skills/file-artifact-reviewer/`**,
  **`skills/file-design-maintainer/`** — `SKILL.md` descriptions matching the
  three agents above.
- **`skills/start-ui/`**, **`skills/stop-ui/`**, **`skills/upgrade-ui/`** —
  start, stop, or rebuild-and-restart the local `python-cad` viewer, from an
  explicit user request, using the command line (runtime records under
  `.makeitours/ui-server.*`, git-ignored).
