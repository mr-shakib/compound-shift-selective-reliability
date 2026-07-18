# Data Safety — C3-E

This document defines the handling rules for MIMIC-CXR / MIMIC-CXR-JPG and CheXpert Plus data within
this project. It applies to every researcher working in this workspace.

## Credentialing and authorization

- MIMIC-CXR, MIMIC-CXR-JPG, and CheXpert Plus are **credentialed datasets**. Access requires an
  approved PhysioNet (MIMIC) or Redivis/Stanford AIMI (CheXpert Plus) credentialing process, including
  a signed Data Use Agreement (DUA).
- **Each researcher must hold independent, personal authorization.** Credentials, access, and DUAs are
  not transferable. Do not share downloaded data, derived report text, or access tokens with anyone who
  has not independently completed credentialing for that dataset.
- Do not attempt to bypass PhysioNet, Stanford, Redivis, authentication, credentialing, or DUA
  requirements by any means.

## Where raw data may live

- Raw reports and images **must remain local** to authorized, credentialed machines/storage, under
  `c3e/data/mimic/` and `c3e/data/chexpert_plus/` (or another local path you control) — never in a
  location the DUA does not permit.
- Raw MIMIC or CheXpert Plus data — reports, report text, images, DICOM/image metadata, patient or
  study identifiers, or anything derived closely enough to reconstruct them — **must never be pasted
  into or uploaded to**:
  - ChatGPT, Claude, Codex, or any other hosted LLM/chat prompt
  - GitHub, GitLab, or any other version-control host
  - Email
  - Google Drive, Dropbox, OneDrive, or other cloud storage
  - Hosted notebooks (Colab, Kaggle, hosted Jupyter, etc.)
  - Any third-party API or SaaS platform not covered by the dataset's DUA

## What may be shared for analysis or discussion

Only the **permitted aggregate outputs** produced by the audit toolkit may be shared outside the local
credentialed environment (e.g., pasted into an analysis discussion, attached to an internal note):

- `summary.json`
- `section_availability.csv`
- `label_prevalence.csv`
- `leakage_by_label.csv`
- `missingness_by_label.csv`
- `gate_report.json`
- `cross_site_comparison.csv`
- `cross_site_gate.json`

These are aggregate, cohort-level statistics with no per-patient or per-report content.

## What must never be shared

The following are considered unsafe to share under any circumstances, including internally over
non-secure channels:

- `study_aggregate.csv` (row-level, one row per study — closer to raw structure)
- Raw report text, in whole or in part
- Patient identifiers
- Study identifiers
- Image identifiers
- Image files (JPG, PNG, DICOM, or any other format)

`scripts/collect_safe_outputs.sh` automates copying only the approved aggregate list into
`results/shareable_aggregates/` and explicitly excludes `study_aggregate.csv`. Use that script rather
than manually copying files, and always visually confirm the output list before sharing anything.

## General rules

- Keep all raw-data work local. Do not process raw clinical reports until you have independently
  verified you hold authorized local access.
- Do not place passwords, API keys, or access tokens inside scripts, config files, or code committed to
  version control. Use environment variables or a local, gitignored secrets file instead.
- The project `.gitignore` (see `c3e/.gitignore`) excludes data directories, sensitive aggregate files,
  raw image/report formats, and anything matching credential/secret/token patterns — but it is a
  safety net, not a substitute for careful judgment before running `git add`.
