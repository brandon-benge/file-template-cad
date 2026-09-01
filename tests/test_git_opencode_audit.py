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
    template: Path
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
    template = tmp_path / "file-template-cad-gold"
    tools = tmp_path / "bin"
    artifacts = tmp_path / "artifacts"
    trigger = tmp_path / "trigger.json"
    called = tmp_path / "opencode-called.txt"
    validator = tools / "validator"
    opencode = tools / "opencode"

    # A minimal file-template-cad "gold standard" the audit runner reconciles
    # this checkout's infrastructure against before OpenCode runs. Its tracked
    # infrastructure (pyproject.toml, tracked.txt) matches the checkout below,
    # so reconciliation is a no-op here and adds no extra commit; the
    # dedicated reconciliation test seeds real drift on top of this.
    run("git", "init", "-b", "main", template, cwd=tmp_path)
    run("git", "config", "user.name", "Template", cwd=template)
    run("git", "config", "user.email", "template@example.com", cwd=template)
    (template / "pyproject.toml").write_text("[project]\nname = \"file-template-cad\"\n")
    (template / "tracked.txt").write_text("original\n")
    run("git", "add", "-A", cwd=template)
    run("git", "commit", "-m", "template", cwd=template)

    run("git", "init", "--bare", remote, cwd=tmp_path)
    run("git", "init", "-b", "main", checkout, cwd=tmp_path)
    run("git", "config", "user.name", "Test Runner", cwd=checkout)
    run("git", "config", "user.email", "runner@example.com", cwd=checkout)
    (checkout / "tracked.txt").write_text("original\n")
    (checkout / "pyproject.toml").write_text("[project]\nname = \"file-template-cad\"\n")
    (checkout / "config.py").write_text("original = True\n")
    run("git", "add", "tracked.txt", "pyproject.toml", "config.py", cwd=checkout)
    run("git", "commit", "-m", "initial", cwd=checkout)
    run("git", "remote", "add", "origin", remote, cwd=checkout)
    run("git", "push", "-u", "origin", "main", cwd=checkout)

    tools.mkdir()
    opencode.write_text(
        """#!/usr/bin/env bash
set -eu
printf '%s\\n' "${1:-}" >> "${MAKEITOURS_TEST_CALLED_FILE:-/dev/null}"
if test "${1:-}" = "--version"; then
  echo "1.15.2"
  exit 0
fi
if test "${1:-}" = "models"; then
  if test -n "${MAKEITOURS_TEST_CATALOG_SIZE:-}"; then
    yes x | head -c "$MAKEITOURS_TEST_CATALOG_SIZE"
  else
    printf '%s\\n' "catalog provider opencode-go model test-model"
    printf '%s\\n' "catalog provider openai model gpt-test"
  fi
  exit 0
fi
printf '%s\\n' '{"type":"message","text":"safe event"}'
printf '%s\\n' "stdout ${OPENCODE_API_KEY:-} ${OPENAI_API_KEY:-} ${ANTHROPIC_API_KEY:-} ${GOOGLE_API_KEY:-} ${OPENROUTER_API_KEY:-} ${GROQ_API_KEY:-} ${XAI_API_KEY:-} ${DEEPINFRA_API_KEY:-} ${MISTRAL_API_KEY:-} ${GITHUB_TOKEN:-}"
printf '%s\\n' "stderr ${OPENCODE_API_KEY:-} ${OPENAI_API_KEY:-} ${ANTHROPIC_API_KEY:-} ${GOOGLE_API_KEY:-} ${OPENROUTER_API_KEY:-} ${GROQ_API_KEY:-} ${XAI_API_KEY:-} ${DEEPINFRA_API_KEY:-} ${MISTRAL_API_KEY:-} ${GITHUB_TOKEN:-}" >&2
case "${MAKEITOURS_TEST_OPENCODE_MODE:-nochange}" in
  fail) exit 7 ;;
  hang) sleep 30 ;;
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
exit "${MAKEITOURS_TEST_VALIDATION_EXIT:-0}"
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
            "MAKEITOURS_OPENCODE_MODEL": "opencode-go/test-model",
            "OPENCODE_AGENT": "test-agent",
            "OPENCODE_API_KEY": "secret-test-value",
            "MAKEITOURS_VALIDATION_EXECUTABLE": str(validator),
            "MAKEITOURS_FAILURE_ARTIFACT_DIR": str(artifacts),
            "MAKEITOURS_CAD_TEMPLATE_CHECKOUT": str(template),
            "RUNNER_TEMP": str(tmp_path),
            "MAKEITOURS_TEST_CALLED_FILE": str(called),
        }
    )
    start = run("git", "rev-parse", "HEAD", cwd=checkout).stdout.strip()
    return {
        "checkout": checkout,
        "remote": remote,
        "template": template,
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


def called_commands(transaction: Transaction) -> list[str]:
    path = Path(transaction["env"]["MAKEITOURS_TEST_CALLED_FILE"])
    return path.read_text().splitlines() if path.exists() else []


@pytest.mark.parametrize(
    ("environment", "stage", "exit_code"),
    [
        ({"MAKEITOURS_TEST_OPENCODE_MODE": "fail"}, "opencode", 7),
        ({"MAKEITOURS_TEST_OPENCODE_MODE": "change", "MAKEITOURS_TEST_VALIDATION_EXIT": "9"}, "validation", 9),
        ({"MAKEITOURS_TEST_OPENCODE_MODE": "commit"}, "unexpected_commit", 1),
        ({"MAKEITOURS_TEST_OPENCODE_MODE": "policy"}, "policy", 1),
    ],
)
def test_failure_does_not_commit_or_push(
    transaction: Transaction, environment: dict[str, str], stage: str, exit_code: int
):
    result = execute(transaction, **environment)

    assert result.returncode == exit_code
    assert heads(transaction) == (transaction["start"], transaction["start"])
    assert not (transaction["checkout"] / ".makeitours" / "audit" / "v1" / "100-1").exists()
    artifact = transaction["artifacts"] / "100-1"
    manifest = json.loads((artifact / "run.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["failure_stage"] == stage
    assert "secret-test-value" not in (artifact / "stderr.log").read_text()
    assert "[authentication protected]" in (artifact / "stderr.log").read_text()
    assert "repository history was not changed" in result.stderr


def test_inactivity_watchdog_terminates_hung_opencode(transaction: Transaction):
    result = execute(
        transaction,
        MAKEITOURS_TEST_OPENCODE_MODE="hang",
        MAKEITOURS_OPENCODE_INACTIVITY_SECONDS="1",
    )

    assert result.returncode == 124
    assert heads(transaction) == (transaction["start"], transaction["start"])
    artifact = transaction["artifacts"] / "100-1"
    manifest = json.loads((artifact / "run.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["failure_stage"] == "opencode"
    assert manifest["opencode"]["exit_code"] == 124
    assert "OpenCode produced no output for 1 seconds" in result.stderr


def test_success_commits_source_and_audit_atomically(transaction: Transaction):
    result = execute(transaction, MAKEITOURS_TEST_OPENCODE_MODE="change")

    assert result.returncode == 0, result.stderr
    local, remote = heads(transaction)
    assert local == remote
    assert local != transaction["start"]
    changed = run("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", cwd=transaction["checkout"])
    assert "config.py" in changed.stdout
    assert ".makeitours/audit/v1/100-1/run.json" in changed.stdout
    manifest = json.loads((transaction["checkout"] / ".makeitours/audit/v1/100-1/run.json").read_text())
    assert manifest["status"] == "completed"
    assert manifest["opencode"]["provider_id"] == "opencode-go"
    assert manifest["opencode"]["model_id"] == "test-model"
    assert manifest["opencode"]["credential_presence"] == {
        "OPENCODE_API_KEY_PRESENT": True,
        "OPENAI_API_KEY_PRESENT": False,
        "ANTHROPIC_API_KEY_PRESENT": False,
        "GOOGLE_API_KEY_PRESENT": False,
        "OPENROUTER_API_KEY_PRESENT": False,
        "GROQ_API_KEY_PRESENT": False,
        "XAI_API_KEY_PRESENT": False,
        "DEEPINFRA_API_KEY_PRESENT": False,
        "MISTRAL_API_KEY_PRESENT": False,
    }
    assert not (transaction["artifacts"] / "100-1").exists()


def test_successful_no_change_is_an_audit_only_success(transaction: Transaction):
    result = execute(transaction, MAKEITOURS_TEST_OPENCODE_MODE="nochange")

    assert result.returncode == 0, result.stderr
    local, remote = heads(transaction)
    assert local == remote
    assert local != transaction["start"]
    changed = run("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", cwd=transaction["checkout"])
    assert set(changed.stdout.splitlines()) == {
        ".makeitours/audit/v1/100-1/events.jsonl",
        ".makeitours/audit/v1/100-1/run.json",
    }
    manifest = json.loads((transaction["checkout"] / ".makeitours/audit/v1/100-1/run.json").read_text())
    assert manifest["status"] == "no_changes"
    assert manifest["failure_stage"] is None
    assert not (transaction["artifacts"] / "100-1").exists()


def test_rejects_failure_artifact_directory_inside_checkout(transaction: Transaction):
    result = execute(
        transaction,
        MAKEITOURS_FAILURE_ARTIFACT_DIR=str(transaction["checkout"] / "unsafe-artifacts"),
    )

    assert result.returncode == 64
    assert heads(transaction) == (transaction["start"], transaction["start"])
    assert not (transaction["checkout"] / "unsafe-artifacts").exists()


def test_push_failure_does_not_advance_remote_and_keeps_artifact(transaction: Transaction):
    missing_remote = transaction["remote"].parent / "missing.git"
    run("git", "remote", "set-url", "origin", missing_remote, cwd=transaction["checkout"])

    result = execute(transaction, MAKEITOURS_TEST_OPENCODE_MODE="change")

    assert result.returncode != 0
    local, remote = heads(transaction)
    assert local != transaction["start"]
    assert remote == transaction["start"]
    assert (transaction["artifacts"] / "100-1" / "run.json").is_file()
    assert "force" not in result.stderr.lower()


def test_bare_model_id_rejected_before_opencode(transaction: Transaction):
    result = execute(transaction, MAKEITOURS_OPENCODE_MODEL="glm-5.2")

    assert result.returncode == 67
    assert heads(transaction) == (transaction["start"], transaction["start"])
    assert not (transaction["checkout"] / ".makeitours" / "audit" / "v1" / "100-1").exists()
    artifact = transaction["artifacts"] / "100-1"
    manifest = json.loads((artifact / "run.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["failure_stage"] == "model_selection"
    assert "not changed" in result.stderr
    assert "run" not in called_commands(transaction)


@pytest.mark.parametrize(
    "reference",
    [
        "/model",
        "provider/",
        "a/b/c",
        "provider/model with space",
        "provider/model\t",
        "provider/mode\x7f",
    ],
)
def test_malformed_model_reference_rejected(transaction: Transaction, reference: str):
    result = execute(transaction, MAKEITOURS_OPENCODE_MODEL=reference)

    assert result.returncode == 67
    assert heads(transaction) == (transaction["start"], transaction["start"])
    artifact = transaction["artifacts"] / "100-1"
    manifest = json.loads((artifact / "run.json").read_text())
    assert manifest["failure_stage"] == "model_selection"
    assert "run" not in called_commands(transaction)


def test_oversized_model_reference_rejected(transaction: Transaction):
    result = execute(transaction, MAKEITOURS_OPENCODE_MODEL=f"p/{'m' * 300}")

    assert result.returncode == 67
    assert "exceeds 256 bytes" in result.stderr
    assert "run" not in called_commands(transaction)


def test_unknown_provider_rejected(transaction: Transaction):
    result = execute(transaction, MAKEITOURS_OPENCODE_MODEL="unknown/model")

    assert result.returncode == 67
    assert "Unknown provider id" in result.stderr
    assert "run" not in called_commands(transaction)


def test_missing_credential_rejected_without_fallback(transaction: Transaction):
    env = {key: value for key, value in transaction["env"].items() if key != "OPENCODE_API_KEY"}
    result = run(RUNNER, transaction["trigger"], cwd=transaction["checkout"], env=env, check=False)

    assert result.returncode == 67
    assert "OPENCODE_API_KEY is not set" in result.stderr
    assert "run" not in called_commands(transaction)
    artifact = transaction["artifacts"] / "100-1"
    manifest = json.loads((artifact / "run.json").read_text())
    assert manifest["failure_stage"] == "model_selection"
    assert manifest["opencode"]["credential_presence"]["OPENCODE_API_KEY_PRESENT"] is False


def test_empty_credential_rejected_without_fallback(transaction: Transaction):
    result = execute(transaction, OPENCODE_API_KEY="")

    assert result.returncode == 67
    assert "OPENCODE_API_KEY is not set" in result.stderr
    assert "run" not in called_commands(transaction)


def test_unset_model_reference_fails_and_writes_dump(transaction: Transaction):
    env = {key: value for key, value in transaction["env"].items() if key != "MAKEITOURS_OPENCODE_MODEL"}
    result = run(RUNNER, transaction["trigger"], cwd=transaction["checkout"], env=env, check=False)

    assert result.returncode == 67
    assert "MAKEITOURS_OPENCODE_MODEL is not set" in result.stderr
    dump = json.loads((transaction["artifacts"] / "100-1" / "provider-model-diagnostic.json").read_text())
    assert dump["attempted_reference"] == ""
    assert dump["parse"]["error"]


def test_openai_provider_proceeds_with_openai_key(transaction: Transaction):
    env = {key: value for key, value in transaction["env"].items() if key != "OPENCODE_API_KEY"}
    env["OPENAI_API_KEY"] = "secret-openai"
    env["MAKEITOURS_OPENCODE_MODEL"] = "openai/gpt-test"
    env["MAKEITOURS_TEST_OPENCODE_MODE"] = "change"
    result = run(RUNNER, transaction["trigger"], cwd=transaction["checkout"], env=env, check=False)

    assert result.returncode == 0, result.stderr
    local, remote = heads(transaction)
    assert local == remote
    assert local != transaction["start"]


def test_anthropic_provider_proceeds_with_anthropic_key(transaction: Transaction):
    env = {key: value for key, value in transaction["env"].items() if key != "OPENCODE_API_KEY"}
    env["ANTHROPIC_API_KEY"] = "secret-anthropic"
    env["MAKEITOURS_OPENCODE_MODEL"] = "anthropic/claude-test"
    env["MAKEITOURS_TEST_OPENCODE_MODE"] = "change"
    result = run(RUNNER, transaction["trigger"], cwd=transaction["checkout"], env=env, check=False)

    assert result.returncode == 0, result.stderr
    local, remote = heads(transaction)
    assert local == remote
    assert local != transaction["start"]


def test_opencode_zen_provider_proceeds_with_opencode_key(transaction: Transaction):
    env = dict(transaction["env"])
    env["MAKEITOURS_OPENCODE_MODEL"] = "opencode-zen/glm-test"
    env["MAKEITOURS_TEST_OPENCODE_MODE"] = "change"
    result = run(RUNNER, transaction["trigger"], cwd=transaction["checkout"], env=env, check=False)

    assert result.returncode == 0, result.stderr
    local, remote = heads(transaction)
    assert local == remote
    assert local != transaction["start"]


@pytest.mark.parametrize(
    ("provider_id", "env_name", "secret_value"),
    [
        ("google", "GOOGLE_API_KEY", "secret-google"),
        ("openrouter", "OPENROUTER_API_KEY", "secret-openrouter"),
        ("groq", "GROQ_API_KEY", "secret-groq"),
        ("xai", "XAI_API_KEY", "secret-xai"),
        ("deepinfra", "DEEPINFRA_API_KEY", "secret-deepinfra"),
        ("mistral", "MISTRAL_API_KEY", "secret-mistral"),
    ],
)
def test_provider_proceeds_with_matching_key(
    transaction: Transaction, provider_id: str, env_name: str, secret_value: str
):
    env = {key: value for key, value in transaction["env"].items() if key != "OPENCODE_API_KEY"}
    env[env_name] = secret_value
    env["MAKEITOURS_OPENCODE_MODEL"] = f"{provider_id}/model-test"
    env["MAKEITOURS_TEST_OPENCODE_MODE"] = "change"
    result = run(RUNNER, transaction["trigger"], cwd=transaction["checkout"], env=env, check=False)

    assert result.returncode == 0, result.stderr
    local, remote = heads(transaction)
    assert local == remote
    assert local != transaction["start"]


def test_failure_dump_contains_version_catalog_reference_and_presence(transaction: Transaction):
    result = execute(transaction, MAKEITOURS_TEST_OPENCODE_MODE="fail")

    assert result.returncode == 7
    artifact = transaction["artifacts"] / "100-1"
    dump = json.loads((artifact / "provider-model-diagnostic.json").read_text())
    assert dump["artifact_schema_version"] == 1
    assert dump["opencode_version"] == "1.15.2"
    assert "opencode-go" in dump["model_catalog"]["text"]
    assert dump["model_catalog"]["truncated"] is False
    assert dump["attempted_reference"] == "opencode-go/test-model"
    assert dump["parse"]["provider_id"] == "opencode-go"
    assert dump["parse"]["model_id"] == "test-model"
    assert dump["parse"]["error"] is None
    assert dump["credential_presence"]["OPENCODE_API_KEY_PRESENT"] is True
    assert dump["credential_presence"]["OPENAI_API_KEY_PRESENT"] is False
    assert dump["credential_presence"]["ANTHROPIC_API_KEY_PRESENT"] is False


def test_failure_dump_contains_parse_error_for_bare_reference(transaction: Transaction):
    result = execute(transaction, MAKEITOURS_OPENCODE_MODEL="glm-5.2")

    assert result.returncode == 67
    dump = json.loads((transaction["artifacts"] / "100-1" / "provider-model-diagnostic.json").read_text())
    assert dump["attempted_reference"] == "glm-5.2"
    assert dump["parse"]["error"]
    assert dump["parse"]["provider_id"] == ""


def test_dump_catalog_respects_byte_bound(transaction: Transaction):
    result = execute(transaction, MAKEITOURS_TEST_OPENCODE_MODE="fail", MAKEITOURS_TEST_CATALOG_SIZE="2097152")

    assert result.returncode == 7
    dump = json.loads((transaction["artifacts"] / "100-1" / "provider-model-diagnostic.json").read_text())
    assert dump["model_catalog"]["truncated"] is True
    assert dump["model_catalog"]["retained_bytes"] == 1048576
    assert dump["model_catalog"]["original_bytes"] > 1048576
    assert len(dump["model_catalog"]["text"]) == 1048576
    assert len(dump["model_catalog"]["sha256"]) == 64


def test_no_provider_secret_values_in_failure_artifacts(transaction: Transaction):
    env = dict(transaction["env"])
    env["OPENAI_API_KEY"] = "secret-openai"
    env["ANTHROPIC_API_KEY"] = "secret-anthropic"
    env["GOOGLE_API_KEY"] = "secret-google"
    env["OPENROUTER_API_KEY"] = "secret-openrouter"
    env["GROQ_API_KEY"] = "secret-groq"
    env["XAI_API_KEY"] = "secret-xai"
    env["DEEPINFRA_API_KEY"] = "secret-deepinfra"
    env["MISTRAL_API_KEY"] = "secret-mistral"
    env["GITHUB_TOKEN"] = "secret-github-token"
    env["MAKEITOURS_TEST_OPENCODE_MODE"] = "fail"
    result = run(RUNNER, transaction["trigger"], cwd=transaction["checkout"], env=env, check=False)

    assert result.returncode == 7
    artifact = transaction["artifacts"] / "100-1"
    secrets = [
        "secret-test-value",
        "secret-openai",
        "secret-anthropic",
        "secret-google",
        "secret-openrouter",
        "secret-groq",
        "secret-xai",
        "secret-deepinfra",
        "secret-mistral",
        "secret-github-token",
    ]
    for name in ["run.json", "events.jsonl", "stderr.log", "artifact.json", "provider-model-diagnostic.json"]:
        text = (artifact / name).read_text()
        for secret in secrets:
            assert secret not in text, f"{name} contains {secret}"
    # The fake prints every provider key and GITHUB_TOKEN to stdout and
    # stderr; both filter paths must redact every one.
    assert "[authentication protected]" in (artifact / "stderr.log").read_text()
    for secret in secrets:
        assert secret not in result.stdout, f"stdout contains {secret}"


def test_diagnostic_dump_tolerates_failing_opencode(transaction: Transaction):
    failing_bin = transaction["checkout"].parent / "failing-bin"
    failing_bin.mkdir()
    broken = failing_bin / "opencode"
    broken.write_text("#!/usr/bin/env bash\nexit 1\n")
    broken.chmod(0o755)
    env = dict(transaction["env"])
    env["PATH"] = f"{failing_bin}{os.pathsep}{env['PATH']}"
    env["MAKEITOURS_TEST_OPENCODE_MODE"] = "fail"
    result = run(RUNNER, transaction["trigger"], cwd=transaction["checkout"], env=env, check=False)

    assert result.returncode != 0
    artifact = transaction["artifacts"] / "100-1"
    dump = json.loads((artifact / "provider-model-diagnostic.json").read_text())
    assert dump["opencode_version"] == "unavailable"
    assert "opencode models failed" in dump["model_catalog"]["text"]
    assert dump["model_catalog"]["retained_bytes"] == len(dump["model_catalog"]["text"].encode("utf-8"))
    assert len(dump["model_catalog"]["sha256"]) == 64


def test_infrastructure_is_reconciled_before_opencode_runs(transaction: Transaction):
    checkout = transaction["checkout"]
    template = transaction["template"]

    # Drift the checkout's infrastructure away from the template, add a stray
    # tracked infrastructure file the template doesn't have, and hand-edit a
    # customer-owned file.
    (checkout / "tracked.txt").write_text("HAND EDITED\n")
    (checkout / "stray.cfg").write_text("customer added\n")
    (checkout / "config.py").write_text("customer = 'keep me'\n")
    run("git", "add", "-A", cwd=checkout)
    run("git", "commit", "-m", "local drift", cwd=checkout)
    run("git", "push", "origin", "main", cwd=checkout)
    drifted_head = run("git", "rev-parse", "HEAD", cwd=checkout).stdout.strip()

    result = execute(transaction, MAKEITOURS_TEST_OPENCODE_MODE="nochange")
    assert result.returncode == 0, result.stderr

    # Infrastructure now matches the template again; the stray file is gone.
    assert (checkout / "tracked.txt").read_text() == (template / "tracked.txt").read_text()
    assert not (checkout / "stray.cfg").exists()
    # The customer-owned file is never touched by reconciliation.
    assert (checkout / "config.py").read_text() == "customer = 'keep me'\n"

    # Reconciliation landed as its own commit, and everything was pushed.
    log_subjects = run(
        "git", "log", "--format=%s", f"{drifted_head}..HEAD", cwd=checkout
    ).stdout.splitlines()
    assert "chore: reconcile infrastructure with file-template-cad" in log_subjects
    local, remote = heads(transaction)
    assert local == remote
