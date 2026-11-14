"""tools/release-identity (2026-10-09 approval, project-upgrade-button): each release archive
names its own release, and each release publishes its upgrade policy."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "release-identity"
COMMIT = "a" * 40


def _tree(tmp_path: Path, minimum: object = None) -> Path:
    tree = tmp_path / "file-template-cad"
    (tree / "requirements/locks").mkdir(parents=True)
    shutil.copy(ROOT / "requirements/locks/dev-ubuntu-x86_64-py312.lock", tree / "requirements/locks/")
    (tree / ".github").mkdir()
    policy = json.loads((ROOT / ".github/release-policy.json").read_text())
    policy["minimum_supported"] = minimum
    (tree / ".github/release-policy.json").write_text(json.dumps(policy))
    return tree


def _run(tree: Path, tag: str, out: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *flags, str(tree), tag, COMMIT, str(out)], capture_output=True, text=True
    )


def _locked_cad_tools() -> str:
    lock = (ROOT / "requirements/locks/dev-ubuntu-x86_64-py312.lock").read_text()
    line = next(line for line in lock.splitlines() if line.startswith("python-cad-tools=="))
    return line.split("==")[1].split()[0]


def test_writes_the_identity_and_the_policy(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    out = tmp_path / "template-policy.json"
    assert _run(tree, "v0.1.0.40", out).returncode == 0
    identity = json.loads((tree / ".makeitours/template-release.json").read_text())
    assert identity == {
        "schema_version": 1,
        "release": "v0.1.0.40",
        "commit": COMMIT,
        "python_cad_tools": _locked_cad_tools(),
    }
    policy = json.loads(out.read_text())
    assert policy["latest"] == "v0.1.0.40" and policy["minimum_supported"] is None
    assert policy["python_cad_tools"] == identity["python_cad_tools"] and policy["message"]


def test_the_committed_policy_starts_with_no_gate() -> None:
    assert json.loads((ROOT / ".github/release-policy.json").read_text())["minimum_supported"] is None


def test_publishes_a_raised_minimum(tmp_path: Path) -> None:
    out = tmp_path / "policy.json"
    assert _run(_tree(tmp_path, "v0.1.0.38"), "v0.1.0.40", out).returncode == 0
    assert json.loads(out.read_text())["minimum_supported"] == "v0.1.0.38"


@pytest.mark.parametrize("minimum", ["latest", 38, "0.1.0.38"])
def test_refuses_a_malformed_minimum(tmp_path: Path, minimum: object) -> None:
    assert _run(_tree(tmp_path, minimum), "v0.1.0.40", tmp_path / "policy.json").returncode == 65


def test_refuses_a_malformed_tag(tmp_path: Path) -> None:
    assert _run(_tree(tmp_path), "latest", tmp_path / "policy.json").returncode == 64


def test_a_project_release_keeps_the_template_release_it_came_from(tmp_path: Path) -> None:
    """file-template-cad#32: a project's own tag is not a template release."""
    tree = _tree(tmp_path)
    record = tree / ".makeitours/template-release.json"
    record.parent.mkdir()
    committed = '{"schema_version": 1, "release": "v0.1.0.63", "commit": "' + "b" * 40 + '"}\n'
    record.write_text(committed)
    out = tmp_path / "template-policy.json"
    assert _run(tree, "v0.1.0.1", out, "--project").returncode == 0
    assert record.read_text() == committed
    assert json.loads(out.read_text())["latest"] == "v0.1.0.1"


def test_a_project_release_without_a_record_invents_none(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    assert _run(tree, "v0.1.0.1", tmp_path / "template-policy.json", "--project").returncode == 0
    assert not (tree / ".makeitours/template-release.json").exists()


def test_the_release_workflow_publishes_the_identity_and_the_policy() -> None:
    workflow = (ROOT / ".github/workflows/release-template.yml").read_text()
    assert "python3 tools/release-identity $project_flag staging/file-template-cad" in workflow
    # Only the template repository writes its own tag as the template release.
    assert (
        'if [ "$GITHUB_REPOSITORY" != "brandon-benge/file-template-cad" ]; then\n            project_flag="--project"'
        in workflow
    )
    assert "--sort=name" in workflow and "gzip -n" in workflow
    for asset in ("template-policy.json", "template-policy.json.sha256"):
        assert workflow.count(asset) >= 2, asset  # uploaded and attached to the release
