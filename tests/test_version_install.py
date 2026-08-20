"""Hermetic tests for the tools/install-selected-python-cad-tools runner.

These tests exercise the runner's lockfile reconciliation with --dry-run, a
fixture lockfile, a fixture pyproject.toml, and a fake PyPI JSON served from a
file:// URL. No network access, package installation, or project build occurs.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNNER = PROJECT_ROOT / "tools" / "install-selected-python-cad-tools"
VERSION_VAR = "MAKEITOURS_TEST_CAD_TOOLS_VERSION"

LOCK_TEXT = """\
build123d==0.11.1 \\
    --hash=sha256:1111111111111111111111111111111111111111111111111111111111111111 \\
    --hash=sha256:2222222222222222222222222222222222222222222222222222222222222222
    # via file-template-cad (pyproject.toml)
numpy==2.3.0 \\
    --hash=sha256:3333333333333333333333333333333333333333333333333333333333333333
    # via build123d
python-cad-tools==0.1.9 \\
    --hash=sha256:4444444444444444444444444444444444444444444444444444444444444444 \\
    --hash=sha256:5555555555555555555555555555555555555555555555555555555555555555
    # via file-template-cad (pyproject.toml)
trimesh==4.12.0 \\
    --hash=sha256:6666666666666666666666666666666666666666666666666666666666666666
    # via file-template-cad (pyproject.toml)
"""

PYPROJECT_TEXT = """\
[project]
name = "fixture-cad"
version = "0.1.0"
requires-python = ">=3.12,<3.14"
dependencies = [
  "python-cad-tools>=0.1.7,<0.2",
  "build123d>=0.11.1,<0.12",
  "trimesh>=4.12,<5",
]
"""


def _make_fixture(tmp_path: Path, version: str, digests: list[str]) -> Path:
    """Create a fixture project directory with lock, pyproject, and fake PyPI."""
    root = tmp_path / "fixture"
    root.mkdir(parents=True, exist_ok=True)
    (root / "lock.txt").write_text(LOCK_TEXT, encoding="utf-8")
    (root / "pyproject.toml").write_text(PYPROJECT_TEXT, encoding="utf-8")

    pypi_dir = root / "pypi" / "python-cad-tools" / version
    pypi_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "info": {"version": version},
        "urls": [
            {
                "filename": f"python_cad_tools-{version}-py3-none-any.whl",
                "digests": {"sha256": digests[0]},
            },
            {
                "filename": f"python-cad-tools-{version}.tar.gz",
                "digests": {"sha256": digests[1]},
            },
        ],
    }
    (pypi_dir / "json").write_text(json.dumps(payload), encoding="utf-8")
    return root


def _run_runner(root: Path, *extra_args: str, version: str | None = None):
    env = dict(os.environ)
    if version is None:
        env.pop(VERSION_VAR, None)
    else:
        env[VERSION_VAR] = version
    args = [
        sys.executable,
        str(RUNNER),
        "--lock",
        str(root / "lock.txt"),
        "--pyproject",
        str(root / "pyproject.toml"),
        "--pypi-json-base",
        f"file://{root}",
        "--version",
        VERSION_VAR,
        *extra_args,
    ]
    return subprocess.run(args, capture_output=True, text=True, env=env)


def test_unset_variable_keeps_committed_lock(tmp_path):
    root = _make_fixture(tmp_path, "0.1.10", ["aaaa", "bbbb"])
    result = _run_runner(root, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert result.stdout == LOCK_TEXT


def test_selected_version_replaces_pin_block_and_preserves_others(tmp_path):
    root = _make_fixture(tmp_path, "0.1.10", ["aaaa1111", "bbbb2222"])
    result = _run_runner(root, "--dry-run", version="0.1.10")
    assert result.returncode == 0, result.stderr
    assert "python-cad-tools==0.1.10" in result.stdout
    assert "--hash=sha256:aaaa1111" in result.stdout
    assert "--hash=sha256:bbbb2222" in result.stdout
    # The old pin and hashes are gone.
    assert "python-cad-tools==0.1.9" not in result.stdout
    assert "--hash=sha256:4444444444444444444444444444444444444444444444444444444444444444" not in result.stdout
    # Other packages and their hashes are untouched.
    assert "build123d==0.11.1" in result.stdout
    assert "--hash=sha256:1111111111111111111111111111111111111111111111111111111111111111" in result.stdout
    assert "trimesh==4.12.0" in result.stdout
    assert "--hash=sha256:6666666666666666666666666666666666666666666666666666666666666666" in result.stdout
    # The "# via" comments are preserved.
    assert "# via file-template-cad (pyproject.toml)" in result.stdout


def test_output_writes_reconciled_requirements(tmp_path):
    root = _make_fixture(tmp_path, "0.1.10", ["aaaa1111", "bbbb2222"])
    output = tmp_path / "out.lock"
    result = _run_runner(root, "--output", str(output), version="0.1.10")
    assert result.returncode == 0, result.stderr
    assert "python-cad-tools==0.1.10" in output.read_text(encoding="utf-8")


def test_invalid_version_fails_fast(tmp_path):
    root = _make_fixture(tmp_path, "0.1.10", ["aaaa", "bbbb"])
    result = _run_runner(root, "--dry-run", version="not-a-version")
    assert result.returncode != 0
    assert "invalid python-cad-tools version" in result.stderr


def test_absent_version_fails_fast(tmp_path):
    root = _make_fixture(tmp_path, "0.1.10", ["aaaa", "bbbb"])
    # 0.1.11 is within the declared constraint but has no PyPI JSON fixture.
    result = _run_runner(root, "--dry-run", version="0.1.11")
    assert result.returncode != 0
    assert "was not found on PyPI" in result.stderr


def test_prerelease_version_fails_fast(tmp_path):
    root = _make_fixture(tmp_path, "0.1.10", ["aaaa", "bbbb"])
    result = _run_runner(root, "--dry-run", version="0.1.10rc1")
    assert result.returncode != 0
    assert "must be a stable release" in result.stderr


def test_out_of_constraint_version_fails_fast(tmp_path):
    root = _make_fixture(tmp_path, "0.1.10", ["aaaa", "bbbb"])
    result = _run_runner(root, "--dry-run", version="0.5.0")
    assert result.returncode != 0
    assert "does not satisfy declared constraint" in result.stderr


def test_install_command_uses_require_hashes():
    runner_text = RUNNER.read_text(encoding="utf-8")
    assert "--require-hashes" in runner_text
    assert '"-r", str(' in runner_text or "-r" in runner_text
