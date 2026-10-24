"""Section 12.5: CLI end-to-end.

The build tests read the session's shared CLI build (conftest.py), made with
repeated --format flags in a path containing spaces; `clean` runs on a copy of
it, so no test here builds the model again.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import _cli, copy_built_project

pytestmark = [pytest.mark.integration]


def test_cli_build_from_root(cli_step_ifc_project, identity) -> None:
    """CLI build run from the project root."""
    assert (cli_step_ifc_project / "generated" / "step" / f"{identity.stem}.step").is_file()


def test_cli_build_from_path_with_spaces(cli_step_ifc_project, identity) -> None:
    """The shared CLI build ran in a path containing spaces."""
    assert " " in str(cli_step_ifc_project)
    assert (cli_step_ifc_project / "generated" / "step" / f"{identity.stem}.step").is_file()


def test_cli_validate(copied_project) -> None:
    """CLI validate on a clean (never-built) project."""
    result = _cli("validate", cwd=copied_project)
    assert result.returncode == 0, f"CLI validate failed: {result.stderr}"
    assert '"status":"ok"' in result.stdout


def test_cli_clean(cli_step_ifc_project, tmp_path: Path, identity) -> None:
    """CLI clean removes a built project's generated output (on a copy of the shared build)."""
    project = copy_built_project(cli_step_ifc_project, tmp_path / "built copy")
    assert (project / "generated" / "step" / f"{identity.stem}.step").is_file()
    result = _cli("clean", cwd=project)
    assert result.returncode == 0, f"CLI clean failed: {result.stderr}"
    assert not (project / "generated" / "step").exists()
