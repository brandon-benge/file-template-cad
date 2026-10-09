"""tools/reconcile-infrastructure --plan / --source (2026-10-09 approval, project-upgrade-button).

Upgrade Project computes the change as a plan first. Every case in
tests/fixtures/reconcile-plans.json (shared with makeitours-app's InfrastructurePlan) must
plan the same against a git checkout and an extracted release directory, `--plan` must write
nothing, and applying the plan must give the planned result without touching design files.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "reconcile-infrastructure"
CASES = json.loads((ROOT / "tests/fixtures/reconcile-plans.json").read_text())["cases"]


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def _git_tree(root: Path, files: dict[str, str]) -> Path:
    root.mkdir()
    _write(root, files)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A", "-f"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "seed"],
        check=True,
    )
    return root


def _run(project: Path, template: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *flags, str(template)], cwd=project, capture_output=True, text=True, check=True
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_plan_matches_the_shared_fixture_for_a_checkout_and_a_release_tree(tmp_path: Path, case: dict) -> None:
    project = _git_tree(tmp_path / "project", case["project"])
    checkout = _git_tree(tmp_path / "template-checkout", case["template"])
    release = tmp_path / "template-release"
    release.mkdir()
    _write(release, case["template"])
    before = _snapshot(project)

    from_checkout = json.loads(_run(project, checkout, "--plan").stdout)
    from_release = json.loads(_run(project, release, "--plan", "--source").stdout)

    assert from_checkout == {"schema_version": 1, "changes": case["expected"]}
    assert from_release == from_checkout
    assert _snapshot(project) == before, "--plan must write nothing"


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_applying_the_plan_leaves_nothing_to_do_and_design_files_untouched(tmp_path: Path, case: dict) -> None:
    project = _git_tree(tmp_path / "project", case["project"])
    release = tmp_path / "template-release"
    release.mkdir()
    _write(release, case["template"])
    design = {
        path: content
        for path, content in case["project"].items()
        if path in ("config.py", "model.py", "drawing_annotations.py") or (path.startswith("models/") and path.endswith(".py"))
    }

    _run(project, release, "--source")

    for path, content in design.items():
        assert (project / path).read_text() == content, path
    for path, content in case.get("expected_contents", {}).items():
        assert (project / path).read_text() == content, path
    removed = [change["path"] for change in case["expected"] if change["action"] == "remove"]
    assert all(not (project / path).exists() for path in removed)
    # Commit the applied tree (as an upgrade would), then nothing is left to plan.
    subprocess.run(["git", "-C", str(project), "add", "-A", "-f"], check=True)
    subprocess.run(
        ["git", "-C", str(project), "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "upgrade", "--allow-empty"],
        check=True,
    )
    assert json.loads(_run(project, release, "--plan", "--source").stdout)["changes"] == []


def test_a_template_checkout_never_removes_the_release_identity(tmp_path: Path) -> None:
    case = CASES[0]
    project = _git_tree(
        tmp_path / "project",
        {**case["project"], ".makeitours/template-release.json": '{"schema_version": 1, "release": "v0.1.0.30"}\n'},
    )
    checkout = _git_tree(tmp_path / "template-checkout", case["template"])
    assert json.loads(_run(project, checkout, "--plan").stdout)["changes"] == []
