# requirements/

Infrastructure (see `tests/README.md` for what that means). Split into two
generations that have diverged:

- **`locks/dev-{macos-arm64,ubuntu-x86_64}-py{312,313}.lock`** — the active
  ones. `.github/workflows/ci.yml`'s `locked-install` job regenerates each
  with `pip-compile --extra=dev --generate-hashes` and installs from it with
  `pip install --require-hashes`, so these are what CI (and a reproducible
  dev install) actually depend on. Only ever regenerated for the
  platform/version a workflow run actually built and verified against — check
  individual commit messages; they don't all move together.
- **The eight loose `dev-*.lock` / `runtime-*.lock` files directly under
  `requirements/`** — from this template's initial commit, never regenerated
  since (nothing in CI or any script references them), and now stale relative
  to `locks/` (e.g. an older pinned `python-cad-tools`). Read `locks/` for the
  real, current pins.

If this directory — or the loose top-level files, or `locks/` — is removed or
reorganized, this description no longer applies to whatever replaced it.
