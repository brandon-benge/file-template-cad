# .vscode/

Infrastructure (see `tests/README.md`). Currently just `settings.json`,
disabling VS Code's automatic Python virtual-environment activation in the
integrated terminal (`python.terminal.activateEnvironment: false`) so a
terminal here matches whatever environment this project's own tooling
(`ruff`, `mypy`, `pytest`, `python-cad`) already expects, rather than VS Code
silently switching it.
