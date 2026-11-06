"""Section 12.7: Determinism between two independent builds.

The session's two shared builds (conftest.py) are independent clean builds of
their own project copies: the CLI step+ifc build and the full API build. Their
step and ifc output is compared, which also shows the two entry points produce
the same artifacts. Full-format determinism for GLB, drawings, and quantities is
covered by test_build_artifacts.py (single-build consistency).

2026-11-06 (makeitours-data-plane#293): the full build replaced a separate API
step+ifc build here; building only step and ifc writes those files byte for byte
the same as building every format.
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
def two_builds(cli_step_ifc_project: Path, full_build) -> TwoBuilds:
    """Two independent clean builds: the shared CLI step+ifc build and the shared full API build,
    each from its own clean project copy. The full build's manifest is narrowed to the paths
    the step+ifc build wrote."""
    output1 = cli_step_ifc_project / "generated"
    output2 = full_build.project / "generated"
    manifest1 = _load_json(output1 / "manifests" / "build-manifest.json")
    manifest2 = _load_json(output2 / "manifests" / "build-manifest.json")
    cli_paths = {e["path"] for e in manifest1["artifacts"]}
    full_paths = {e["path"] for e in manifest2["artifacts"]}
    assert cli_paths <= full_paths, (
        f"The step+ifc build wrote artifacts the full build did not: {cli_paths - full_paths}"
    )
    manifest2 = {**manifest2, "artifacts": [e for e in manifest2["artifacts"] if e["path"] in cli_paths]}
    return TwoBuilds(output1=output1, manifest1=manifest1, output2=output2, manifest2=manifest2)


# ── 12.7 Failure rollback/recovery and determinism ──────────────────────────


def test_two_clean_builds_identical(two_builds, identity) -> None:
    assert two_builds.manifest1["design_semantic_hash"] == two_builds.manifest2["design_semantic_hash"]
    known_non_deterministic = {
        "run-metadata.json",
        "build-manifest.json",
        f"{identity.stem}.step",
    }

    def stable(manifest: dict) -> str:
        return semantic_hash(
            sorted(
                (
                    e
                    for e in manifest["artifacts"]
                    if not e["volatile"] and not any(e["path"].endswith(name) for name in known_non_deterministic)
                ),
                key=lambda e: e["path"],
            )
        )

    assert stable(two_builds.manifest1) == stable(two_builds.manifest2), (
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
    for entry in two_builds.manifest1["artifacts"]:
        if Path(entry["path"]).name in volatile_names:
            continue
        bytes1 = (two_builds.output1 / entry["path"]).read_bytes()
        bytes2 = (two_builds.output2 / entry["path"]).read_bytes()
        assert bytes1 == bytes2, f"Byte mismatch for {entry['path']} between builds"
