# generated/

Disposable build output — not customer-owned, not infrastructure. Gitignored
except `.gitkeep` (see `.gitignore`); everything else here is produced by
`python-cad build` / `validate` / `verify` and safe to delete at any time.
Never hand-edit anything under this directory or rely on it being present in
a fresh checkout.

Current layout, keyed to the model's `artifact_stem` (`FileTemplate` for this
template):

- **`step/FileTemplate.step`**, **`ifc/FileTemplate.ifc`**,
  **`glb/FileTemplate.glb`** — the exported geometry, one file per format,
  each with a sibling `validation.json` (`step/`, `ifc/`) or `manifest.json`
  (`glb/`).
- **`drawings/`** — `svg/`, `pdf/`, `dxf/` outputs plus
  `annotation-manifest.json` (the drawing annotation provider's output).
- **`quantities/`** — `quantities.csv`/`.json`, `materials.csv`,
  `summary.md`.
- **`manifests/`** — `design-manifest.json` (model id, name, artifact stem,
  elements, semantic hash), `build-manifest.json` (the artifact set and its
  stable hash), `run-metadata.json`.

If this directory or its layout changes, this file no longer describes it —
trust `python-cad`'s own output over this description.
