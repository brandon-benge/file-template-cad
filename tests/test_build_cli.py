"""Section 12.5: CLI end-to-end.

CLI tests use a shared module-scoped step-only build. With pytest-xdist
--dist loadscope, this file runs on one worker in parallel with other
build test files.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import _cli, _copy_project

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
def cli_built_project(tmp_path_factory: pytest.TempPathFactory, repo_root: Path) -> Path:
    """CLI build with step only, created once for this module."""
    dest = tmp_path_factory.mktemp("cli_project")
    _copy_project(repo_root, dest)
    result = _cli("build", "--format", "step", cwd=dest)
    assert result.returncode == 0, f"CLI build failed: stderr={result.stderr}"
    return dest


def test_cli_build_from_root(cli_built_project) -> None:
    """CLI build (step-only, shared fixture)."""
    assert (cli_built_project / "generated" / "step" / "FileTemplate.step").is_file()


def test_cli_build_from_path_with_spaces(copied_project_with_spaces) -> None:
    """CLI build in a path containing spaces (own build, step-only)."""
    result = _cli("build", "--format", "step", cwd=copied_project_with_spaces)
    assert result.returncode == 0, f"CLI build failed in path with spaces: {result.stderr}"
    assert (copied_project_with_spaces / "generated" / "step" / "FileTemplate.step").is_file()


def test_cli_validate(copied_project) -> None:
    """CLI validate on a clean (never-built) project."""
    result = _cli("validate", cwd=copied_project)
    assert result.returncode == 0, f"CLI validate failed: {result.stderr}"
    assert '"status":"ok"' in result.stdout


def test_cli_clean(copied_project) -> None:
    """CLI build (step-only) then clean on a fresh project copy."""
    _cli("build", "--format", "step", cwd=copied_project)
    assert (copied_project / "generated" / "step" / "FileTemplate.step").is_file()
    result = _cli("clean", cwd=copied_project)
    assert result.returncode == 0, f"CLI clean failed: {result.stderr}"
    assert not (copied_project / "generated" / "step").exists()
