"""Section 12.7: Determinism between two independent builds.

Both builds use step+ifc (Option 6b): the session's shared CLI and API builds
(conftest.py). Full-format determinism for GLB, drawings, and quantities is
covered by test_build_artifacts.py (single-build consistency).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from python_cad_tools.determinism import semantic_hash

pytestmark = [pytest.mark.integration]


@dataclass
class TwoBuilds:
    output1: Path
    manifest1: dict
    output2: Path
    manifest2: dict


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def two_builds(cli_step_ifc_project: Path, api_step_ifc_project: Path) -> TwoBuilds:
    """Two independent clean step+ifc builds: the shared CLI build and the shared API build.

    Each comes from its own clean project copy; comparing a CLI build with an API build
    also shows the two entry points produce the same artifacts.
    """
    output1 = cli_step_ifc_project / "generated"
    output2 = api_step_ifc_project / "generated"
    return TwoBuilds(
        output1=output1,
        manifest1=_load_json(output1 / "manifests" / "build-manifest.json"),
        output2=output2,
        manifest2=_load_json(output2 / "manifests" / "build-manifest.json"),
    )


# ── 12.7 Failure rollback/recovery and determinism ──────────────────────────


def test_two_clean_builds_identical(two_builds, identity) -> None:
    assert two_builds.manifest1["design_semantic_hash"] == two_builds.manifest2["design_semantic_hash"]
    known_non_deterministic = {
        "run-metadata.json",
        "build-manifest.json",
        f"{identity.stem}.step",
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


def test_deterministic_nonvolatile_bytes(two_builds, identity) -> None:
    volatile_names = {"run-metadata.json", "build-manifest.json", f"{identity.stem}.step"}
    for entry1, entry2 in zip(two_builds.manifest1["artifacts"], two_builds.manifest2["artifacts"], strict=True):
        if Path(entry1["path"]).name in volatile_names:
            continue
        path1 = two_builds.output1 / entry1["path"]
        path2 = two_builds.output2 / entry2["path"]
        bytes1 = path1.read_bytes()
        bytes2 = path2.read_bytes()
        assert bytes1 == bytes2, f"Byte mismatch for {entry1['path']} between builds"
