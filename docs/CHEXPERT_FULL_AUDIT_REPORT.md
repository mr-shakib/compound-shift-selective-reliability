# CheXpert Plus Full Aggregate-Safe Audit Report (C3-E2)

Status: **complete, 2026-07-18.** Both label endpoints audited under the preregistered
multiple-image analysis policy. All figures below are aggregate-only (counts, weighted counts,
percentages) — no identifiers, paths, report text, or per-row data. Source outputs:
`results/c3e_chexpert_plus/impression/`, `.../findings/`, `.../label_source_comparison.{csv,json}`.

Method: image-level observation unit (frontal only), study-equal weighting (each study's frontal
images share total weight 1), one-to-one label join on `path_to_image`, study key derived as
`patient_folder + study_folder`. Policy locked before results: `CHEXPERT_MULTIPLE_IMAGE_POLICY.md`.

## 1. Cohort structure

| Metric | Value |
|---|---|
| Total table rows | 223,462 |
| Frontal image rows (analysis cohort) | 191,071 |
| Lateral / excluded rows | 32,391 |
| Patients (all / frontal) | 64,725 / 64,710 |
| Studies (all / frontal) | 187,711 / 187,674 |
| Frontal images per study | min 1, median 1, mean 1.018, max 3 |
| Multi-frontal studies | 3,356 (1.8%) |
| Frontal AP / PA / LL / RL | 161,622 / 29,432 / 16 / 1 |
| Split (frontal images) | train 190,869 / valid 202 |
| Patients per split | train 64,510 / valid 200 — **overlap 0** |

Study-key parse failures: 0. Join: one-to-one, 0 unmatched, expansion 1.0.

## 2. Context availability (permitted model inputs only)

Permitted inputs: `section_clinical_history`, `section_history`, and their combination. Image-level
unweighted with study-equal-weighted estimates (weighted ≈ unweighted throughout, since 98% of
studies are single-frontal).

| Field | non-empty | usable | low-info | median tokens | <5 tok | <10 tok |
|---|---|---|---|---|---|---|
| clinical_history | 100.0% | 48.0% | 52.0% | 4 | 98,151 | 167,432 |
| history | 100.0%* | 12.3% | 87.7% | 1 | 167,245 | 186,097 |
| **combined** | **78.5%** | **60.3%** (wt 60.1%) | **18.2%** | **7** | 33,168 | 121,297 |

*non-empty is among present rows; clinical_history is null in 37.9% of frontal rows, history in 83.6%.
Combined **usable-context rate 60.3%** (weighted 60.1%). Combined natural absent 21.5% + low-info
18.2% = **39.7%** naturally missing-or-low.

## 3. Label distributions (positive % among known = non-null)

| Target | impression pos% | findings pos% | imp known-n | fnd known-n |
|---|---|---|---|---|
| Cardiomegaly | 63.9% | 48.7% | 41,119 | 18,950 |
| Edema | 64.8% | 66.6% | 77,875 | 17,153 |
| Pleural Effusion | 71.3% | 67.9% | 111,811 | 30,802 |
| Atelectasis | 49.3% | 51.9% | 61,143 | 15,105 |
| Consolidation | 21.0% | 25.5% | 57,920 | 13,783 |

All five targets have thousands of positives in both sources (impression 12,181–79,671; findings
3,520–20,923) — far above the gate's `min_target_positive` (200). Prevalence broken down by AP/PA,
train/valid, and usable- vs missing-context groups is in each source's `label_prevalence.csv`.

## 4. Missingness relationship (association, not causation)

Context-absent fraction varies across a target's label states. Per-target spread of the
context-absent fraction (max − min over pos/neg/unc/unmentioned):

| Target | absent-fraction spread |
|---|---|
| Cardiomegaly | 0.070 |
| Edema | 0.095 |
| Pleural Effusion | 0.104 |
| Atelectasis | 0.104 |
| Consolidation | 0.080 |

Max spread 0.104 ≥ 0.05 → **context missingness appears label-associated.** This is an association
only; **no causal claim** is made. It is flagged as a modeling risk (context-conditioned estimates
may be biased and must be reported as such).

## 5. Leakage analysis (permitted inputs only)

