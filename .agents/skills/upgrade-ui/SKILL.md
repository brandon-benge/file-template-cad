---
name: upgrade-ui
description: Upgrade the current CAD project installation and launch the rebuilt local viewer with the upgrade-ui tool or its command-line fallback. Use when the user explicitly asks to upgrade, refresh, or reinstall the local project and start its UI, including from Claude or OpenAI environments without OpenCode tools.
---

# Upgrade UI

Act only after an explicit upgrade request. Use the requested port, or port
8080 by default. Prefer the `upgrade-ui` tool when it is available. When
OpenCode tools are not available, run this sequence from the repository root:

```text
.venv/bin/pip install --upgrade .
.venv/bin/python-cad --version
.venv/bin/python-cad clean
.venv/bin/python-cad serve --build --port 8080
```

Report the installed version and viewer URL. This operational tool upgrades the
active environment; it does not edit `pyproject.toml`, regenerate dependency
locks, select dependency versions, commit changes, or imply E2E verification.
Keep the final command in a managed long-running terminal session so it can be
stopped with Ctrl-C. Use `python-cad-tools-upgrader` for a repository
dependency-version change.
