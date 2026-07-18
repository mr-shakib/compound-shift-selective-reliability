# C3-E Decision Gate

This document records the decision rules for whether the C3-E dataset route (MIMIC-CXR source,
CheXpert Plus external target) is viable. The CheXpert Plus audit passed on 2026-07-18; the MIMIC and
cross-site gates remain unassessed pending authorized access. See `C3E2_PHASE_CLOSURE.md` for the
frozen external-site decision.

## Proceed to text-only audit when:

- At least three target labels have sufficient source and external positive counts
- Usable pre-diagnostic context is available for at least 40% of studies at both institutions
- At least one institution has at least 5% absent or low-information context
- Direct target mentions do not dominate nearly all positive histories
- Patient overlap across source splits is zero
- A meaningful cross-site context-availability or context-quality difference exists
- Label definitions can be harmonized

## Modify when:

- Only two labels are viable
- Natural missingness is weak but context-quality shift is strong
- Direct disease mentions are high but masked text remains informative
- Context sections require different mappings at the two institutions

## Reject the dataset route when:

- Fewer than two labels are viable
- Context is almost always absent
- Context is almost always explicitly label-revealing
- No meaningful context shift exists between institutions
- Labels cannot be harmonized
- Patient-level separation cannot be guaranteed

## How this maps to the toolkit's automated gate

The toolkit computes an automated `gate_report.json` per site (see `c3e_audit_toolkit/c3e/audit.py:
gate_report`) and a `cross_site_gate.json` from `c3e-audit compare`. These check machine-readable
proxies for several of the criteria above (viable label count, usable-context fraction,
missing-or-low-information fraction, direct-mention fraction, cross-site difference thresholds) using
the thresholds configured in `configs/mimic.yaml` / `configs/chexpert_plus.yaml`. The automated gate is
a necessary check, not a sufficient one — the full Proceed / Modify / Reject decision above requires
human judgment (e.g., "labels can be harmonized" and "patient-level separation guaranteed" are not
fully captured by the automated thresholds) and should be recorded as a dated entry in
`docs/research_log.md` once real audit outputs exist.

## Current gate state — 2026-07-18

- **CheXpert Plus local data-validity gate: GO.** All five targets are viable, usable context is
  60.3%, absent/low-information context is 39.7%, leakage is low, and hierarchy/joins pass.
- **Required modifications:** findings-derived label sensitivity, explicit Cardiomegaly sensitivity,
  context-missingness stratification, study-equal weighting, and patient-clustered uncertainty.
- **Rejected:** report-derived labels and the official CheXpert valid split as the primary development
  split.
- **MIMIC and cross-site gates: not evaluated.** The final dataset-route verdict remains deferred,
  rather than failed, until MIMIC intake and harmonization pass.
