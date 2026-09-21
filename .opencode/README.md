# .opencode/

Infrastructure (see `tools/README.md`): configuration and native tools for
the OpenCode CLI agent runtime this project's Git-triggered audit workflow
(`tools/run-git-opencode-audit`) drives.

- **`agents`**, **`skills`** — symlinks to `../.agents/agents` and
  `../.agents/skills`, so OpenCode's own expected layout resolves to the same
  agent/skill definitions documented in `.agents/README.md`.
- **`commands/autocommit.md`** — the `/autocommit` slash command: loads the
  `save` skill and commits already-verified changes via the native
  `specrepo-autocommit` tool, only when the user explicitly asked for a
  commit.
- **`tools/specrepo-autocommit.js`** (+ `.py`) — the native tool
  `autocommit.md` calls; the JS file is a thin OpenCode `tool()` wrapper
  around the Python CLI.
- **`tools/start-ui.js`**, **`stop-ui.js`**, **`upgrade-ui.js`** — native
  tools behind the `start-ui`/`stop-ui`/`upgrade-ui` skills: manage a local
  `python-cad` viewer process (start/stop/rebuild-and-restart) via a tracked
  PID file.
- **`package.json`** — pins `@opencode-ai/plugin`, the SDK the native tools
  above import. The exact pinned version can differ briefly from a sister
  repo's until `tools/reconcile-infrastructure` is next run — it isn't kept
  in sync automatically. `node_modules/`, the lockfile, and `.gitignore`
  itself are gitignored (`.opencode/.gitignore`) — a local install, not
  repository content.

If this directory is removed (e.g. OpenCode support dropped), this file no
longer applies.
