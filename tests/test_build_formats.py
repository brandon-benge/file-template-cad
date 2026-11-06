"""Format selection through CLI --format flags.

Both tests read the session's shared CLI step+ifc build (conftest.py), made with
repeated --format flags. 2026-11-06 (makeitours-data-plane#293): the separate API
step+ifc build is gone; `build_project(formats=...)` is covered by python-cad-tools'
own tests, and the CLI passes its --format flags to it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

#: What a build writes besides the selected formats.
_ALWAYS_WRITTEN = {"manifests"}


def test_build_selected_formats(cli_step_ifc_project: Path, identity) -> None:
    """A build restricted to step+ifc writes those formats and no other format directory."""
    output = cli_step_ifc_project / "generated"
    assert (output / "step" / f"{identity.stem}.step").is_file()
    assert (output / "ifc" / f"{identity.stem}.ifc").is_file()
    written = {p.name for p in output.iterdir() if p.is_dir() and any(p.rglob("*"))}
    assert written - _ALWAYS_WRITTEN <= {"step", "ifc"}, f"Unselected formats written: {written}"


def test_cli_repeated_format(cli_step_ifc_project, identity) -> None:
    """CLI build with repeated --format flags produces expected formats."""
    assert (cli_step_ifc_project / "generated" / "step" / f"{identity.stem}.step").is_file()
    assert (cli_step_ifc_project / "generated" / "ifc" / f"{identity.stem}.ifc").is_file()
    assert not (cli_step_ifc_project / "generated" / "glb").exists()
