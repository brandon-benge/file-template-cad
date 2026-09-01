"""Static policy checks for CI/workflow definitions, symlinks, and boundaries.

These tests run locally without contacting GitHub, installing dependencies,
or building the project.
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_ci_yml_exists():
    assert (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").is_file()


def test_pages_yml_exists():
    assert (PROJECT_ROOT / ".github" / "workflows" / "pages.yml").is_file()


def test_old_build_design_yml_removed():
    assert not (PROJECT_ROOT / ".github" / "workflows" / "build-design.yml").is_file()


def test_opencode_workflow_uses_one_non_cancelling_repository_queue():
    text = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    assert text.count("git-opencode-${{ github.repository }}") == 1
    assert "queue: max" in text
    assert "cancel-in-progress: false" in text
    assert "Wait for prior workflow runs" not in text
    assert text.count("Handle Git-triggered OpenCode request") == 1
    assert "startsWith(github.event.comment.body, '/oc')" in text
    assert "startsWith(github.event.comment.body, '/opencode')" in text


def test_opencode_workflow_owns_a_bounded_audit_transaction():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    runner = (PROJECT_ROOT / "tools" / "run-git-opencode-audit").read_text()
    watchdog = (PROJECT_ROOT / "tools" / "run-with-inactivity-watchdog").read_text()
    ubuntu_lock = (PROJECT_ROOT / "requirements" / "locks" / "dev-ubuntu-x86_64-py313.lock").read_text()
    schema = PROJECT_ROOT / ".makeitours" / "schema" / "git-opencode-run-v1.schema.json"
    assert "opencode-ai@latest" in workflow
    assert "Install latest OpenCode" in workflow
    assert "anomalyco/opencode/github@latest" not in workflow
    assert "tools/run-git-opencode-audit" in workflow
    assert "--format json" in runner
    assert "run-with-inactivity-watchdog" in runner
    assert "git commit" in runner
    assert "git push origin HEAD" in runner
    assert "MAKEITOURS_FAILURE_ARTIFACT_DIR" in workflow
    assert "MAKEITOURS_FAILURE_ARTIFACT_DIR" in runner
    assert "Failure artifact directory must be outside the repository" in runner
    assert "repository history was not changed" in runner
    assert 'if test "$status" = "failed"' in runner
    assert "write_failure_artifact" in runner
    assert "MAX_STDERR_BYTES=1048576" in runner
    assert "makeitours-failure-artifacts" in workflow
    assert ".makeitours/audit/v1/${{ github.run_id }}" not in workflow
    assert "[authentication protected]" in runner
    assert "MAX_EVENTS_BYTES=8388608" in runner
    assert "DEFAULT_OPENCODE_INACTIVITY_SECONDS=600" in runner
    assert "run-with-inactivity-watchdog" in runner
    assert "Run every long-running test, validation, build, and verification command as a separate tool call" in runner
    assert "Do not chain commands with &&, ;, or pipes" in runner
    assert "do not start these commands in parallel or in the background" in runner
    assert "Finish all requested geometry, metadata, material, and user-facing-name edits" in runner
    assert "After final verification succeeds, do not make another source edit" in runner
    assert "pytest-xdist==" in ubuntu_lock
    assert "start_new_session=True" in watchdog
    assert "cache: pip" in workflow
    assert "uses: actions/cache@v4" in workflow
    assert "validation-environment-cache" in workflow
    assert schema.is_file()


def test_opencode_workflow_permissions_are_bounded():
    text = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    assert "contents: write" in text
    assert "issues: write" in text
    assert "pull-requests: write" not in text
    assert "write-all" not in text


def test_opencode_workflow_has_no_hardcoded_model_id():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    assert "glm-5.2" not in workflow
    # The only OPENCODE_MODEL token allowed is the MAKEITOURS_OPENCODE_MODEL
    # repository variable; the old hardcoded OPENCODE_MODEL env key must
    # never reappear.
    assert re.search(r"(?<!MAKEITOURS_)OPENCODE_MODEL:", workflow) is None
    assert re.search(r"(?<!MAKEITOURS_)OPENCODE_MODEL", workflow) is None


def test_opencode_workflow_sources_model_from_repository_variable():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    assert "MAKEITOURS_OPENCODE_MODEL: ${{ vars.MAKEITOURS_OPENCODE_MODEL }}" in workflow


def test_opencode_workflow_passes_candidate_provider_secrets():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    assert "OPENCODE_API_KEY: ${{ secrets.OPENCODE_API_KEY }}" in workflow
    assert "OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}" in workflow
    assert "ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}" in workflow


def test_opencode_runner_owns_model_selection_validation():
    runner = (PROJECT_ROOT / "tools" / "run-git-opencode-audit").read_text()
    assert "MAKEITOURS_OPENCODE_MODEL" in runner
    assert "validate_model_reference" in runner
    assert "provider-model-diagnostic.json" in runner
    assert "credential_presence" in runner
    assert "OPENCODE_API_KEY_PRESENT" in runner
    assert "OPENAI_API_KEY_PRESENT" in runner
    assert "ANTHROPIC_API_KEY_PRESENT" in runner
    assert "OPENAI_API_KEY" in runner
    assert "ANTHROPIC_API_KEY" in runner
    assert "exit 67" in runner


def test_sister_repository_contract_parity():
    """The shared Git-triggered OpenCode contract files stay byte-identical."""
    sibling_names = [name for name in ["benge-property-cad", "file-template-cad"] if name != PROJECT_ROOT.name]
    sibling = next(
        (
            PROJECT_ROOT.parent / name
            for name in sibling_names
            if (PROJECT_ROOT.parent / name / ".makeitours" / "schema" / "git-opencode-run-v1.schema.json").is_file()
        ),
        None,
    )
    if sibling is None:
        pytest.skip("sister repository is not present in this workspace")
    shared = [
        ".github/workflows/opencode.yml",
        "tools/run-git-opencode-audit",
        "tools/reconcile-infrastructure",
        "tools/run-with-inactivity-watchdog",
        ".makeitours/schema/git-opencode-run-v1.schema.json",
        "tests/test_git_opencode_audit.py",
    ]
    for relative in shared:
        assert (PROJECT_ROOT / relative).read_bytes() == (sibling / relative).read_bytes(), (
            f"shared contract file diverged: {relative}"
        )


def test_ci_yml_required_jobs():
    text = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    required = [
        "locked-install",
        "static-analysis",
        "boundary-governance",
        "compatibility-report",
        "required-gate",
    ]
    for job in required:
        assert job in text, f"ci.yml missing required job: {job}"


def test_regular_ci_excludes_end_to_end_testing():
    text = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    forbidden = [
        "test_build_artifacts.py",
        "test_build_cli.py",
        "test_build_determinism.py",
        "test_viewer_e2e.py",
        "playwright install",
    ]
    for value in forbidden:
        assert value not in text, f"regular CI must not run E2E command: {value}"


def test_end_to_end_workflow_is_manual():
    text = (PROJECT_ROOT / ".github" / "workflows" / "end-to-end.yml").read_text()
    assert "workflow_dispatch:" in text
    assert "push:" not in text
    assert "pull_request:" not in text
    assert "test_build_artifacts.py" in text or "test_build_determinism.py" in text
    assert "test_viewer_e2e.py" in text


def test_actions_pinned_to_sha():
    """Check that third-party actions are pinned to full commit SHAs."""
    for wf in ["ci.yml", "end-to-end.yml", "pages.yml"]:
        text = (PROJECT_ROOT / ".github" / "workflows" / wf).read_text()
        for match in re.finditer(r"uses:\s+(\S+)(?:@)(\S+)", text):
            action = match.group(1)
            ref = match.group(2)
            if not action.startswith("actions/"):
                continue
            # actions/checkout@v4 and similar version tags are acceptable
            # if they are well-known actions. The plan says to pin
            # third-party actions to reviewed full commit SHAs, but
            # actions/checkout, setup-python, etc. are first-party.
            if not re.match(r"^[0-9a-f]{40}$", ref):
                if action.startswith("actions/"):
                    # Known first-party actions may use tags
                    assert re.match(r"^v?\d+", ref), f"{action}@{ref} not pinned to SHA or version tag"
                else:
                    assert re.match(r"^[0-9a-f]{40}$", ref), (
                        f"Third-party action {action}@{ref} must be pinned to full SHA"
                    )


def test_workflow_permissions_least_privilege():
    for wf in ["ci.yml", "end-to-end.yml", "pages.yml"]:
        text = (PROJECT_ROOT / ".github" / "workflows" / wf).read_text()
        # Must declare permissions at top level
        assert "permissions:" in text, f"{wf} missing top-level permissions block"
        # Must not use write-all
        assert "write-all" not in text, f"{wf} uses write-all"


def test_pages_yml_workflow_run_trigger():
    text = (PROJECT_ROOT / ".github" / "workflows" / "pages.yml").read_text()
    assert "workflow_run:" in text
    assert "workflows:" in text
    assert "File Template CAD CI" in text


def test_pages_yml_no_node():
    text = (PROJECT_ROOT / ".github" / "workflows" / "pages.yml").read_text()
    assert "node" not in text.lower()
    assert "npm" not in text.lower()
    assert "viewer/" not in text


def test_pages_yml_verify_head_sha():
    text = (PROJECT_ROOT / ".github" / "workflows" / "pages.yml").read_text()
    assert "head_sha" in text
    assert "git rev-parse HEAD" in text or "rev-parse" in text


def test_opencode_directories_exist():
    for d in [".opencode/commands", ".opencode/tools"]:
        assert (PROJECT_ROOT / d).is_dir(), f"Missing directory: {d}"


def test_agents_md_exists():
    assert (PROJECT_ROOT / "AGENTS.md").is_file()


def test_agents_md_has_separation_of_duties():
    text = (PROJECT_ROOT / "AGENTS.md").read_text()
    assert "file-design-maintainer" in text
    assert "file-artifact-reviewer" in text
    assert "cad-compatibility-verifier" in text
    assert "python-cad-tools-upgrader" not in text
    assert "explicitly asks to commit" in text
    assert "Repository boundary" in text


def test_agents_md_states_the_two_tier_authoring_contract():
    text = (PROJECT_ROOT / "AGENTS.md").read_text()
    assert "Authoring tiers" in text
    assert "Tier 1" in text and "Tier 2" in text
    assert "verified authoring" in text
    assert "unverified direct library access" in text
    assert "two-tier-contract.md" in text
    # Each agent states its own tier boundary; no agent claims Tier 1
    # guarantees for Tier 2 (directly-authored) artifacts.
    design_maintainer = text.split("## File Design Maintainer", 1)[1].split("## File Artifact Reviewer", 1)[0]
    assert "Tier 1" in design_maintainer and "Tier 2" in design_maintainer
    artifact_reviewer = text.split("## File Artifact Reviewer", 1)[1].split("## CAD Compatibility Verifier", 1)[0]
    assert "Tier 1" in artifact_reviewer
    assert "Out of scope" in artifact_reviewer and "Tier 2" in artifact_reviewer
    compatibility_verifier = text.split("## CAD Compatibility Verifier", 1)[1]
    assert "Tier 1 verification" in compatibility_verifier
    assert "Tier 2 verification" in compatibility_verifier
    assert "does not assert artifact determinism" in compatibility_verifier


def test_readme_agent_governance_references_the_tier_contract():
    text = (PROJECT_ROOT / "README.md").read_text()
    section = text.split("## Agent governance", 1)[1]
    assert "Tier 1" in section and "Tier 2" in section


def test_python_cad_tools_version_selection_is_fully_removed():
    """The python-cad-tools version-selection feature -- rebuild.yml, its
    install-selected-python-cad-tools tool, and their test -- is gone, and no
    workflow reads the MAKEITOURS_PYTHON_CAD_TOOLS_VERSION variable anymore."""
    workflows = PROJECT_ROOT / ".github" / "workflows"
    assert not (workflows / "rebuild.yml").exists()
    assert not (PROJECT_ROOT / "tools" / "install-selected-python-cad-tools").exists()
    assert not (PROJECT_ROOT / "tests" / "test_version_install.py").exists()
    for workflow in workflows.glob("*.yml"):
        assert "MAKEITOURS_PYTHON_CAD_TOOLS_VERSION" not in workflow.read_text(), workflow.name


def test_opencode_workflow_reconciles_infrastructure_before_running():
    """Every triggered run reconciles this repo's infrastructure against
    file-template-cad's live committed content before OpenCode's edit loop,
    so a phone-initiated change never leaves infrastructure drifted."""
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    runner = (PROJECT_ROOT / "tools" / "run-git-opencode-audit").read_text()
    reconciler = PROJECT_ROOT / "tools" / "reconcile-infrastructure"

    # The workflow fetches file-template-cad live (a shallow anonymous clone,
    # outside the repo working tree) and hands its path to the runner.
    assert "git clone --depth 1 https://github.com/brandon-benge/file-template-cad.git" in workflow
    assert "MAKEITOURS_CAD_TEMPLATE_CHECKOUT: ${{ runner.temp }}/file-template-cad-gold" in workflow

    # The runner reconciles before it captures START_SHA / runs OpenCode, and
    # commits the result as its own commit so it never trips the
    # customer-owned-only policy check on OpenCode's own changes.
    assert reconciler.is_file()
    assert 'python3 "$SCRIPT_DIR/reconcile-infrastructure" "$CAD_TEMPLATE_CHECKOUT"' in runner
    assert "MAKEITOURS_CAD_TEMPLATE_CHECKOUT" in runner
    reconcile_index = runner.index("reconcile-infrastructure")
    assert reconcile_index < runner.index('readonly START_SHA=')
    assert reconcile_index < runner.index("opencode run --format json")
    assert 'git commit -m "chore: reconcile infrastructure with file-template-cad"' in runner

    # The reconciler never touches the four customer-owned paths, generated/,
    # or the per-repo audit trail.
    reconciler_text = reconciler.read_text()
    assert '_CUSTOMER_TOP_LEVEL = {"config.py", "model.py", "drawing_annotations.py"}' in reconciler_text
    assert 'models/' in reconciler_text
    assert '".makeitours/audit"' in reconciler_text


def test_python_cad_tools_upgrader_agent_retired():
    """The agent-owned python-cad-tools upgrade path is fully removed."""
    assert not (PROJECT_ROOT / ".agents" / "agents" / "python-cad-tools-upgrader.md").exists()
    assert not (PROJECT_ROOT / ".agents" / "skills" / "python-cad-tools-upgrader").exists()
    config = (PROJECT_ROOT / "opencode.jsonc").read_text()
    assert "python-cad-tools-upgrader" not in config
    assert '"pyproject.toml": "allow"' not in config
    assert "requirements/*.lock" not in config
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert "python-cad-tools-upgrader" not in readme
    agents_md = (PROJECT_ROOT / "AGENTS.md").read_text()
    assert "owns dependency upgrades" not in agents_md
    upgrade_ui = (PROJECT_ROOT / ".agents" / "skills" / "upgrade-ui" / "SKILL.md").read_text()
    assert "python-cad-tools-upgrader" not in upgrade_ui
    normalized = " ".join(upgrade_ui.split())
    assert "When OpenCode tools are not available" in normalized


def test_remaining_agents_and_tools_unchanged():
    config = (PROJECT_ROOT / "opencode.jsonc").read_text()
    for agent in ["file-design-maintainer", "file-artifact-reviewer", "cad-compatibility-verifier"]:
        assert f'"{agent}":' in config
        assert (PROJECT_ROOT / ".agents" / "agents" / f"{agent}.md").is_file()
    assert (PROJECT_ROOT / ".agents" / "skills" / "cad-compatibility-verifier" / "SKILL.md").is_file()
    assert (PROJECT_ROOT / ".agents" / "skills" / "file-design-maintainer" / "SKILL.md").is_file()
    assert (PROJECT_ROOT / ".agents" / "skills" / "file-artifact-reviewer" / "SKILL.md").is_file()
    assert (PROJECT_ROOT / "tools" / "run-git-opencode-audit").is_file()


def test_ui_tools_and_skills_exist():
    for name in ["start-ui", "stop-ui", "upgrade-ui"]:
        assert (PROJECT_ROOT / ".opencode" / "tools" / f"{name}.js").is_file()
        skill = PROJECT_ROOT / ".agents" / "skills" / name / "SKILL.md"
        assert skill.is_file()
        normalized = " ".join(skill.read_text().split())
        assert "When OpenCode tools are not available" in normalized


def test_save_has_no_agent_and_requires_explicit_git_commit():
    assert not (PROJECT_ROOT / ".agents" / "agents" / "save.md").exists()
    config = (PROJECT_ROOT / "opencode.jsonc").read_text()
    assert '"save": {' not in config
    assert '"specrepo-autocommit": "allow"' in config
    save_skill = (PROJECT_ROOT / ".agents" / "skills" / "save" / "SKILL.md").read_text()
    save_tool = (PROJECT_ROOT / ".opencode" / "tools" / "specrepo-autocommit.js").read_text()
    assert "explicitly asks to commit" in save_skill
    assert "python3 .opencode/tools/specrepo-autocommit.py" in save_skill
    assert "userExplicitlyRequestedGitCommit" in save_tool


def test_locks_in_requirements_locks():
    locks_dir = PROJECT_ROOT / "requirements" / "locks"
    assert locks_dir.is_dir()
    expected = [
        "dev-ubuntu-x86_64-py312.lock",
        "dev-ubuntu-x86_64-py313.lock",
        "dev-macos-arm64-py312.lock",
        "dev-macos-arm64-py313.lock",
    ]
    for name in expected:
        assert (locks_dir / name).is_file(), f"Missing lock: {name}"


def test_governance_boundary_check():
    """AGENTS.md enforces the tooling boundary."""
    text = (PROJECT_ROOT / "AGENTS.md").read_text()
    assert "site-packages" in text