Searched only `section_clinical_history` + `section_history` with the reviewed term dictionary.
Direct target-mention rate among **positive**-labeled images:

| Target | direct (among positives) | any-mention (all) |
|---|---|---|
| Cardiomegaly | 0.08% | 0.03% |
| Edema | 2.96% | 1.67% |
| Pleural Effusion | 3.84% | 2.01% |
| Atelectasis | 0.22% | 0.11% |
| Consolidation | 0.44% | 0.15% |

Every target is far below the gate ceiling (`max_direct_mention_fraction_among_positives = 0.70`).
Synonym, negated, and speculative rates are all < 1% for most targets (full detail in
`leakage_by_label.csv`). **Leakage severity: LOW for all five targets.** The permitted context is
genuinely pre-diagnostic — it does not trivially reveal the labels.

## 6. Multiple-image sensitivity

Within-study label disagreement among the 3,356 multi-frontal studies is negligible — differing
studies: Cardiomegaly 3, Edema 0, Pleural Effusion 2, Atelectasis 1, Consolidation 2 (≤ 0.09%).

Positive-fraction-among-known under the four preregistered policies (primary study-equal-weighted,
unweighted image-level [Sensitivity A], one-image-per-study [B], target-specific concordant subset
[C]): the maximum shift across all four policies is **< 0.001 (0.1 percentage point)** for every
target in both sources. Concordant-subset exclusions are 0–1 studies per target. **The audit is
essentially insensitive to the multiple-image policy choice** (`image_policy_sensitivity.csv`).

## 7. Label-source sensitivity (impression vs findings)

Positive-prevalence-among-known difference (impression − findings):

| Target | Δ (percentage points) |
|---|---|
| Cardiomegaly | +15.2 |
| Pleural Effusion | +3.3 |
| Edema | −1.8 |
| Atelectasis | −2.5 |
| Consolidation | −4.5 |

Cardiomegaly shows a **notable** source difference; the other four are within ±5 pp. **Both sources
pass the gate with all five labels viable.** Findings is sparser (far more `unmentioned`), consistent
with the findings section being present in only ~27% of reports — hence its role as the mandatory
sensitivity endpoint, not the primary. Full comparison: `label_source_comparison.{csv,json}`.

## 8. Gate evaluation (pre-specified thresholds, unchanged)

| Gate | Threshold | Observed | Pass |
|---|---|---|---|
| Combined usable context | ≥ 40% | 60.3% | ✅ |
| Natural absent/low-info context | ≥ 5% | 39.7% | ✅ |
| Viable target labels | ≥ 3 | 5 | ✅ |
| Sufficient positives per viable label | ≥ 200 | ≥ 3,520 | ✅ |
| Direct-mention leakage among positives | ≤ 70% | ≤ 3.84% | ✅ |
| Patient-level separation (train/valid) | 0 overlap | 0 | ✅ |
| Multiple-image-policy sensitivity | small | < 0.1 pp | ✅ |
| Label-source sensitivity | both viable | both pass; Cardiomegaly Δ15pp noted | ⚠️ noted |
| Label-dependent missingness | reported | present (spread 0.104), association only | ⚠️ noted |
| Safe-output compliance | clean | scan clean | ✅ |

Both `gate_report.json` files report `passed: true`. Statistical associations above are **not**
interpreted as clinical meaning.

## 9. Interpretation

The data-validity premise for CheXpert Plus is **supported**: a substantial usable pre-diagnostic
context signal (60% usable), target labels that are **not** trivially leaked by that context (< 4%
direct mention among positives), a sound patient→study→image hierarchy with clean patient-level
separation, and estimates that are robust to the multiple-image policy. The main caveats are the
label-associated context missingness and the Cardiomegaly impression-vs-findings gap, both of which
are documented and carried forward, not resolved here.

CheXpert Plus is validated as **one** site. The cross-site comparison still requires MIMIC with
harmonized CheXbert labeling (`LABEL_HARMONIZATION_PLAN.md`).

## 10. Boundaries (not done, not authorized here)

No model training, no CheXbert run, no MIMIC processing, no image downloading, no cross-site
analysis, no patient-/study-/image-level manifest. The tiny `valid` split (202 frontal images / 200
patients) is **not** a usable test set — a proper patient-level resplit is required before modeling.
