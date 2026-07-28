from __future__ import annotations

import shutil
import subprocess
import sys
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
