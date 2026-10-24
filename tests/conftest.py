from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _copy_project(src: Path, dest: Path) -> None:
    ignores = {
        "generated",
        ".venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".mypy",
        ".back_agents",
        ".back_opencode",
        "node_modules",
        ".tools",
        "viewer",
        "backup",
        ".claude",
        ".codex",
        ".github",
        "site",
    }
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        name = item.name
        if name in ignores or name.startswith("."):
            continue
        if item.is_dir():
            shutil.copytree(item, dest / name, symlinks=False, ignore=shutil.ignore_patterns("__pycache__"))
        elif item.is_file():
            shutil.copy2(item, dest / name)


@pytest.fixture
def copied_project(repo_root: Path, tmp_path: Path) -> Path:
    dest = tmp_path / "project"
    _copy_project(repo_root, dest)
    return dest


@pytest.fixture
def copied_project_with_spaces(repo_root: Path, tmp_path: Path) -> Path:
    dest = tmp_path / "my project with spaces" / "file"
    _copy_project(repo_root, dest)
    return dest


@pytest.fixture(scope="session")
def session_project(full_build: FullBuild) -> Path:
    """A project with a full build in `generated/`, shared read-only by the viewer tests."""
    return full_build.project


# ── Shared builds ────────────────────────────────────────────────────────────
#
# Each build reruns the whole model, which is the slow part of this suite on a
# hosted sandbox (2026-10-24: about 10 builds took 3.5–5 minutes on half a CPU,
# and the suite runs twice per change). Tests share three builds instead, each
# made once per session and never modified: a full build through the API, a
# step+ifc build through the API, and a step+ifc build through the CLI in a path
# with spaces. A test that changes a project works on a copy.


@dataclass(frozen=True)
class FullBuild:
    project: Path
    result: Any


@pytest.fixture(scope="session")
def full_build(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> FullBuild:
    """Every default format, built once through the API."""
    from python_cad_tools.build import BuildOptions, build_project

    dest = tmp_path_factory.mktemp("full_build") / "project"
    _copy_project(repo_root, dest)
    return FullBuild(dest, build_project(BuildOptions(project_root=dest)))


STEP_IFC = ("step", "ifc")


@pytest.fixture(scope="session")
def api_step_ifc_project(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Only step and ifc, built once through the API (`build_project(formats=...)`)."""
    from python_cad_tools.build import BuildOptions, build_project

    dest = tmp_path_factory.mktemp("api_step_ifc") / "project"
    _copy_project(repo_root, dest)
    build_project(BuildOptions(project_root=dest, formats=STEP_IFC))  # type: ignore[arg-type]
    return dest


@pytest.fixture(scope="session")
def cli_step_ifc_project(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Only step and ifc, built once through the CLI with repeated --format flags, in a path
    that contains spaces."""
    dest = tmp_path_factory.mktemp("cli_step_ifc") / "my project with spaces" / "file"
    _copy_project(repo_root, dest)
    result = _cli("build", "--format", "step", "--format", "ifc", cwd=dest)
    assert result.returncode == 0, f"CLI build failed: stderr={result.stderr}"
    return dest


def copy_built_project(built: Path, dest: Path) -> Path:
    """A writable copy of a built project, `generated/` included."""
    shutil.copytree(built, dest, symlinks=False)
    return dest


# ── CLI helper (shared across test files) ────────────────────────────────────


def _cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "python_cad_tools.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@dataclass(frozen=True)
class ProjectIdentity:
    model_id: str
    stem: str
    provider_id: str


@pytest.fixture(scope="session")
def identity(cli_step_ifc_project: Path) -> ProjectIdentity:
    """The names this project declares, read from its own build output and source.

    These tests ship with the template and run in every project cut from it, and a
    project renames the model id, artifact stem and provider id. Read them from the
    project instead of typing the template's values: the model id and artifact stem
    from the shared CLI build's design manifest, the provider id from the project's
    own drawing_annotations.PROVIDER_ID.
    """
    work = cli_step_ifc_project
    design = json.loads((work / "generated" / "manifests" / "design-manifest.json").read_text())
    spec = importlib.util.spec_from_file_location("_identity_drawing_annotations", work / "drawing_annotations.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return ProjectIdentity(design["model_id"], design["artifact_stem"], module.PROVIDER_ID)
