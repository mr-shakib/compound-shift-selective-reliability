# Phase C3-E4 Closure — Provenance Repair and Final Pre-Experiment Lock

Status: **COMPLETE / GO FOR CONDITIONAL MIMIC REPORT-METADATA INTAKE**

Closure date: **2026-07-18**

## Provenance status

The missing Git provenance limitation is repaired. The project now has a valid local repository with
raw-data exclusions, an explicit staging policy, a reviewed baseline commit, and a locked provenance
policy. The repair used local operations only; no remote, upload, external API, raw-data edit, model
training, CheXbert run, or MIMIC processing occurred.

## Git repository and baseline

- Previous project-root Git state: `.git` absent.
- Current repository: valid Git repository.
- Branch: `main`.
- Baseline commit: `6b02a62de50ffe36fc336eb3201ababbd109f19b`.
- Baseline commit date: `2026-07-18T17:14:17+06:00`.
- Baseline committed files: 76.
- Baseline message: `C3E: freeze CheXpert audit and preregister cross-site protocol`.
- Baseline staged safety result: pass; 348,948 committed bytes, largest file 26,352 bytes, no
  prohibited staged filename, private absolute path, secret value, or raw-data artifact.
- Synthetic verification before baseline: 39 tests passed.

The baseline was created with explicit file paths. No unrestricted `git add .` was used.

## Raw-data exclusion status

`.gitignore` excludes the complete data tree, Parquet, JSONL, DICOM, medical image formats, the three
raw CheXpert label filenames, archives, model weights/checkpoints, environments, caches, credentials,
tokens, cookies, signed URLs, private manifests/row-level exports, and raw logs. It does not globally
exclude safe JSON or CSV aggregates.

Before staging, `git check-ignore` passed for the CheXpert main Parquet table and
`findings_fixed.json`, `impression_fixed.json`, and `report_fixed.json`. No raw medical data or
identifier-level export was staged or committed.

## Hash and amendment provenance

`C3E2_ARTIFACT_HASHES.sha256` predates Git initialization and remains unchanged as the historical
pre-Git phase manifest. C3-E4 amendments do not rewrite it. The baseline commit and subsequent
provenance-lock commit record the version transition. Frozen CheXpert aggregate outputs were not
recomputed or edited.

## Bootstrap policy lock

- Unit: patient.
- Cluster contents: retain all eligible studies and images for each resampled patient.
- Final valid replicates: **2,000**.
- Random seed: **20260718**.
- Interval: two-sided 95% percentile bootstrap.
- Optional sensitivity: BCa only after technical validation and when computationally feasible.

These settings were fixed before model training or model results. No bootstrap was run in C3-E4.

## CheXbert pinning readiness

`CHEXBERT_ARTIFACT_PINNING_PLAN.md` defines the required code, checkpoint, tokenizer, package,
preprocessing, ontology, determinism, execution, and checksum record. Readiness is **plan-complete but
artifact-pending**. No CheXbert artifact was downloaded or executed.

The exact upstream checkpoint provenance of supplied CheXpert Plus labels is not assumed. Primary
cross-site harmonization requires verified upstream equivalence or separately authorized local
relabelling of both sites with one pinned pipeline.

## Items requiring MIMIC access

- Verify individual access, training, and DUA status.
- Obtain and checksum the authorized reports/metadata-only inputs.
- Verify MIMIC schema, patient/study/image hierarchy, joins, and split integrity.
- Audit Clinical History availability and low-information context locally.
- Validate Findings/Impression parsing without cloud processing.
- Pin CheXbert artifacts and establish exact cross-site labeler harmonization.
- Compare aggregate label/context distributions and run the MIMIC/cross-site data-validity gates.

## Authorization boundary

- MIMIC reports/metadata intake: **conditionally authorized after access/DUA, disk-space, and checksum
  verification**, following the sequential intake protocol.
- MIMIC processing now: **prohibited**.
- Image downloading: **prohibited; requires a passed MIMIC gate and separate dated authorization**.
- Model training: **prohibited; requires later explicit authorization**.
- CheXbert download/execution: **prohibited in this phase**.
- External-result tuning or CheXpert-driven decisions: **prohibited**.

## Verdict

**GO** for provenance-complete protocol readiness and conditional reports/metadata intake after
authorized access arrives. This is not a GO for images, labeling execution, training, statistical
evaluation, or cross-site claims.
