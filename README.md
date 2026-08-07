# Compound-shift evaluation of multimodal selective reliability

Does a selective prediction policy calibrated at one hospital remain reliable at
another when pre-diagnostic clinical context changes in availability or
alignment?

This repository holds the protocol, code, and aggregate results for a
retrospective pre-deployment evaluation that crosses two shifts deliberately —
institution and context availability — so their interaction can be estimated
rather than assumed away.

**Status: work in progress.** The confirmatory analysis is not complete, and no
result should be cited from this repository yet.

## What is here

| Path | Contents |
|---|---|
| `protocols/C3E6_stage2/` | machine-readable protocol, hash-manifested, with an amendment log and an automated validator |
| `c3e_audit_toolkit/c3e/` | intake, labelling, training, calibration, evaluation and analysis code |
| `c3e_audit_toolkit/tests/` | 160+ tests, all fixtures synthetic |
| `results/` | aggregate artifacts only, each with a manifest of SHA-256 digests |
| `paper/` | LaTeX source |
| `docs/` | research log, statistical analysis plan, data-safety and provenance policies, related-work tracking |

## What is deliberately not here

No medical data. No images, no row-level labels, no report text, no model
checkpoints, no patient or study identifiers. MIMIC-CXR-JPG and CheXpert Plus
are available to credentialed researchers from PhysioNet and Stanford AIMI
respectively, under data use agreements that prohibit redistribution.

Everything under `results/` is aggregate and was checked before commit against
an explicit allowlist and a scan for identifiers, paths and secrets, following
`docs/PROVENANCE_AND_VERSIONING_POLICY.md`.

## Design in one paragraph

Models are developed and a selective policy calibrated at a source hospital,
then evaluated at an external hospital with per-pathology thresholds and
abstention cutoffs **transferred frozen**. Re-fitting a threshold at the target
site would test whether a method transfers; it cannot test whether a deployed
policy transfers, because the policy that would actually ship is the frozen one.
At each site, context is left intact, removed, or replaced with another
patient's — separating absence of information from wrong information.

Four models are compared: image-only and text-only controls, probability late
fusion, and feature-concatenation fusion. Backbones are conventional and held
constant, so architecture cannot serve as a competing explanation for any
transport effect observed.

## Preregistration

The protocol was frozen in a machine-readable registry before any label, model
output, or metric existed. Every amendment is dated with its rationale and its
confirmatory status; changes made after external-result inspection are labelled
post-hoc exploratory by protocol rule.

```bash
python protocols/C3E6_stage2/scripts/validate_protocol.py
```

## Reproducing

The pipeline runs in stages, each writing an audit artifact with compliance
declarations and a digest manifest. Reserved evaluation tiers are unreadable in
code by any stage that could influence a model, a threshold, or a policy — the
boundary is enforced rather than documented.

```bash
cd c3e_audit_toolkit
python -m pytest tests/ -q
```

## Licence

Code is MIT licensed (`LICENSE`). Documentation, the protocol registry and the
aggregate artifacts under `results/` are released under CC BY 4.0.

This licence covers only what is in this repository. It grants no rights over
MIMIC-CXR-JPG or CheXpert Plus, which remain governed by their own data use
agreements and are not redistributed here.
