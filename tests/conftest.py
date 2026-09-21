from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

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
def session_project(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    dest = tmp_path_factory.mktemp("session_project")
    _copy_project(repo_root, dest)
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
def identity(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> ProjectIdentity:
    """The names this project declares, read from its own build output and source.

    These tests ship with the template and run in every project cut from it, and a
    project renames the model id, artifact stem and provider id. Read them from the
    project instead of typing the template's values: the model id and artifact stem
    from a step-only build's design manifest, the provider id from the project's
    own drawing_annotations.PROVIDER_ID.
    """
    work = tmp_path_factory.mktemp("identity") / "project"
    _copy_project(repo_root, work)
    result = _cli("build", "--format", "step", cwd=work)
    assert result.returncode == 0, f"identity build failed: {result.stderr}"
    design = json.loads((work / "generated" / "manifests" / "design-manifest.json").read_text())
    spec = importlib.util.spec_from_file_location("_identity_drawing_annotations", work / "drawing_annotations.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return ProjectIdentity(design["model_id"], design["artifact_stem"], module.PROVIDER_ID)
