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
- ~~Novelty is not yet confirmed.~~ **Partially addressed 2026-08-03**; see the
  session update below. Three closest-work rows are verified and none anticipates
  the crossed design; five candidates remain unverified.

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

## Session update — 2026-07-18 (C3-E4 provenance repair)

- Confirmed the project-root `.git` entry was absent, initialized a local repository on `main`, and
  created baseline commit `6b02a62de50ffe36fc336eb3201ababbd109f19b` from an explicit 76-file
  allowlist after staged-name, size, identifier/path, secret, and long-line scans passed.
- Hardened `.gitignore`; verified the main CheXpert Parquet and three raw label files are ignored.
- Removed local absolute workspace paths from tracked historical Markdown; clearly synthetic test
  identifiers remain only in a test file that declares all fixtures synthetic.
- Locked the final patient-clustered bootstrap to 2,000 replicates, seed 20260718, and primary 95%
  percentile intervals before model results.
- Added provenance/versioning and CheXbert artifact-pinning policies. No raw data, MIMIC processing,
  image download, model training, CheXbert download/execution, external API, or upload occurred.

## Session update — 2026-08-03 (Stages 4 and 5 complete; protocol v0.4.0; novelty check opened)

- **Stage 4 full-cohort labels.** CheXbert generated labels for 173,572 impression studies
  (100% of cohort) and 110,740 findings studies (63.80%), 48m38s on one consumer GPU. The port
  passed its fidelity gate 56/56 against upstream reference labels before any project label was
  written. The prespecified label-source sensitivity reproduced at scale: Cardiomegaly shows the
  largest impression-versus-findings gap of the five targets (15.43% vs 22.74%), the pattern the
  C3-E2 audit flagged when findings-derived labels were made a mandatory sensitivity analysis.
  A labeller property worth carrying into Methods: CheXbert almost never assigns explicit
  *negative* to Atelectasis (590 negatives against 31,974 positives), and the same holds at the
  external site, so it is a labeller artefact rather than a MIMIC one.
- **Stage 5 image acquisition.** All 193,282 frontal JPGs acquired, 318.5 GB, every tier complete.
  The PhysioNet HTTP endpoint proved unusable for bulk transfer (0.15 MB/s against a 27 MB/s link,
  then a 403 block after an hour); the cause is structural, a single origin at 331 ms round trip
  serving ~1.8 MB objects that finish before TCP slow-start opens the window. Transfer moved to
  the PhysioNet S3 access point.
- **Integrity.** Every image was hashed against the publisher's `SHA256SUMS.txt`: 193,282 of
  193,282 match, zero unresolved mismatches. One file failed the first pass as a truncated object
  left by an interrupted transfer; the resume check had tested non-emptiness rather than
  completeness, so a retry skipped rather than repaired it. Re-fetched and re-verified. A checksum
  pass after any resumed transfer is therefore mandatory, not optional.
- **Protocol v0.4.0.** `models.exact_backbones` resolved from `PENDING_HARDWARE_GATE`:
  DenseNet-121 / ImageNet / 224px image arm, BERT-base-uncased / 128 tokens text arm, probability
  averaging for M3, pooled-feature concatenation for M4, with optimisation and early-stopping
  settings fixed alongside. The gate is a single 6 GB consumer GPU. Recorded as prespecified: no
  model trained, no metric computed, no external result inspected. Nothing remains pending in the
  protocol. Validator passes 30/30.
- **Novelty check opened.** `closest_work.csv` had never been populated. Three rows are now
  verified against full text or the official page. CW01 (selective classification under
  distribution shift) is the closest methodological neighbour but uses no clinical data and no
  cross-hospital transfer. CW02 (Yang, Wan and Pan, 2025) establishes that clinical history helps
  CXR classification but is single-institution with held-out splits only, and has no abstention,
  no leakage audit and no calibration transfer — it is a premise paper, not a competitor. Five
  candidates remain `unverified` and must be inspected before results are written up.
- Nothing observed so far anticipates the crossed institution-by-context design, the frozen
  source-to-external threshold transfer, or the report-structure hazards recorded in Stage 3B.
- No model was trained, no threshold selected, no metric computed, and no external-site result
  inspected in this session.
