# Statistical Analysis Plan

Status: **LOCKED FOR PROTOCOL READINESS 2026-07-18**

Scope: final MIMIC development and CheXpert Plus external evaluation; no statistical test is
performed in this phase.

## Analysis population and units

- **Prediction unit:** frontal chest-radiograph image.
- **Dependence:** images from the same study share clinical context/report information and are not
  independent; studies from the same patient are also dependent.
- **Primary weighting:** study-equal weighting. If a study contributes `m` eligible frontal images,
  each receives weight `1/m`, so every eligible study has total weight 1.
- **Clustering:** confidence intervals use a patient-clustered bootstrap. Sample patients with
  replacement and retain every eligible study and image belonging to each sampled patient.
- **Pathology eligibility:** evaluate each pathology on positive and negative labels known under the
  relevant label source. Unmentioned labels are excluded. Uncertain labels are excluded in the
  primary analysis and handled in registered sensitivity analyses as positive and as negative.
- **Reporting:** every metric is pathology-specific. Macro summaries may supplement but never replace
  the five pathology tables.

## Endpoints and prediction errors

For each pathology, the frozen model produces a probability and a confidence/uncertainty score. The
binary failure indicator is an incorrect pathology decision at the MIMIC-selected classification
threshold. Selective prediction orders cases from most to least confident; coverage is the
study-equal-weighted fraction retained and selective risk is the study-equal-weighted error rate among
retained cases. Score orientation must be frozen on MIMIC so that a larger failure-detection score
always means “more likely to fail.”

## Primary reliability metrics

1. **Area under the risk–coverage curve (AURC):** numerical integral of selective risk over coverage
   from 0 to 1, using the complete ranked curve and study weights; lower is better.
2. **Selective risk at fixed coverage:** report at coverage 0.80, 0.90, and 0.95. If exact coverage is
   unavailable because of tied scores, use the conservative threshold that does not exceed the target
   coverage and report achieved coverage.
3. **Coverage at fixed risk:** report the maximum achieved coverage with selective risk at or below
   0.05, 0.10, and 0.20. These are descriptive operating points, not clinical safety guarantees.
4. **Failure-detection AUROC:** discrimination of the frozen failure score for incorrect versus
   correct predictions.
5. **Failure-detection AUPRC:** precision–recall area for the failure class; always report the
   study-weighted failure prevalence beside it.

All five are primary reliability metrics. AURC is the lead summary for H1–H3 and H6;
failure-detection AUROC is the lead ranking metric for H4. No single pooled metric overrides
pathology-specific conclusions.

## Secondary performance and calibration metrics

- AUROC.
- AUPRC, with pathology prevalence reported.
- Brier score.
- Expected calibration error (ECE), using 15 equal-width probability bins. Empty bins are omitted;
  report the binning rule and a reliability diagram. ECE is descriptive and is not used to recalibrate
  on CheXpert.

Calibration parameters, decision thresholds, and selective operating thresholds are fitted or chosen
on MIMIC only and applied unchanged to CheXpert.

## Confidence intervals and bootstrap

- **Bootstrap unit:** patient.
- **Complete clusters:** resample patients with replacement and retain every eligible study and image
  for each sampled patient. Never resample individual images or split a patient cluster.
- **Final bootstrap replicates:** exactly **2,000 valid replicates**.
- **Random seed:** **20260718**.
- **Confidence interval:** two-sided **95%**.
- **Primary interval method:** percentile bootstrap (2.5th and 97.5th percentiles).
- **Optional sensitivity:** BCa intervals may be reported only when the implementation has been
  technically validated for the weighted, clustered statistic and is computationally feasible. BCa
  cannot replace or suppress the primary percentile interval.
- Recompute the primary study-equal weights within each replicate.
- For within-site paired model/subgroup contrasts, use the same sampled patient clusters in both arms.
  For MIMIC-versus-CheXpert contrasts, resample patients independently within each institution in each
  replicate and calculate the between-site difference.
- Report the number of valid replicates. If fewer than 2,000 are valid for a metric, do not report a
  final interval; diagnose the cause without changing the endpoint based on its direction.

The seed, unit, interval method, confidence level, and replicate count were fixed on 2026-07-18
**before model training or model results were available**. No bootstrap is run in C3-E4.

## Primary comparisons

- MIMIC versus CheXpert for the identical frozen model.
- Multimodal versus image-only model within site and their cross-site change.
- Usable versus absent versus low-information context within site.
- The hospital-by-context difference-in-differences registered in H2.
- Pathology-specific transport changes and source/external error-rank agreement.

Absolute metrics and paired or between-site differences are reported together. A confidence interval
is not interpreted as proof of equivalence merely because it includes zero.

## Context subgroup analysis

Use the same locally implemented, frozen context parser at both institutions.

- **Missing context:** neither permitted pre-diagnostic context field contains non-whitespace text.
- **Low-information context:** non-empty context fails the locked usable-context rule (fewer than five
  normalized tokens or matches a locked generic low-information phrase).
- **Usable context:** non-empty context that is not low-information.
- Report the three strata separately and the combined absent-or-low group used in H1/H2/H6.
- Report patient, study, image, positive-label, negative-label, and failure counts by stratum before
  metrics. Suppress inferential interpretation where a stratum cannot support stable bootstrap
  estimation.
- Context missingness is observational and label-associated; subgroup differences must not be stated
  as causal effects of removing context.

## Mandatory sensitivity analyses

1. **Label source:** impression-derived labels are primary; repeat all primary results using
   findings-derived labels. Highlight Cardiomegaly because the audit showed prevalence sensitivity.
2. **AP versus PA:** repeat metrics within AP and PA frontal views. Do not combine LL/RL with frontal
   views. Report counts and avoid causal claims because view is not randomized.
3. **One image per study:** use the locked deterministic, label-blind rule (lowest parsed view number,
   then stable lexical tie-break) and repeat primary metrics.
4. **Concordant-study:** per pathology, include multi-frontal studies only when all observed labels for
   that target agree; report exclusions.
5. **Uncertain labels:** repeat with uncertain mapped to positive and to negative, keeping unmentioned
   excluded.

The preregistered unweighted image-level analysis is an additional structural sensitivity. No
sensitivity may replace the study-equal-weighted primary analysis.

## Multiple comparisons

The confirmatory family is defined separately for each registered hypothesis and primary reliability
metric across the five pathologies. If formal null-hypothesis tests are later performed, use the Holm
procedure to control the family-wise error rate at 0.05 within that family and report both raw and
adjusted p-values. Secondary metrics, subgroup expansions, and sensitivity analyses are explicitly
supportive/exploratory; if p-values are reported for them, control false discovery rate with
Benjamini–Hochberg within a clearly named family.

Confidence intervals remain 95% intervals and are not silently converted into multiplicity-adjusted
intervals. Claims must identify the metric, pathology, family, and adjustment. Directional consistency,
effect estimates, and interval widths are emphasized over a binary significance label.

## Missing predictions and implementation failures

Do not silently drop missing model outputs. Report their count by site, pathology, view, and context
stratum. A primary external run with unexplained missing predictions, patient leakage, join expansion,
or threshold/calibration drift fails closed and must be corrected under a dated implementation
amendment before interpretation.

## Analysis boundary

No statistical tests, bootstrap evaluation, model fitting, calibration, or threshold selection are
performed in C3-E3. CheXpert outcomes cannot change this plan's model-development decisions.
