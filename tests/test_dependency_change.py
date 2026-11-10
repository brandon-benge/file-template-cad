"""tools/dependency-change (file-template-cad#21): CI proves the locked install on macOS only
when pyproject.toml or requirements/ changed since the last commit whose checks passed."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "dependency-change"
LINUX_ONLY = ["ubuntu-24.04"]
WITH_MACOS = ["ubuntu-24.04", "macos-latest"]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def _commit(repo: Path, files: dict[str, str]) -> str:
    for relative, text in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "change")
    return _git(repo, "rev-parse", "HEAD")


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "project"
    repo.mkdir()
    _git(repo, "init", "-q")
    base = _commit(
        repo,
        {"pyproject.toml": "[project]\n", "requirements/locks/dev.lock": "a==1\n", "model.py": "x = 1\n"},
    )
    return repo, base


def _runners(repo: Path, *args: str) -> list[str]:
    result = subprocess.run([sys.executable, str(TOOL), *args], cwd=repo, capture_output=True, text=True, check=True)
    runners = json.loads(result.stdout)
    assert isinstance(runners, list)
    return runners


def test_a_design_change_skips_macos(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    _commit(repo, {"model.py": "x = 2\n", "models/part.py": "y = 1\n"})
    assert _runners(repo, base) == LINUX_ONLY


def test_a_lock_change_runs_macos(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    _commit(repo, {"requirements/locks/dev.lock": "a==2\n"})
    assert _runners(repo, base) == WITH_MACOS


def test_a_pyproject_change_runs_macos(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    _commit(repo, {"pyproject.toml": "[project]\nname = 'x'\n"})
    assert _runners(repo, base) == WITH_MACOS


def test_a_change_in_an_earlier_unchecked_commit_still_runs_macos(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    _commit(repo, {"requirements/locks/dev.lock": "a==2\n"})
    _commit(repo, {"model.py": "x = 3\n"})
    assert _runners(repo, base) == WITH_MACOS


def test_no_base_or_an_unknown_base_runs_macos(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    assert _runners(repo) == WITH_MACOS
    assert _runners(repo, "") == WITH_MACOS
    assert _runners(repo, "f" * 40) == WITH_MACOS
