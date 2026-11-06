from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from collections.abc import Iterator
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
# and the suite runs twice per change). Tests share two builds instead, each
# made once per session and never modified: a full build through the API, and a
# step+ifc build through the CLI in a path with spaces. Together they are the
# determinism proof (test_build_determinism.py). A test that changes a project
# works on a copy.
#
# 2026-11-06 (makeitours-data-plane#293): when a session uses both builds, the
# CLI build starts as a subprocess before the API build runs in this process, so
# the two run at the same time on a container with more than one core (Benge:
# 57 s for both on two cores, 106 s one after the other).


@dataclass(frozen=True)
class FullBuild:
    project: Path
    result: Any


STEP_IFC = ("step", "ifc")
_CLI_STEP_IFC_ARGS = ("build", "--format", "step", "--format", "ifc")


@dataclass
class _CliBuild:
    project: Path
    process: subprocess.Popen[str] | None = None
    finished: bool = False

    def wait(self) -> Path:
        if not self.finished:
            if self.process is None:
                result = _cli(*_CLI_STEP_IFC_ARGS, cwd=self.project)
                returncode, stderr = result.returncode, result.stderr
            else:
                _, stderr = self.process.communicate()
                returncode = self.process.returncode
            assert returncode == 0, f"CLI build failed: stderr={stderr}"
            self.finished = True
        return self.project


#: 2026-11-06 (makeitours-data-plane#293): the test that first asks for a shared build carries
#: that build's time, and with both builds running together it carries both. The default
#: per-test limit (120 s, pyproject.toml) failed Benge's release check on a 2-vCPU staging
#: container, where the two builds share the cores, while each build alone fits. Tests that use
#: a shared build get this limit instead; every other test keeps the default.
SHARED_BUILD_TIMEOUT_SECONDS = 600
_SHARED_BUILD_FIXTURES = ("full_build", "cli_step_ifc_project")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        fixtures = getattr(item, "fixturenames", ())
        if any(name in fixtures for name in _SHARED_BUILD_FIXTURES) and item.get_closest_marker("timeout") is None:
            item.add_marker(pytest.mark.timeout(SHARED_BUILD_TIMEOUT_SECONDS))


def _session_uses(session: pytest.Session, fixture: str) -> bool:
    return any(fixture in getattr(item, "fixturenames", ()) for item in session.items)


@pytest.fixture(scope="session")
def _cli_build(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Iterator[_CliBuild]:
    dest = tmp_path_factory.mktemp("cli_step_ifc") / "my project with spaces" / "file"
    _copy_project(repo_root, dest)
    build = _CliBuild(dest)
    yield build
    if build.process is not None and build.process.poll() is None:
        build.process.kill()
        build.process.communicate()


@pytest.fixture(scope="session")
def full_build(request: pytest.FixtureRequest, repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> FullBuild:
    """Every default format, built once through the API.

    When the session also uses the CLI build, that build is started first and runs
    alongside this one.
    """
    from python_cad_tools.build import BuildOptions, build_project

    if _session_uses(request.session, "cli_step_ifc_project"):
        cli = request.getfixturevalue("_cli_build")
        if cli.process is None and not cli.finished:
            cli.process = subprocess.Popen(
                [sys.executable, "-m", "python_cad_tools.cli", *_CLI_STEP_IFC_ARGS],
                cwd=cli.project,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
    dest = tmp_path_factory.mktemp("full_build") / "project"
    _copy_project(repo_root, dest)
    return FullBuild(dest, build_project(BuildOptions(project_root=dest)))


@pytest.fixture(scope="session")
def cli_step_ifc_project(request: pytest.FixtureRequest, _cli_build: _CliBuild) -> Path:
    """Only step and ifc, built once through the CLI with repeated --format flags, in a path
    that contains spaces. Waits for the build `full_build` started (whichever a test asks
    for first, both run together), or builds it here when the session needs no full build."""
    if _session_uses(request.session, "full_build"):
        request.getfixturevalue("full_build")
    return _cli_build.wait()


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
