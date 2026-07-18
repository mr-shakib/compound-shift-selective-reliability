# C3E Repository Instructions

## Project identity

C3E is a research project evaluating whether multimodal selective
reliability transports across hospitals when pre-diagnostic clinical
context changes in availability or alignment.

The primary contribution is a compound-shift evaluation protocol.

It is not currently a new-architecture project, prospective clinical
study, deployment study, or regulatory validation.

## Repository structure

- Python package: `c3e_audit_toolkit/c3e/`
- Package tests: `c3e_audit_toolkit/tests/`
- Frozen machine-readable protocol: `protocols/C3E6_stage2/`
- Research documentation: `docs/`
- Safe generated results: `results/`
- Medical or restricted data: `data/`

Do not create a second Python project or a new top-level `src/` package.
New Stage 2B implementation code belongs inside the existing
`c3e_audit_toolkit/c3e/` package.

## Current authorization

Authorized:

- protocol validation;
- synthetic non-medical data generation;
- data-contract development;
- unit and integration testing;
- documentation;
- synthetic metric dry-runs;
- safe report generation.

Not authorized:

- loading medical images;
- downloading medical datasets;
- model training;
- MIMIC-CXR processing;
- CheXpert model evaluation;
- cross-site scientific claims;
- external-site tuning;
- implementation of post-hoc mitigation methods.

## Frozen scientific decisions

Do not change without an approved protocol amendment:

- target pathologies:
  - Cardiomegaly
  - Edema
  - Pleural Effusion
  - Atelectasis
  - Consolidation
- primary label source: `impression_fixed.json`
- sensitivity label source: `findings_fixed.json`
- forbidden label source: `report_fixed.json`
- permitted text must be pre-diagnostic;
- Findings, Impression, and complete reports are forbidden model inputs;
- bootstrap replicates: 2000;
- bootstrap seed: 20260718;
- resampling unit: patient;
- primary source coverage: 80%;
- sensitivity coverages: 90% and 70%;
- frozen source-selected threshold transfer;
- C0, C1, and C2 intervention semantics;
- no CheXpert tuning.

## Protocol integrity

Before protocol-dependent work, run:

```bash
python protocols/C3E6_stage2/scripts/validate_protocol.py