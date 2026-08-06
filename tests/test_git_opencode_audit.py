"""Focused transaction tests for the Git-triggered OpenCode audit runner."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import TypedDict

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNNER = PROJECT_ROOT / "tools" / "run-git-opencode-audit"


class Transaction(TypedDict):
    checkout: Path
    remote: Path
    artifacts: Path
    trigger: Path
    env: dict[str, str]
    start: str


def run(*args: str | Path, cwd: Path, env: dict[str, str] | None = None, check: bool = True):
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        check=check,
        text=True,
        capture_output=True,
    )


@pytest.fixture
def transaction(tmp_path: Path) -> Transaction:
    if shutil.which("jq") is None:
        pytest.skip("jq is required by the audit runner")

    remote = tmp_path / "origin.git"
    checkout = tmp_path / "checkout"
    tools = tmp_path / "bin"
    artifacts = tmp_path / "artifacts"
    trigger = tmp_path / "trigger.json"
    validator = tools / "validator"
    opencode = tools / "opencode"

    run("git", "init", "--bare", remote, cwd=tmp_path)
    run("git", "init", "-b", "main", checkout, cwd=tmp_path)
    run("git", "config", "user.name", "Test Runner", cwd=checkout)
    run("git", "config", "user.email", "runner@example.com", cwd=checkout)
    (checkout / "tracked.txt").write_text("original\n")
    (checkout / "config.py").write_text("original = True\n")
    run("git", "add", "tracked.txt", "config.py", cwd=checkout)
    run("git", "commit", "-m", "initial", cwd=checkout)
    run("git", "remote", "add", "origin", remote, cwd=checkout)
    run("git", "push", "-u", "origin", "main", cwd=checkout)

    tools.mkdir()
    opencode.write_text(
        """#!/usr/bin/env bash
set -eu
if test "${1:-}" = "--version"; then
  echo "1.15.2"
  exit 0
fi
printf '%s\\n' '{"type":"message","text":"safe event"}'
printf '%s\\n' "stderr ${OPENCODE_API_KEY:-}" >&2
case "${AICAD_TEST_OPENCODE_MODE:-nochange}" in
  fail) exit 7 ;;
  change) printf '%s\\n' changed > config.py ;;
  policy) printf '%s\\n' forbidden > forbidden.txt ;;
  commit)
    printf '%s\\n' committed > committed.txt
    git add committed.txt
    git commit -m "unexpected opencode commit" >/dev/null
    ;;
esac
"""
    )
    validator.write_text(
        """#!/usr/bin/env bash
