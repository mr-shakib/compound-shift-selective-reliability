# C3-E Research Log

## Research domain

Reliable multimodal learning under incomplete, conflicting, and shifted evidence.

## Current candidate

External selective reliability of chest-X-ray and pre-diagnostic clinical-history models under cross-hospital context missingness.

## Dataset route

- Source: MIMIC-CXR / MIMIC-CXR-JPG
- External target: CheXpert Plus

## Current phase

C3-E3 — Protocol Lock and MIMIC Readiness

## Current status

- PhysioNet access requested.
- CheXpert Plus access granted; its full aggregate-safe audit passed and C3-E2 is frozen.
- MIMIC access remains pending; no MIMIC data has been processed.
- No image-model training is authorized.
- Audit toolkit installation status: installed successfully (editable install, `pip install -e .` into `.venv`).
- Toolkit test status: 2 passed (`pytest -q`), see `logs/toolkit_test.log`.

## Date

2026-07-18

## Actions completed

- Located the audit toolkit (both an extracted `c3e_audit_toolkit/` directory and `c3e_audit_toolkit.zip` were present at the base directory); used the pre-extracted directory directly per instructions.
- Created the full pre-access workspace tree under `c3e/` (`data/mimic`, `data/chexpert_plus`, `results/c3e_mimic`, `results/c3e_chexpert_plus`, `results/c3e_cross_site`, `docs/`, `logs/`, `scripts/`).
- Moved the toolkit into `c3e/c3e_audit_toolkit`.
- Created a Python virtual environment at `c3e/c3e_audit_toolkit/.venv`, upgraded pip/setuptools/wheel, and installed the toolkit in editable mode (`pip install -e .`).
- Installed `pytest` and ran the toolkit test suite: 2 passed, output saved to `c3e/logs/toolkit_test.log`.
- Created this research log, closest-work tracking files, terms review, data-safety controls, execution scripts, CheXpert Plus schema-mapping scaffold, manual access checklist, and decision-gate document (see corresponding files in `docs/` and `scripts/`).

## Evidence currently required

- Clinical-history availability at both institutions
- Low-information history rates
- Label prevalence
- Uncertain-label prevalence
- Direct target-term mention rates
- Missingness by label
- Patient-level split integrity
- Cross-hospital context-distribution differences

## Current restrictions

- No raw medical data may be uploaded to external services.
- No large image download is authorized.
- No model development is authorized.
- Novelty is not yet confirmed.

## Next action

When MIMIC access arrives, verify individual access and DUA status, then download and checksum only
the authorized reports and metadata before any local parsing. Image download and model training remain
unauthorized.

## Session update — 2026-07-15 (schema metadata reviewed)

- Reviewed a local Redivis dataset schema export for CheXpert Plus
  (`<local-research-workspace>/chexpert_plus.json`), the dataset's own
  published metadata from `https://stanford.redivis.com/datasets/5yyj-1a9f6ap0x`. Contains table/column
  names and types only — no patient records, report text, images, or identifiers.
- This confirmed real column names in the main table `df_chexpert_plus_240401` (223,462 rows): patient
  ID is `deid_patient_id`; context/history fields are `section_clinical_history` and `section_history`;
  view info is split across `ap_pa` and `frontal_lateral`; a `split` column exists.
- No dedicated study or image identifier column was found, and no explicit "indication" column exists.
  The pathology label columns remain unknown — the `chexpert_labels` table in the schema export is
  itself a file index, not an expanded column list.
- Updated `c3e_audit_toolkit/configs/chexpert_plus.yaml` and `docs/CHEXPERT_SCHEMA_MAPPING.md` to
  reflect these schema-confirmed (not yet row-value-confirmed) mappings; several fields remain `TODO` /
  `pending` (study ID, image ID, label columns, exact string encodings).
- This is schema-level confirmation only — no row-level CheXpert Plus data has been accessed, and the
  audit still cannot be run until the remaining TODOs are resolved with real row-level access.

## Session update — 2026-07-18 (C3-E2 closure and C3-E3 protocol lock)

- Froze the completed CheXpert Plus aggregate audit: 191,071 frontal images and 187,674 frontal
  studies; combined usable pre-diagnostic context 60.3%; natural absent/low-information context 39.7%.
- Confirmed all five target labels are viable, direct target leakage is low, and patient → study →
  image hierarchy plus label joins are clean.
- Locked impression-derived labels as primary, findings-derived labels as mandatory sensitivity, and
  prohibited report-derived labels. Cardiomegaly prevalence is label-source-sensitive and must be
  highlighted.
- Recorded that these are **CheXpert Plus feasibility-audit findings, not final model results**.
- Locked external-validation roles (MIMIC development, CheXpert external), six hypotheses, the
  statistical analysis plan, and the sequential MIMIC intake/readiness protocol.
- Authorized MIMIC reports/metadata intake only after access/DUA verification. No images, MIMIC
  processing in this session, external API use, statistical tests, or model training occurred.
