# .agents/

Infrastructure (see `tests/README.md`): the canonical source for this
project's OpenCode-compatible subagents and skills. `.opencode/agents` and
`.opencode/skills` symlink here so OpenCode's own expected layout resolves to
the same definitions.

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
- **`skills/save/`** — commit already-verified changes, only on an explicit
  user request to commit/save; the `/autocommit` command
  (`.opencode/commands/autocommit.md`) loads this skill.
- **`skills/start-ui/`**, **`skills/stop-ui/`**, **`skills/upgrade-ui/`** —
  start, stop, or rebuild-and-restart the local `python-cad` viewer, from an
  explicit user request, with a command-line fallback for environments
  without OpenCode's native tools.
