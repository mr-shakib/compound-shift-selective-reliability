# Phase C3-E2 Closure — CheXpert Plus Feasibility Audit

Status: **FROZEN / PASSED**

Closure date: **2026-07-18**

Baseline Git commit: **`6b02a62de50ffe36fc336eb3201ababbd109f19b`**

Branch: **`main`**

Baseline commit date: **2026-07-18T17:14:17+06:00**

The project did not contain a Git repository when C3-E2 originally closed. C3-E4 repaired that
limitation by initializing a repository and creating the baseline commit above with an explicit
76-file safety allowlist. The original content freeze remains recorded in
`results/c3e_chexpert_plus/C3E2_ARTIFACT_HASHES.sha256`.

This closure freezes the aggregate-safe C3-E2 evidence and decisions. It does not authorize raw-data
processing, image download, model training, or cross-site claims.

## Phase objectives

1. Verify the CheXpert Plus patient → study → image hierarchy and all label joins.
2. Quantify availability and quality of permitted pre-diagnostic context.
3. Establish viability of the five target pathologies without direct target leakage.
4. approve a primary label source and a mandatory label-source sensitivity endpoint.
5. Lock an analysis policy for studies containing multiple frontal images.
6. determine whether CheXpert Plus is viable as the external institution for the planned study.
7. Produce only aggregate-safe evidence and preserve remaining cross-site questions for MIMIC intake.

## Verified findings

- Analysis cohort: **191,071 frontal images from 187,674 frontal studies**.
- Combined permitted context (`section_clinical_history` + `section_history`) is usable for **60.3%**
  of frontal images (60.1% study-equal weighted).
- Natural context absence (**21.5%**) plus low-information context (**18.2%**) totals **39.7%**.
- Cardiomegaly, Edema, Pleural Effusion, Atelectasis, and Consolidation are viable under both
  impression-derived and findings-derived labels, with thousands of positives per target.
- Direct target mention among positive labels is low for every target (maximum observed **3.84%**).
- `path_to_image` is a complete one-to-one image/label join: no duplicates, no unmatched rows, and
  expansion factor 1.0.
- The derived study key `patient_folder + study_folder` is valid; the patient → study → image
  hierarchy is clean, with zero parse failures and zero multi-patient or multi-split studies.
- The official train/valid split has zero patient overlap. Its valid subset is too small to serve as
  the primary development or evaluation split.
- Multiple-image-policy sensitivity is negligible: maximum prevalence movement is below 0.1
  percentage point for every target and label source.
- Context missingness is label-associated (maximum observed state-wise absent-fraction spread 0.104);
  this is an association and not a causal result.
- Cardiomegaly has a notable impression-versus-findings prevalence difference (15.2 percentage
  points among known labels); the other four targets differ by at most 4.5 percentage points.
- Safe-output scanning passed. Cross-site feasibility remains untested because MIMIC access is
  pending.

These are **CheXpert Plus feasibility-audit findings, not model-performance or clinical results**.

## Gate record

| Gate | Result | Decision |
|---|---|---|
| Combined usable context ≥40% | 60.3% | **PASS / GO** |
| Natural absent or low-information context ≥5% | 39.7% | **PASS / GO** |
| At least three viable targets | five under both sources | **PASS / GO** |
| At least 200 positives per viable target | minimum 3,520 | **PASS / GO** |
| Direct positive-label mention ≤70% | maximum 3.84% | **PASS / GO** |
| Patient-level split separation | zero overlap | **PASS / GO** |
| Join and hierarchy integrity | verified | **PASS / GO** |
| Multiple-image sensitivity small | <0.1 percentage point | **PASS / GO** |
| Aggregate-output safety | scan clean | **PASS / GO** |
| Label-source comparability | both viable; Cardiomegaly gap | **PASS WITH MANDATORY SENSITIVITY / MODIFY** |
| Label-independent context availability | association present | **NOT SATISFIED AS AN ASSUMPTION / MODIFY ANALYSIS** |
| Cross-site context shift | MIMIC unavailable | **BLOCKED / NOT EVALUATED** |

