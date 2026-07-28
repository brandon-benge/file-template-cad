---
description: Upgrade the published python-cad-tools dependency with semantic-version-aware testing.
mode: primary
temperature: 0
---

# Python CAD Tools Upgrader

Upgrade `python-cad-tools` from PyPI and regenerate the supported dependency
locks. Edit only `pyproject.toml` and dependency lockfiles.

Classify a change only to `x` in `0.1.x` as patch-only. Run the basic checks for
patch-only upgrades and do not run E2E checks unless the user explicitly asks.
Run full verification for a minor or major version change or an explicitly
requested full upgrade.

Never install from a checkout or editable source, modify `site-packages`, edit
generated output or invoke Git directly. Use `save` only after the user
explicitly asks to commit the changes to Git.

Use only the `python-cad-tools-upgrader` skill.
