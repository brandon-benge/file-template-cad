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

**`locks/dev-ubuntu-x86_64-py312.lock` is also the MakeItOurs release lock.**
The hosted pipeline's Build Agent (makeitours-data-plane D105) runs its
`reproducibility` check against exactly this file and fails a release unless
every pin equals the version installed in the released
`makeitours-agentic` sandbox image. It was regenerated on 2026-09-24 from that
image's x86_64 toolchain (owner decision: the lock follows the image, so it
must be regenerated whenever the image's toolchain changes). To regenerate:
export the image's versions (`docker run --platform linux/amd64 <image> pip
list --format=freeze`, minus `pip`, `setuptools`, `wheel` and
`makeitours-agentic`), write them into this file as the starting pins, then in
a `python:3.12-slim-bookworm` linux/amd64 container with `pip<26.2` and
pip-tools run
`CUSTOM_COMPILE_COMMAND="pip-compile --extra=dev --generate-hashes --output-file=requirements/locks/dev-ubuntu-x86_64-py312.lock pyproject.toml" pip-compile --extra=dev --generate-hashes --output-file=requirements/locks/dev-ubuntu-x86_64-py312.lock pyproject.toml`
(pip-compile keeps existing pins that satisfy `pyproject.toml`). CI's own
regeneration also keeps these pins, since it starts from the committed file.

If this directory — or the loose top-level files, or `locks/` — is removed or
reorganized, this description no longer applies to whatever replaced it.
