"""Section 12.7: Determinism between two independent builds.

Both builds use step+ifc (Option 6b). Full-format determinism for GLB,
drawings, and quantities is covered by test_build_artifacts.py (single-build
consistency). With pytest-xdist --dist loadscope, this file runs on one worker
in parallel with other build test files (~104 s).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from conftest import _copy_project
from python_cad_tools.build import BuildOptions, build_project
from python_cad_tools.determinism import semantic_hash

pytestmark = [pytest.mark.integration]


@dataclass
class TwoBuilds:
    output1: Path
    manifest1: dict
    output2: Path
    manifest2: dict


FORMATS: tuple[str, ...] = ("step", "ifc")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def two_builds(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> TwoBuilds:
    """Two independent step+ifc builds for determinism comparison.

    Creates two clean project copies and builds each with the same format
    set (step+ifc) so artifact manifests are directly comparable.
    """
    # First build
    first_copy = tmp_path_factory.mktemp("determinism_first")
    _copy_project(repo_root, first_copy)
    build_project(BuildOptions(project_root=first_copy, formats=FORMATS))  # type: ignore[arg-type]
    output1 = first_copy / "generated"
    manifest1 = _load_json(output1 / "manifests" / "build-manifest.json")

    # Second build
    second_copy = tmp_path_factory.mktemp("determinism_second")
    _copy_project(repo_root, second_copy)
    build_project(BuildOptions(project_root=second_copy, formats=FORMATS))  # type: ignore[arg-type]
    output2 = second_copy / "generated"
    manifest2 = _load_json(output2 / "manifests" / "build-manifest.json")

    return TwoBuilds(output1=output1, manifest1=manifest1, output2=output2, manifest2=manifest2)


# ── 12.7 Failure rollback/recovery and determinism ──────────────────────────


def test_two_clean_builds_identical(two_builds) -> None:
    assert two_builds.manifest1["design_semantic_hash"] == two_builds.manifest2["design_semantic_hash"]
    known_non_deterministic = {
        "run-metadata.json",
        "build-manifest.json",
        "FileTemplate.step",
    }
    bm1_stable_excluding_step = semantic_hash(
        [
            e
            for e in two_builds.manifest1["artifacts"]
            if not e["volatile"] and not any(e["path"].endswith(name) for name in known_non_deterministic)
        ]
    )
    bm2_stable_excluding_step = semantic_hash(
        [
            e
            for e in two_builds.manifest2["artifacts"]
            if not e["volatile"] and not any(e["path"].endswith(name) for name in known_non_deterministic)
        ]
    )
    assert bm1_stable_excluding_step == bm2_stable_excluding_step, (
        "Stable artifact hash mismatch excluding known non-deterministic files"
    )
    arts1 = {e["path"]: e for e in two_builds.manifest1["artifacts"]}
    arts2 = {e["path"]: e for e in two_builds.manifest2["artifacts"]}
    assert set(arts1) == set(arts2), "Artifact paths differ between builds"
    for path_key, entry1 in arts1.items():
        entry2 = arts2[path_key]
        if any(entry1["path"].endswith(name) for name in known_non_deterministic):
            continue
        assert entry1["sha256"] == entry2["sha256"], f"SHA-256 mismatch for {path_key} between builds"


def test_deterministic_nonvolatile_bytes(two_builds) -> None:
    volatile_names = {"run-metadata.json", "build-manifest.json", "FileTemplate.step"}
    for entry1, entry2 in zip(two_builds.manifest1["artifacts"], two_builds.manifest2["artifacts"], strict=True):
        if Path(entry1["path"]).name in volatile_names:
            continue
        path1 = two_builds.output1 / entry1["path"]
        path2 = two_builds.output2 / entry2["path"]
        bytes1 = path1.read_bytes()
        bytes2 = path2.read_bytes()
        assert bytes1 == bytes2, f"Byte mismatch for {entry1['path']} between builds"