exit "${AICAD_TEST_VALIDATION_EXIT:-0}"
"""
    )
    opencode.chmod(0o755)
    validator.chmod(0o755)
    trigger.write_text(
        json.dumps(
            {
                "event_name": "issues",
                "repository": "owner/repository",
                "repository_id": "123",
                "workflow": "opencode",
                "run_id": "100",
                "run_attempt": "1",
                "actor": "owner",
                "ref": "refs/heads/main",
                "trigger_sha": "unused",
                "issue": {"number": 1, "title": "Test", "body": "Test request"},
                "comment": None,
            }
        )
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{tools}{os.pathsep}{env['PATH']}",
            "OPENCODE_MODEL": "test/model",
            "OPENCODE_AGENT": "test-agent",
            "OPENCODE_API_KEY": "secret-test-value",
            "AICAD_VALIDATION_EXECUTABLE": str(validator),
            "AICAD_FAILURE_ARTIFACT_DIR": str(artifacts),
            "RUNNER_TEMP": str(tmp_path),
        }
    )
    start = run("git", "rev-parse", "HEAD", cwd=checkout).stdout.strip()
    return {
        "checkout": checkout,
        "remote": remote,
        "artifacts": artifacts,
        "trigger": trigger,
        "env": env,
        "start": start,
    }


def execute(transaction: Transaction, **updates: str):
    env = dict(transaction["env"])
    env.update(updates)
    return run(
        RUNNER,
        transaction["trigger"],
        cwd=transaction["checkout"],
        env=env,
        check=False,
    )


def heads(transaction: Transaction) -> tuple[str, str]:
    local = run("git", "rev-parse", "HEAD", cwd=transaction["checkout"]).stdout.strip()
    remote = run(
        "git", "--git-dir", transaction["remote"], "rev-parse", "refs/heads/main", cwd=transaction["checkout"]
    ).stdout.strip()
    return local, remote


@pytest.mark.parametrize(
    ("environment", "stage", "exit_code"),
    [
        ({"AICAD_TEST_OPENCODE_MODE": "fail"}, "opencode", 7),
        ({"AICAD_TEST_OPENCODE_MODE": "change", "AICAD_TEST_VALIDATION_EXIT": "9"}, "validation", 9),
        ({"AICAD_TEST_OPENCODE_MODE": "commit"}, "unexpected_commit", 1),
        ({"AICAD_TEST_OPENCODE_MODE": "policy"}, "policy", 1),
    ],
)
def test_failure_does_not_commit_or_push(
    transaction: Transaction, environment: dict[str, str], stage: str, exit_code: int
):
    result = execute(transaction, **environment)

    assert result.returncode == exit_code
    assert heads(transaction) == (transaction["start"], transaction["start"])
    assert not (transaction["checkout"] / ".aicad" / "audit" / "v1" / "100-1").exists()
    artifact = transaction["artifacts"] / "100-1"
    manifest = json.loads((artifact / "run.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["failure_stage"] == stage
    assert "secret-test-value" not in (artifact / "stderr.log").read_text()
    assert "[authentication protected]" in (artifact / "stderr.log").read_text()
    assert "repository history was not changed" in result.stderr


def test_success_commits_source_and_audit_atomically(transaction: Transaction):
    result = execute(transaction, AICAD_TEST_OPENCODE_MODE="change")

    assert result.returncode == 0, result.stderr
    local, remote = heads(transaction)
    assert local == remote
    assert local != transaction["start"]
    changed = run("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", cwd=transaction["checkout"])
    assert "config.py" in changed.stdout
    assert ".aicad/audit/v1/100-1/run.json" in changed.stdout
    assert json.loads((transaction["checkout"] / ".aicad/audit/v1/100-1/run.json").read_text())["status"] == "completed"
    assert not (transaction["artifacts"] / "100-1").exists()


def test_successful_no_change_is_an_audit_only_success(transaction: Transaction):
    result = execute(transaction, AICAD_TEST_OPENCODE_MODE="nochange")

    assert result.returncode == 0, result.stderr
    local, remote = heads(transaction)
    assert local == remote
    assert local != transaction["start"]
    changed = run("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", cwd=transaction["checkout"])
    assert set(changed.stdout.splitlines()) == {
        ".aicad/audit/v1/100-1/events.jsonl",
        ".aicad/audit/v1/100-1/run.json",
    }
    manifest = json.loads((transaction["checkout"] / ".aicad/audit/v1/100-1/run.json").read_text())
    assert manifest["status"] == "no_changes"
    assert manifest["failure_stage"] is None
    assert not (transaction["artifacts"] / "100-1").exists()


def test_rejects_failure_artifact_directory_inside_checkout(transaction: Transaction):
    result = execute(
        transaction,
        AICAD_FAILURE_ARTIFACT_DIR=str(transaction["checkout"] / "unsafe-artifacts"),
    )

    assert result.returncode == 64
    assert heads(transaction) == (transaction["start"], transaction["start"])
    assert not (transaction["checkout"] / "unsafe-artifacts").exists()


def test_push_failure_does_not_advance_remote_and_keeps_artifact(transaction: Transaction):
    missing_remote = transaction["remote"].parent / "missing.git"
    run("git", "remote", "set-url", "origin", missing_remote, cwd=transaction["checkout"])

    result = execute(transaction, AICAD_TEST_OPENCODE_MODE="change")

    assert result.returncode != 0
    local, remote = heads(transaction)
    assert local != transaction["start"]
    assert remote == transaction["start"]
    assert (transaction["artifacts"] / "100-1" / "run.json").is_file()
    assert "force" not in result.stderr.lower()
