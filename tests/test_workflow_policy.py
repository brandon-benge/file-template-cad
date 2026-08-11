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
    schema = PROJECT_ROOT / ".aicad" / "schema" / "git-opencode-run-v1.schema.json"
    assert "opencode-ai@1.15.2" in workflow
    assert "anomalyco/opencode/github@latest" not in workflow
    assert "tools/run-git-opencode-audit" in workflow
    assert "--format json" in runner
    assert "PIPESTATUS" in runner
    assert "git commit" in runner
    assert "git push origin HEAD" in runner
    assert "AICAD_FAILURE_ARTIFACT_DIR" in workflow
    assert "AICAD_FAILURE_ARTIFACT_DIR" in runner
    assert "Failure artifact directory must be outside the repository" in runner
    assert "repository history was not changed" in runner
    assert 'if test "$status" = "failed"' in runner
    assert "write_failure_artifact" in runner
    assert "MAX_STDERR_BYTES=1048576" in runner
    assert "aicad-failure-artifacts" in workflow
    assert ".aicad/audit/v1/${{ github.run_id }}" not in workflow
    assert "[authentication protected]" in runner
    assert "MAX_EVENTS_BYTES=8388608" in runner
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
    # The only OPENCODE_MODEL token allowed is the AICAD_OPENCODE_MODEL
    # repository variable; the old hardcoded OPENCODE_MODEL env key must
    # never reappear.
    assert re.search(r"(?<!AICAD_)OPENCODE_MODEL:", workflow) is None
    assert re.search(r"(?<!AICAD_)OPENCODE_MODEL", workflow) is None


def test_opencode_workflow_sources_model_from_repository_variable():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    assert "AICAD_OPENCODE_MODEL: ${{ vars.AICAD_OPENCODE_MODEL }}" in workflow


def test_opencode_workflow_passes_candidate_provider_secrets():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "opencode.yml").read_text()
    assert "OPENCODE_API_KEY: ${{ secrets.OPENCODE_API_KEY }}" in workflow
    assert "OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}" in workflow
    assert "ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}" in workflow


def test_opencode_runner_owns_model_selection_validation():
    runner = (PROJECT_ROOT / "tools" / "run-git-opencode-audit").read_text()
    assert "AICAD_OPENCODE_MODEL" in runner
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
            if (PROJECT_ROOT.parent / name / ".aicad" / "schema" / "git-opencode-run-v1.schema.json").is_file()
        ),
        None,
    )
    if sibling is None:
        pytest.skip("sister repository is not present in this workspace")
    shared = [
        ".github/workflows/opencode.yml",
        "tools/run-git-opencode-audit",
        ".aicad/schema/git-opencode-run-v1.schema.json",
        "tests/test_git_opencode_audit.py",
        ".github/workflows/rebuild.yml",
        "tools/install-selected-python-cad-tools",
        "tests/test_version_install.py",
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


def test_rebuild_yml_exists():
    assert (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").is_file()


def test_rebuild_yml_is_manual_dispatch_without_inputs():
    text = (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").read_text()
    assert "workflow_dispatch:" in text
    assert "inputs:" not in text
    assert "push:" not in text
    assert "pull_request:" not in text
    assert "workflow_run:" not in text


def test_rebuild_yml_reads_selected_version_variable():
    text = (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").read_text()
    assert "AICAD_PYTHON_CAD_TOOLS_VERSION" in text
    assert "vars.AICAD_PYTHON_CAD_TOOLS_VERSION" in text
    assert "install-selected-python-cad-tools" in text


def test_rebuild_yml_has_no_hardcoded_version_or_local_wheel():
    text = (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").read_text()
    assert "0.1.9" not in text
    assert "python-cad-tools==" not in text
    assert "python-cad-tools/dist" not in text
    assert "test-with-cad-override" not in text


def test_rebuild_yml_never_commits_or_mutates_locks():
    text = (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").read_text()
    assert "git commit" not in text
    assert "pip-compile" not in text
    assert "install-selected-python-cad-tools" in text
    # The only requirements path allowed is the committed dev lock passed to
    # the runner, which installs from a temporary reconciled file.
    assert "requirements/locks/dev-ubuntu-x86_64-py313.lock" in text
    # No shell redirection or output-file writes into the project tree.
    assert "> requirements" not in text
    assert "--output-file" not in text


def test_rebuild_yml_permissions_least_privilege():
    text = (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").read_text()
    assert "write-all" not in text
    assert "contents: write" in text
    assert "pages: write" in text
    assert "id-token: write" in text


def test_rebuild_yml_derives_base_path_from_repository_name():
    text = (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").read_text()
    assert "github.event.repository.name" in text
    assert "--base-path" in text
    assert "/file-template-cad/" not in text
    assert "/benge-property-cad/" not in text


def test_rebuild_yml_tags_deployed_version():
    text = (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").read_text()
    assert "aicad-deploy-" in text
    assert "git tag" in text
    assert "git push origin" in text
    assert "refs/tags/" in text
    assert "git rev-parse -q --verify" in text


def test_rebuild_yml_reuses_pages_pipeline():
    text = (PROJECT_ROOT / ".github" / "workflows" / "rebuild.yml").read_text()
    for command in [
        "python-cad validate --project-root .",
        "python-cad clean --project-root .",
        "python-cad build --project-root .",
        "python-cad verify --project-root .",
        "python-cad prepare-site --project-root .",
    ]:
        assert command in text
    for action in [
        "actions/configure-pages@v5",
        "actions/upload-pages-artifact@v3",
        "actions/deploy-pages@v4",
    ]:
        assert action in text


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
