# CheXpert Plus Multiple-Image Analysis Policy — PREREGISTRATION

Status: **LOCKED 2026-07-18, before the complete audit results were inspected.** This
document fixes the observation unit, weighting, uncertainty, and sensitivity policies for the
CheXpert Plus analyses. It was written and committed *prior* to running the full impression /
findings audits (Tasks 4–6 of C3-E2), so none of the choices below are contingent on observed
outcomes. Any later deviation must be recorded as a dated amendment, not a silent edit.

Companion docs: `CHEXPERT_CONFIG_DECISION.md`, `CHEXPERT_JOIN_AUDIT.md`,
`CHEXPERT_SCHEMA_MAPPING.md`, `LABEL_HARMONIZATION_PLAN.md`.

## Verified structural context (from prior C3-E2 work)

- Main table is image-level: one row per image; `path_to_image` is row-unique.
- Derived study key = `patient_folder + study_folder` (from `path_to_image`, `PurePosixPath`):
  187,711 studies (= official count), 0 parse failures.
- Patient key: `deid_patient_id` (64,725 patients). Study key maps cleanly within patient
  (0 multi-patient / multi-split studies).
- 3,356 studies (1.8%) carry more than one **frontal** image; median 1 frontal image/study.

## Primary analysis

- **Observation unit:** frontal image (`frontal_lateral == "Frontal"`).
- **Patient grouping unit:** `deid_patient_id`.
- **Study cluster:** derived `patient_folder + study_folder`.
- **Retain all frontal images.** Do **not** aggregate labels. Do **not** choose a single image.
- **Study-equal weighting.** For every study with `m` included frontal images, each of that
  study's images receives weight `1/m`. Every study therefore contributes total weight exactly
  `1`. Weighted statistics (prevalence, context rates) use these image weights so that a study
  with many frontal images does not dominate a single-image study.

Rationale: images within a study share one report and are correlated; study-equal weights make
each study count once while still retaining every image (no information discarded, no arbitrary
selection).

## Primary uncertainty policy

For inferential evaluation **later** (not in this descriptive audit), use a
**patient-clustered bootstrap**:

- Resample **patients** with replacement.
- For each sampled patient, retain **all** of that patient's studies and images (whole cluster
  kept intact — never resample images independently).
- Fixed, documented random seed.
- **≥ 1,000 replicates** in final model evaluation.

Independent per-image bootstrap is explicitly prohibited (it would understate correlation-driven
uncertainty).

## Sensitivity A — unweighted image level

Repeat the primary descriptive statistics with **unweighted** image-level counts over all
frontal images (each image weight 1). Reveals how much study-equal weighting moves estimates.

## Sensitivity B — one frontal image per study

Reduce each study to a **single** frontal image using a deterministic, **label-blind** rule:

1. Select the image with the **lowest parsed view number** (the integer in the `viewN_...`
   filename component).
2. Break any unresolved tie by **stable lexical ordering** of the filename component,
   internally only.
3. **Never** use labels, report text, pathology, image quality, or any model output.

Selected paths / identifiers are never exposed; only aggregate results over the reduced set are
reported.

## Sensitivity C — target-specific concordant-study subset

For **each target label separately**, build a concordant subset:

- **Include** every single-frontal-image study.
- **Include** a multi-frontal-image study **only if all observed (non-null) labels for that
  specific target agree** across its frontal images.
- **Exclude** a multi-frontal study from a target's concordant subset **only for that target**
  when its frontal images disagree on that target (a study excluded for Cardiomegaly may still
  be included for Edema).
- Report the excluded counts and percentages per target.
- Do **not** use any-positive, majority vote, or any forced label aggregation. Concordance is a
  filter, not an aggregation.

## Locking statement

All four policies (primary + A/B/C) and the bootstrap specification above were fixed here
**before** the audit outputs in `results/c3e_chexpert_plus/` were generated or read. The same
policies apply identically to the impression (primary) and findings (sensitivity) label sources.

## Post-hoc note (2026-07-18, after results)

The audits were subsequently run under exactly these policies (`CHEXPERT_FULL_AUDIT_REPORT.md`).
Outcome relevant to the policy: the multiple-image policy choice barely matters — within-study
label disagreement among the 3,356 multi-frontal studies is ≤ 0.09%, and the positive-prevalence
shift across the primary / unweighted / one-image / concordant policies is < 0.1 percentage point
for every target. The preregistered primary (study-equal-weighted, all frontal images retained)
therefore stands, with A/B/C confirming robustness rather than changing conclusions. No policy was
altered after seeing results; the patient-clustered bootstrap (≥ 1,000 replicates) remains
specified for the later inferential evaluation and was not run in this descriptive audit.
