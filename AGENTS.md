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

Stage status: C3-E6 Stages 3A through 4 are complete. Full-cohort source-site
labels exist for both endpoints. Stage 5, frontal image acquisition, is open.

Authorized:

- protocol validation;
- synthetic non-medical data generation;
- data-contract development;
- unit and integration testing;
- documentation;
- synthetic metric dry-runs;
- safe report generation;
- MIMIC metadata inspection;
- MIMIC report parsing;
- report structure analysis;
- report section statistics;
- CheXbert execution on report text at the source site;
- source-site label generation for the impression and findings scopes;
- downloading MIMIC-CXR-JPG frontal images listed in the Stage 3E manifests.

Not authorized:

- loading or decoding medical image content;
- downloading images outside the Stage 3E manifests;
- downloading any DICOM dataset;
- model training;
- image-model inference;
- external-site label regeneration;
- CheXpert model evaluation;
- threshold selection or tuning;
- evaluation or metric computation on real data;
- cross-site scientific claims;
- external-site tuning;
- implementation of post-hoc mitigation methods.

Report parsing is authorized for structural analysis and for labelling through
the pinned CheXbert port. It does not authorize model input construction or
export of report text. Section content may be measured and summarised in
aggregate; it may not be written into any artifact under `results/`.

Row-level labels are restricted data. They are written only into the gitignored
`data/` tree; only aggregate prevalence and provenance may reach `results/`.

The external site uses the CheXbert labels shipped with CheXpert Plus, per
`docs/LABEL_HARMONIZATION_PLAN.md`. Regenerating them is not authorized.

Image acquisition is bounded by the five Stage 3E manifests under
`data/mimic/download_manifests/` — 193,282 frontal JPGs. Acquisition means
transfer to the gitignored `data/mimic/images/` tree only. Decoding image
content, inspecting pixels, and model training remain unauthorized until a
separate stage opens them. Credentials are supplied through `~/.netrc` and are
never written into a script, a command line, a log, or any tracked file.

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
```