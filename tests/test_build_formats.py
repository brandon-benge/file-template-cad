"""Format selection: programmatic API and CLI --format flags.

Both tests read the session's shared step+ifc builds (conftest.py): one made
through the API, one through the CLI with repeated --format flags.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration]


def test_build_selected_formats(api_step_ifc_project, identity) -> None:
    """Programmatic build_project with restricted formats (step+ifc only)."""
    output = api_step_ifc_project / "generated"
    assert (output / "step" / f"{identity.stem}.step").is_file()
    assert (output / "ifc" / f"{identity.stem}.ifc").is_file()
    assert not (output / "glb").exists() or not list((output / "glb").rglob("*"))


def test_cli_repeated_format(cli_step_ifc_project, identity) -> None:
    """CLI build with repeated --format flags produces expected formats."""
    assert (cli_step_ifc_project / "generated" / "step" / f"{identity.stem}.step").is_file()
    assert (cli_step_ifc_project / "generated" / "ifc" / f"{identity.stem}.ifc").is_file()
    assert not (cli_step_ifc_project / "generated" / "glb").exists()
