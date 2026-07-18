# External Validation Policy

Status: **LOCKED 2026-07-18**

## Institutional roles

- **Source development institution:** MIMIC-CXR / MIMIC-CXR-JPG, Beth Israel Deaconess Medical
  Center.
- **Independent external evaluation institution:** CheXpert Plus, Stanford Health Care.

These roles cannot be reversed after viewing external performance. “Source” and “external” describe
the protocol roles, not data quality or clinical superiority.

## Development boundary

Model architecture, feature processing, pretraining choices, hyperparameters, optimization settings,
random-seed policy, model selection, calibration method and parameters, classification thresholds,
selective-prediction thresholds, fixed operating points, early stopping, stopping decisions, and all
other adaptive choices must be selected using **MIMIC only**. Patient-separated MIMIC development
and validation partitions must be used for every such choice.

CheXpert Plus must not be used for iterative tuning. In particular, external labels, subgroup
metrics, calibration plots, errors, or risk–coverage curves must not feed back into architecture,
hyperparameter, calibration, threshold, checkpoint, stopping, preprocessing, or prompt choices. Any
unplanned change after external results are viewed creates a new exploratory analysis and invalidates
the unchanged claim of independent external validation for that changed system.

The external analysis code, endpoints, metric definitions, subgroup definitions, and output tables
should be frozen and dry-run on synthetic or MIMIC-only data before CheXpert predictions are scored.
CheXpert evaluation should then be a single locked evaluation, apart from correction of a documented
implementation error that does not use outcome direction to choose the correction.

## CheXpert label endpoints

- Primary CheXpert results use **impression-derived labels**.
- Every primary result must be repeated with **findings-derived labels** as a mandatory sensitivity
  analysis.
- Report-derived labels are prohibited because their source scope includes permitted clinical-context
  inputs and creates direct input-target leakage.
- Findings, Impression, Summary, diagnostic conclusions, and full report text are prohibited model
  inputs.

The five pathology endpoints are Cardiomegaly, Edema, Pleural Effusion, Atelectasis, and
Consolidation. Reporting is pathology-specific; a pooled headline cannot replace per-pathology
results.

## Split policy

The shipped CheXpert official valid split is **not the primary development split** and cannot be used
to choose or tune the final system. It is too small for the planned primary role and CheXpert is the
external institution in this protocol.

If a CheXpert-only patient-level resplit is later created for diagnostic or secondary work, it must
be labeled **secondary internal-to-CheXpert analysis**. It cannot be described as independent
external validation, because choices or estimates obtained within that resplit are conditioned on
the external institution. Such an analysis cannot replace the untouched locked evaluation.

## Permitted and prohibited uses

Permitted after the protocol is frozen: compute the preregistered external metrics, confidence
intervals, pathology-specific and context-availability subgroup analyses, and mandatory label/view/
multiple-image sensitivities.

Prohibited: repeated external evaluation during development; selecting a checkpoint because it looks
best on CheXpert; recalibrating or moving thresholds on CheXpert; dropping a pathology or subgroup
because its external result is unfavorable; or presenting a CheXpert-only resplit as independent
external validation.

## Deviations

Every deviation must be dated, justified, and labeled confirmatory or exploratory. If CheXpert
outcomes influenced the deviation, results from the altered pipeline are exploratory and must be
reported separately from the original locked evaluation.
