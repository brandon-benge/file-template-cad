"""Static policy checks for CI/workflow definitions, symlinks, and boundaries.

These tests run locally without contacting GitHub, installing dependencies,
or building the project.
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    not (PROJECT_ROOT / ".github").is_dir(),
    reason=(
        "governance checks on this repository's own CI/workflow files -- meaningless outside "
        "a full checkout of file-template-cad itself. A project seeded from this template "
        "deliberately never receives .github/ (GithubReleaseTemplateSource's EXCLUDED_PREFIXES "
        "in makeitours-data-plane), so every test in this file failed unconditionally in every "
        "seeded project regardless of the actual change under review -- exit code 1 either way, "
        "with no way for a project's own agent to distinguish that from a real regression."
    ),
)


def test_ci_yml_exists():
    assert (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").is_file()


def test_pages_yml_exists():
    assert (PROJECT_ROOT / ".github" / "workflows" / "pages.yml").is_file()


def test_old_build_design_yml_removed():
    assert not (PROJECT_ROOT / ".github" / "workflows" / "build-design.yml").is_file()


MAKEITOURS_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "makeitours.yml"
RUNNER_IMAGE = re.compile(r"image: ghcr\.io/brandon-benge/makeitours-agentic-runner@sha256:[0-9a-f]{64}\n")


def test_makeitours_workflow_uses_one_non_cancelling_repository_queue():
    text = MAKEITOURS_WORKFLOW.read_text()
    assert text.count("makeitours-${{ github.repository }}") == 1
    assert "queue: max" in text
    assert "cancel-in-progress: false" in text
    assert "github.actor == github.repository_owner" in text
    assert "startsWith(github.event.comment.body, '/mio')" in text
    assert "startsWith(github.event.comment.body, '/makeitours')" in text
    assert "'/oc'" not in text and "'/opencode'" not in text


def test_makeitours_workflow_runs_the_pinned_runner_image():
    """The ticket runs makeitours-agentic in the public runner image, pinned by digest (never a
    movable tag), with no OpenCode, Node, Python setup or model gateway (2026-10-07 approval)."""
    text = MAKEITOURS_WORKFLOW.read_text()
    assert RUNNER_IMAGE.search(text), "the runner image must be pinned by sha256 digest"
    assert "run: makeitours-agentic-git-run" in text
    assert "timeout-minutes: 180" in text
    for retired in [
        "opencode-ai",
        "OPENCODE_AGENT",
        "setup-node",
        "setup-python",
        ".audit-venv",
        "MAKEITOURS_VALIDATION_EXECUTABLE",
    ]:
        assert retired not in text, retired
    assert "gateway" not in text.lower()
    assert "MAKEITOURS_FAILURE_ARTIFACT_DIR: ${{ runner.temp }}/makeitours-failure-artifacts" in text
    assert "if: failure()" in text and "retention-days: 14" in text


def test_makeitours_workflow_permissions_are_bounded():
    text = MAKEITOURS_WORKFLOW.read_text()
    assert "contents: write" in text
    assert "issues: write" in text
    assert "actions: write" in text  # dispatching ci.yml and release-template.yml after a push
    assert "pull-requests: write" not in text
    assert "write-all" not in text


def test_makeitours_workflow_sources_model_and_keys_from_the_app_settings():
    workflow = MAKEITOURS_WORKFLOW.read_text()
    assert "glm-5.2" not in workflow
    assert "MAKEITOURS_OPENCODE_MODEL: ${{ vars.MAKEITOURS_OPENCODE_MODEL }}" in workflow
    for name in [
        "OPENCODE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
        "XAI_API_KEY",
        "DEEPINFRA_API_KEY",
        "MISTRAL_API_KEY",
    ]:
        assert f"{name}: ${{{{ secrets.{name} }}}}" in workflow, name
    assert "GITHUB_TOKEN: ${{ github.token }}" in workflow


def test_opencode_ticket_runner_is_retired():
    for retired in [
        ".github/workflows/opencode.yml",
        "tools/run-git-opencode-audit",
        "tools/run-with-inactivity-watchdog",
        "tests/test_git_opencode_audit.py",
    ]:
        assert not (PROJECT_ROOT / retired).exists(), retired
    assert (PROJECT_ROOT / ".makeitours" / "schema" / "makeitours-run-v2.schema.json").is_file()
    # Older runs in history stay readable.
    assert (PROJECT_ROOT / ".makeitours" / "schema" / "git-opencode-run-v1.schema.json").is_file()


def test_sister_repository_contract_parity():
    """The shared Git-triggered request contract files stay byte-identical."""
    sibling_names = [name for name in ["benge-property-cad", "file-template-cad"] if name != PROJECT_ROOT.name]
    sibling = next(
        (
            PROJECT_ROOT.parent / name
            for name in sibling_names
            if (PROJECT_ROOT.parent / name / ".github" / "workflows" / "makeitours.yml").is_file()
        ),
        None,
    )
    if sibling is None:
        pytest.skip("sister repository with the makeitours workflow is not present in this workspace")
    shared = [
        ".github/workflows/makeitours.yml",
        "tools/reconcile-infrastructure",
        ".makeitours/schema/makeitours-run-v2.schema.json",
        ".makeitours/schema/git-opencode-run-v1.schema.json",
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


def test_opencode_is_fully_retired():
    """GitHub tickets run makeitours-agentic and the MakeItOurs app saves with
    makeitours-agentic-commit, so no OpenCode configuration, tools, commit script or
    agent-callable save skill remain (2026-10-08, Amendment 1)."""
    for retired in [".opencode", "opencode.jsonc", ".autoconfig.yaml", ".agents/skills/save"]:
        assert not (PROJECT_ROOT / retired).exists(), retired
    for path in [*(PROJECT_ROOT / ".agents").rglob("*.md"), PROJECT_ROOT / "AGENTS.md", PROJECT_ROOT / "README.md"]:
        text = path.read_text()
        assert "specrepo-autocommit" not in text, path
        assert "opencode.jsonc" not in text, path
        assert "invoke `save`" not in text, path


def test_agents_md_exists():
    assert (PROJECT_ROOT / "AGENTS.md").is_file()


def test_agents_md_has_separation_of_duties():
    text = (PROJECT_ROOT / "AGENTS.md").read_text()
    assert "file-design-maintainer" in text
    assert "file-artifact-reviewer" in text
    assert "cad-compatibility-verifier" in text
    assert "python-cad-tools-upgrader" not in text
    assert "No agent commits" in text
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


def test_makeitours_workflow_does_not_reconcile_infrastructure_automatically():
    """Infrastructure changes only through the explicit Upgrade Project operation."""
    workflow = MAKEITOURS_WORKFLOW.read_text()
    reconciler = PROJECT_ROOT / "tools" / "reconcile-infrastructure"
    assert "git clone --depth 1 https://github.com/brandon-benge/file-template-cad.git" not in workflow
    assert "MAKEITOURS_CAD_TEMPLATE_CHECKOUT" not in workflow
    assert "run: makeitours-agentic-git-run" in workflow
    assert reconciler.is_file()

    # The reconciler never touches the four customer-owned paths, generated/,
    # or the per-repo audit trail.
    reconciler_text = reconciler.read_text()
    assert '_CUSTOMER_TOP_LEVEL = {"config.py", "model.py", "drawing_annotations.py"}' in reconciler_text
    assert "models/" in reconciler_text
    assert '".makeitours/audit"' in reconciler_text


def test_python_cad_tools_upgrader_agent_retired():
    """The agent-owned python-cad-tools upgrade path is fully removed."""
    assert not (PROJECT_ROOT / ".agents" / "agents" / "python-cad-tools-upgrader.md").exists()
    assert not (PROJECT_ROOT / ".agents" / "skills" / "python-cad-tools-upgrader").exists()
    readme = (PROJECT_ROOT / "README.md").read_text()
    assert "python-cad-tools-upgrader" not in readme
    agents_md = (PROJECT_ROOT / "AGENTS.md").read_text()
    assert "owns dependency upgrades" not in agents_md
    upgrade_ui = (PROJECT_ROOT / ".agents" / "skills" / "upgrade-ui" / "SKILL.md").read_text()
    assert "python-cad-tools-upgrader" not in upgrade_ui


def test_remaining_agents_and_tools_unchanged():
    for agent in ["file-design-maintainer", "file-artifact-reviewer", "cad-compatibility-verifier"]:
        assert (PROJECT_ROOT / ".agents" / "agents" / f"{agent}.md").is_file()
    assert (PROJECT_ROOT / ".agents" / "skills" / "cad-compatibility-verifier" / "SKILL.md").is_file()
    assert (PROJECT_ROOT / ".agents" / "skills" / "file-design-maintainer" / "SKILL.md").is_file()
    assert (PROJECT_ROOT / ".agents" / "skills" / "file-artifact-reviewer" / "SKILL.md").is_file()


def test_ui_skills_exist_and_use_the_command_line():
    for name in ["start-ui", "stop-ui", "upgrade-ui"]:
        skill = PROJECT_ROOT / ".agents" / "skills" / name / "SKILL.md"
        assert skill.is_file()
        text = skill.read_text()
        assert "python-cad" in text and ".opencode" not in text
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()
    assert ".makeitours/ui-server.pid" in gitignore and ".makeitours/ui-server.log" in gitignore


def test_agents_never_commit():
    for path in (PROJECT_ROOT / ".agents" / "agents").glob("*.md"):
        assert "never commit or push" in path.read_text(), path
    assert "No agent commits, pushes, or loads a commit tool" in (PROJECT_ROOT / "AGENTS.md").read_text()


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
