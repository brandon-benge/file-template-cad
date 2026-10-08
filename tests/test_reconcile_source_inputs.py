"""tools/reconcile-infrastructure keeps each project's [tool.python-cad] source-inputs
(2026-10-08 approval, Amendment 2): the design files a project actually has stay listed in its
own order, so reconciling never breaks `python-cad validate`. Design files themselves are never
touched. The app's InfrastructureReconciler applies the same rule."""

import importlib.machinery
import importlib.util
import subprocess
import tomllib
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "reconcile-infrastructure"


def _load():
    loader = importlib.machinery.SourceFileLoader("reconcile_infrastructure", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


reconcile = _load()
TEMPLATE_LIST = [
    "config.py",
    "drawing_annotations.py",
    "model.py",
    "models/__init__.py",
    "models/starter_model.py",
    "pyproject.toml",
]
BENGE_LIST = [
    "config.py",
    "drawing_annotations.py",
    "model.py",
    "models/__init__.py",
    "models/shared.py",
    "models/builder.py",
    "models/roof.py",
    "models/pool.py",
    "pyproject.toml",
]


def test_a_multi_module_project_keeps_its_list_and_order():
    on_disk = sorted(BENGE_LIST[:-1])
    assert reconcile.merged_source_inputs(BENGE_LIST, TEMPLATE_LIST, on_disk) == BENGE_LIST


def test_a_fresh_template_project_is_unchanged():
    on_disk = sorted(TEMPLATE_LIST[:-1])
    assert reconcile.merged_source_inputs(TEMPLATE_LIST, TEMPLATE_LIST, on_disk) == TEMPLATE_LIST


def test_a_new_module_is_appended_and_a_deleted_one_dropped():
    on_disk = sorted([*BENGE_LIST[:-1], "models/spa.py"])
    on_disk.remove("models/pool.py")
    merged = reconcile.merged_source_inputs(BENGE_LIST, TEMPLATE_LIST, on_disk)
    assert "models/pool.py" not in merged
    assert merged[-1] == "models/spa.py"
    assert merged[: merged.index("pyproject.toml") + 1] == [entry for entry in BENGE_LIST if entry != "models/pool.py"]


def test_template_owned_entries_follow_the_template():
    template = [*TEMPLATE_LIST, "requirements/extra.txt"]
    merged = reconcile.merged_source_inputs([*BENGE_LIST, "old-tooling.cfg"], template, sorted(BENGE_LIST[:-1]))
    assert "requirements/extra.txt" in merged and "old-tooling.cfg" not in merged
    assert "models/starter_model.py" not in merged


@pytest.fixture
def template_and_project(tmp_path):
    template = tmp_path / "template"
    project = tmp_path / "project"
    for root in (template, project):
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    (template / "pyproject.toml").write_text(pyproject)
    (template / "README.md").write_text("template\n")
    subprocess.run(["git", "-C", str(template), "add", "-A"], check=True)
    benge_block = "source-inputs = [\n" + "".join(f'  "{entry}",\n' for entry in BENGE_LIST) + "]"
    start = pyproject.index("source-inputs = [")
    end = pyproject.index("]", start) + 1
    (project / "pyproject.toml").write_text(pyproject[:start] + benge_block + pyproject[end:])
    for entry in BENGE_LIST[:-1]:
        (project / entry).parent.mkdir(parents=True, exist_ok=True)
        (project / entry).write_text(f"# {entry}\n")
    subprocess.run(["git", "-C", str(project), "add", "-A"], check=True)
    return template, project


def test_reconcile_keeps_the_projects_list_and_never_touches_design_files(template_and_project, monkeypatch):
    template, project = template_and_project
    before = {entry: (project / entry).read_text() for entry in BENGE_LIST[:-1]}
    pyproject_before = (project / "pyproject.toml").read_text()
    monkeypatch.chdir(project)
    assert reconcile.main(["reconcile-infrastructure", str(template)]) == 0
    assert (project / "pyproject.toml").read_text() == pyproject_before
    assert tomllib.loads(pyproject_before)["tool"]["python-cad"]["source-inputs"] == BENGE_LIST
    assert {entry: (project / entry).read_text() for entry in BENGE_LIST[:-1]} == before
    assert (project / "README.md").read_text() == "template\n"
