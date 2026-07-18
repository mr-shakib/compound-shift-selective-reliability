# Hypothesis Registry

Status: **REGISTERED 2026-07-18, before model training or cross-site evaluation**

All hypotheses are evaluated separately for Cardiomegaly, Edema, Pleural Effusion, Atelectasis, and
Consolidation. The image is the prediction unit, study-equal weighting is primary, and uncertainty is
patient-clustered. No numerical expected effect size is registered. “Risk” means pathology-specific
prediction error among retained predictions; lower AURC and lower selective risk are better.

## H1 — Selective reliability degrades under hospital transfer, especially without useful context

- **Primary metric:** Area under the risk–coverage curve (AURC); selective risk at the locked fixed
  coverage levels is supportive.
- **Comparison:** MIMIC versus CheXpert Plus for the same frozen model, first overall and then within
  usable-, absent-, and low-information-context strata.
- **Expected direction:** Higher AURC and selective risk externally, with the largest degradation in
  absent or low-information context.
- **Falsification condition:** No external degradation, or external reliability is consistently
  better, with no greater degradation in absent/low-information strata across the primary endpoint.
- **Required sensitivities:** findings-derived labels; AP versus PA; one image per study;
  concordant-study restriction; image-only and multimodal models; uncertainty-label handling; and
  failure-detection AUROC/AUPRC.

## H2 — Context missingness interacts with hospital shift

- **Primary metric:** Difference-in-differences in AURC:
  `(CheXpert absent-or-low − CheXpert usable) − (MIMIC absent-or-low − MIMIC usable)`.
- **Comparison:** The context-availability reliability gap across hospitals, with absent and
  low-information groups also reported separately.
- **Expected direction:** The external-versus-source reliability change is worse when context is
  absent or low-information than when it is usable; the interaction is not explained by hospital
  shift alone.
- **Falsification condition:** The patient-clustered 95% confidence interval for the interaction is
  compatible with no interaction and the direction is not stable across the primary pathologies, or
  the gap is consistently opposite.
- **Required sensitivities:** impression versus findings; absent and low-information separated;
  image-only negative-control comparison; AP versus PA; one image per study; concordant studies; and
  prevalence/context reweighting defined from MIMIC only.

## H3 — Reliability transport is pathology-specific

- **Primary metric:** Pathology-specific change in AURC from MIMIC to CheXpert.
- **Comparison:** Cross-site AURC changes across the five registered pathologies.
- **Expected direction:** The magnitude, and potentially the direction, of reliability transport
  differs by pathology.
- **Falsification condition:** Cross-site AURC changes are statistically and practically
  indistinguishable across all five pathologies under the registered uncertainty analysis.
- **Required sensitivities:** all five failure-detection metrics; impression versus findings; AP
  versus PA; context strata; one image per study; concordant studies; and multiplicity-adjusted
  pathology contrasts.

## H4 — Source-site error ranking need not transfer externally

- **Primary metric:** Spearman rank correlation of pathology-specific failure-detection performance
  between MIMIC and CheXpert; rank reversals are reported directly.
- **Comparison:** Ranking of the five pathologies by failure-detection AUROC on MIMIC versus
  CheXpert.
- **Expected direction:** Ranking is not perfectly preserved and at least one pathology changes
  position under transfer.
- **Falsification condition:** The complete pathology ranking is preserved, with rank correlation 1,
  across the primary endpoint and registered sensitivities.
- **Required sensitivities:** failure-detection AUPRC; AURC-based ranking; impression versus
  findings; usable/absent/low-information strata; AP versus PA; one image per study; and concordant
  studies.

## H5 — Conclusions are directionally consistent across label sources

- **Primary metric:** Directional agreement of the registered MIMIC-to-CheXpert AURC contrasts under
  impression-derived versus findings-derived labels.
- **Comparison:** Sign and qualitative conclusion for each pathology and registered context contrast
  under the two harmonized label sources.
- **Expected direction:** Principal conclusions retain the same direction under both label sources,
  even if magnitude and precision differ.
- **Falsification condition:** A principal conclusion reverses direction with non-overlapping
  patient-clustered uncertainty, or the primary claim is supported by only one label source.
- **Required sensitivities:** explicit Cardiomegaly analysis; known-label cohort counts; uncertainty-
  label handling; AP versus PA; one image per study; concordant studies; and all primary reliability
  metrics.

## H6 — Multimodal reliability is more sensitive to context availability than image-only reliability

- **Primary metric:** Model-by-context difference in AURC: the absent-or-low versus usable AURC gap
  for multimodal models minus the same gap for image-only models.
- **Comparison:** Frozen multimodal and image-only models within each hospital and across transfer.
- **Expected direction:** Removing or degrading clinical context produces a larger reliability change
  for multimodal models than for image-only models.
- **Falsification condition:** The multimodal context-availability gap is no larger than the
  image-only gap, or is consistently smaller, for the primary endpoints across hospitals.
- **Required sensitivities:** absent and low-information context separated; empty-text handling for
  multimodal inference; impression versus findings; AP versus PA; one image per study; concordant
  studies; and comparison at matched coverage as well as AURC.

## Interpretation rule

A hypothesis is not declared supported from a single pathology, metric, or favorable subgroup.
Primary metrics and comparisons govern; secondary metrics and sensitivities qualify robustness. Null
or directionally inconsistent results are reported without rewriting the registered hypothesis.
