# C3-E Setup Status

Date: 2026-07-15

## Workspace path

`${PROJECT_ROOT}` (the local `c3e/` project directory).

(Note: the task instructions referenced `~/research/c3e` in several places, but an explicit override at
the top of the request redirected all paths to the location above. This report reflects the actual
location used.)

## Toolkit installation status

- Source: an already-extracted `c3e_audit_toolkit/` directory was found alongside
  `c3e_audit_toolkit.zip` directly in the local research workspace. Per instructions, the pre-extracted
  directory was used directly (not re-extracted from the ZIP) and moved into
  `c3e/c3e_audit_toolkit`. The ZIP file was left in place at the base directory, unmodified.
- Virtual environment created at `c3e/c3e_audit_toolkit/.venv`.
- `pip`, `setuptools`, `wheel` upgraded (pip 25.1.1 → 26.1.2).
- Installed in editable mode via `pip install -e .` — succeeded (`c3e-audit-0.1.0`), pulling in
  `pandas`, `numpy`, `pyyaml`, `python-dateutil`, `six`.
- `pytest` installed (9.1.1) since it was not already available.

## Python version

```
Python 3.14.4
```

## Test result

```
2 passed in 0.21–0.25s
```

Full output saved to `c3e/logs/toolkit_test.log`. Both tests passed with no modification to the test
suite or source code.

## Files created

- `docs/research_log.md`
- `docs/closest_work.csv` (header-only, columns verified to match spec exactly)
- `docs/closest_work_README.md`
- `docs/terms_review.md`
- `docs/DATA_SAFETY.md`
- `docs/CHEXPERT_SCHEMA_MAPPING.md`
- `docs/MANUAL_ACCESS_TASKS.md`
- `docs/C3E_DECISION_GATE.md`
- `docs/SETUP_STATUS.md` (this file)
- `.gitignore`
- `c3e_audit_toolkit/configs/chexpert_plus.yaml` (draft, copied from `chexpert_plus.example.yaml` with
  `TODO` comments on every field requiring real-schema verification)
- `logs/toolkit_test.log`

## Scripts created

All under `c3e/scripts/`, all executable (`chmod +x`), all use `set -euo pipefail`:

- `check_environment.sh` — verified working; prints a readiness summary
- `run_mimic_audit.sh` — verified to fail clearly (non-zero exit, explicit error message) when input
  files are absent; not run against real data (none available yet)
- `run_chexpert_audit.sh` — same validation behavior verified
- `run_cross_site_comparison.sh` — same validation behavior verified
- `collect_safe_outputs.sh` — verified against synthetic demo output (see Validation notes below);
  correctly excludes `study_aggregate.csv` and fails loudly if an expected safe output is missing for a
  site whose audit has actually run

## Files modified

- None outside of files created by this setup. No pre-existing files in the base directory were
  altered. `c3e_audit_toolkit.zip` at the base directory was left untouched.

## Validation performed

- `check_environment.sh` run: all checks passed (Python present, disk space ample, toolkit and venv
  present, `c3e-audit` installed, tests passed, all expected directories present).
- `pytest -q` run directly: 2 passed.
- YAML syntax validated (via `yaml.safe_load`) for `configs/mimic.yaml`, `configs/chexpert_plus.yaml`,
  `configs/chexpert_plus.example.yaml`, `configs/terms.yaml` — all valid.
- CSV header of `docs/closest_work.csv` compared programmatically against the required column list —
  exact match.
- `collect_safe_outputs.sh` smoke-tested by temporarily copying the toolkit's own synthetic
  `demo/output/` files (non-PHI, shipped with the toolkit) into `results/c3e_mimic/`, confirming
  `study_aggregate.csv` was correctly excluded and all six approved aggregate files were copied, then
  removing the test copies to restore the pristine empty `results/` scaffolding.
- Confirmed `data/mimic/` and `data/chexpert_plus/` are empty and no credentialed or PHI-like data
  exists anywhere in the workspace.
- `shellcheck` was **not** run — it is not installed on this machine, and per instructions system
  packages are not installed without asking first. See "Failed or skipped tasks" below.

## Unresolved errors

None. All setup steps completed successfully.

## Manual actions still required

See `docs/MANUAL_ACCESS_TASKS.md` for the full checklists. Summary: PhysioNet credentialing (account,
CITI training, DUAs, approval, report/metadata download) and CheXpert Plus access (Stanford AIMI /
Redivis account, terms review, table inspection, table download) are both outstanding and require
browser-based, account-level actions that cannot be automated here.

## Exact next command to run after MIMIC access is granted

```bash
MIMIC_REPORTS=/path/to/mimic-cxr-reports.zip \
MIMIC_LABELS=/path/to/mimic-cxr-2.0.0-chexpert.csv.gz \
MIMIC_METADATA=/path/to/mimic-cxr-2.0.0-metadata.csv.gz \
MIMIC_SPLITS=/path/to/mimic-cxr-2.0.0-split.csv.gz \
./scripts/run_mimic_audit.sh
```

## Exact next command to run after CheXpert Plus metadata are prepared

First complete `docs/CHEXPERT_SCHEMA_MAPPING.md` and resolve every `TODO` in
`c3e_audit_toolkit/configs/chexpert_plus.yaml`, then:

```bash
CHEXPERT_TABLE=/path/to/chexpert_plus_merged.parquet \
./scripts/run_chexpert_audit.sh
```

Then, once both audits have produced `study_aggregate.csv`:

```bash
./scripts/run_cross_site_comparison.sh
```

## Important note

This setup prepared only the **local pre-access environment** — directory structure, toolkit
installation, test verification, documentation scaffolding, safety controls, and execution scripts. No
credentialed dataset (MIMIC-CXR, MIMIC-CXR-JPG, or CheXpert Plus) has been accessed, downloaded, or
processed, and no dataset audit has actually been run. No claims are made about label prevalence,
context availability, leakage rates, or C3-E gate outcomes — those require real credentialed data and
have not been computed.