No executed CheXpert local gate failed. “Blocked / not evaluated” is not recorded as a pass or a
failure. It prevents a final cross-site dataset-route decision.

## Label-source lock

- **GO — primary:** impression-derived labels (`impression_fixed.json`).
- **GO — mandatory sensitivity:** findings-derived labels (`findings_fixed.json`).
- **REJECT — prohibited:** report-derived labels (`report_fixed.json`) because the report scope
  contains the permitted model-input context and would create direct input-target circularity.
- Findings and Impression are forbidden model inputs. Only pre-diagnostic history/context fields may
  be model inputs.

## Multiple-image policy lock

The prediction unit remains the frontal image. The primary analysis retains every frontal image,
does not aggregate labels, and gives each study total weight 1 (each of its `m` included images has
weight `1/m`). Study dependence must be respected and final uncertainty must use a patient-clustered
bootstrap. Mandatory sensitivities are unweighted image-level analysis, deterministic label-blind
one-frontal-image-per-study selection, and target-specific concordant-study restriction. The audit
did not justify changing this preregistered policy.

## Exact phase decisions

- **GO:** close C3-E2 as passed and freeze its aggregate-safe artifacts.
- **GO:** retain CheXpert Plus as the external evaluation institution.
- **GO:** proceed to C3-E3 protocol lock and to MIMIC reports/metadata intake after access and DUA
  verification.
- **MODIFY:** all later analyses must stratify context as usable, absent, and low-information; account
  for label-associated missingness; and present findings-derived labels as a mandatory sensitivity.
- **MODIFY:** Cardiomegaly conclusions require explicit label-source sensitivity reporting.
- **MODIFY:** use study-equal weighting with patient-clustered uncertainty and the locked
  multiple-image sensitivities.
- **REJECT:** report-derived targets, per-image independent bootstrap, CheXpert-driven tuning, and
  the official CheXpert valid split as the primary development split.
- **DEFER:** the final GO/MODIFY/REJECT decision for the cross-site dataset route until MIMIC passes
  its data-validity and harmonization gates.

## Unresolved risks and decisions

- MIMIC access/DUA status, schema, hierarchy, Clinical History availability, label distributions,
  patient split integrity, and context shift have not been verified.
- Cross-site label harmonization requires local CheXbert runs on MIMIC Findings and Impression.
- CheXpert context missingness is label-associated and may bias subgroup comparisons.
- Cardiomegaly is sensitive to label-source scope.
- Findings-derived labels are sparse, so sensitivity estimates may have wider uncertainty.
- Git provenance is now available from the C3-E4 baseline commit. The original C3-E2 manifest remains
  the content-integrity anchor for the pre-Git phase snapshot.
- Model selection, operating thresholds, calibration, and stopping rules remain future MIMIC-only
  decisions. No model training is authorized by this closure.

## Frozen evidence

Primary narrative evidence is in `CHEXPERT_FULL_AUDIT_REPORT.md`; policy and provenance are in
`CHEXPERT_CONFIG_DECISION.md`, `CHEXPERT_MULTIPLE_IMAGE_POLICY.md`,
`LABEL_HARMONIZATION_PLAN.md`, and the SHA-256 manifest named above. The manifest deliberately
excludes raw medical-data files, identifiers, report text, images, and row-level manifests.

## C3-E4 provenance amendment — 2026-07-18

The original C3-E2 SHA-256 manifest **predates Git initialization** and is retained unchanged as a
historical pre-Git manifest. It must not be silently regenerated to make later policy amendments look
like original C3-E2 content. C3-E4 deliberately amended this closure, the statistical plan, and some
path-bearing documentation after the baseline checkpoint; therefore the historical manifest is not a
checksum declaration for every post-C3-E4 documentation byte. Git records those amendments.

The frozen CheXpert aggregate result files were not recomputed or edited during provenance repair.
Raw medical data remains outside Git. Before the baseline commit, `git check-ignore` confirmed that
the main CheXpert Parquet table and all three raw label JSON files were ignored; the staged-file audit
confirmed that no raw data, identifiers, credentials, model artifacts, virtual environments, or
images were committed.
