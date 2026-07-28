"""Format selection: programmatic API and CLI --format flags.

test_cli_repeated_format uses a shared module-scoped step+ifc build (~48 s).
test_build_selected_formats tests the programmatic API on its own fresh copy.
With pytest-xdist --dist loadscope this file runs on its own worker (~83 s).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import _cli, _copy_project
from python_cad_tools.build import BuildOptions, build_project

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
def step_ifc_project(tmp_path_factory: pytest.TempPathFactory, repo_root: Path) -> Path:
    """Step+ifc build created once for this module."""
    dest = tmp_path_factory.mktemp("fmt_step_ifc")
    _copy_project(repo_root, dest)
    result = _cli("build", "--format", "step", "--format", "ifc", cwd=dest)
    assert result.returncode == 0, f"CLI build failed: stderr={result.stderr}"
    return dest


def test_build_selected_formats(copied_project) -> None:
    """Programmatic build_project with restricted formats (step+ifc only)."""
    result = build_project(BuildOptions(project_root=copied_project, formats=("step", "ifc")))
    output = result.output_root
    assert (output / "step" / "FileTemplate.step").is_file()
    assert (output / "ifc" / "FileTemplate.ifc").is_file()
    assert not (output / "glb").exists() or not list((output / "glb").rglob("*"))


def test_cli_repeated_format(step_ifc_project) -> None:
    """CLI build with repeated --format flags produces expected formats."""
    assert (step_ifc_project / "generated" / "step" / "FileTemplate.step").is_file()
    assert not (step_ifc_project / "generated" / "glb").exists()
