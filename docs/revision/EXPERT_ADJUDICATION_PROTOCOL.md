# Blinded expert adjudication protocol (draft, not executed)

Status: **draft for author and clinical-collaborator review, 2026-10-06.**
No adjudication has been performed. No labels in this repository come from
clinicians, and none may be simulated or produced by a language model and
described as clinical ground truth.

## 1. Purpose

The revision (R1) shows that the sign of the cross-site selective-risk
contrast depends on how report-derived labels are handled. Unlabelled,
uncertain and unmentioned cells occur at very different rates at MIMIC-CXR and
CheXpert Plus (issue L-01). Adjudication against an image-based expert
reference at both sites would:

1. estimate selective error of the frozen policy against a common reference
   at each site, and the cross-site difference;
2. estimate how report labels relate to image findings at each site, per
   pathology. That covers sensitivity and specificity of positive and negative
   labels, and what fraction of *unmentioned* and *uncertain* cells are
   image-positive. These quantities decide which label-handling alternative is
   closest to the truth;
3. test directly the assumption hidden in the original estimator, that
   accepted studies without a labelled target are classified correctly.

## 2. Population and sampling frame

- Frames: the 14,766 source evaluation studies and the 132,923 external N1
  studies (C0), i.e. the cohorts of the primary analysis.
- Unit: study (all frontal images shown together; lateral images optional but
  recorded).
- Model of record: M4 (feature fusion) at the frozen 80% policy; M3 decisions
  recorded for the same studies.
- Stratification (per site, 8 strata): label availability (≥1 labelled target
  vs none) × policy (accepted vs deferred) × M4 decision (any target called
  positive vs none). Sampling is random within strata with a fixed seed
  (20261006). Label-less accepted studies are over-sampled because they
  determine the original estimator's error.
- Exclusions: none beyond the primary cohorts. Images that fail to load are
  replaced from the same stratum, and the replacements are logged.

## 3. Sample size (precision-based)

Let *p* be the study-level probability that the policy makes at least one
error among the five findings, against the expert reference, among accepted
studies. With half-width *h* of a 95% interval, n_eff = 1.96² p(1−p)/h², and
a design effect of about 1.3 for unequal stratum weights:

| p (assumed) | h = 0.05 | h = 0.04 | h = 0.03 |
|---|---|---|---|
| 0.15 | 255 per site | 398 | 708 |
| 0.25 | 375 | 586 | 1,041 |
| 0.35 | 455 | 711 | 1,263 |

A cross-site difference with half-width *h* needs about twice the per-site
n_eff (for p = 0.25: 577 per site for ±0.05, 901 for ±0.04).

**Recommended minimum:** 600 studies per site (1,200 total), allocated 50%
accepted-labelled, 25% accepted-label-less and 25% deferred. This gives about
±0.05 for the per-site accepted-study error at p ≈ 0.25 after weighting, and
±0.07 for inter-reader κ (p₀ = 0.85, pₑ = 0.55). Per-pathology label
sensitivity and specificity will be imprecise for consolidation, which is
uncommon, and the protocol states this in advance rather than enlarging the
sample after the fact.

Reader workload: about 1–1.5 min per study for five findings, so roughly
20–30 hours per primary reader for 1,200 studies. The third reader reviews
only disagreements, typically 15–25% of studies.

## 4. Readers and blinding

- Two board-certified radiologists (primary readers) read every sampled study
  independently. A third, senior radiologist adjudicates disagreements.
- Blinded to: report text, permitted context, CheXbert labels, model
  probabilities, decisions, acceptance, stratum, and site. Images are shown in
  the common 224-pixel pipeline format or the original resolution, at the
  readers' choice, with burned-in text masked where feasible. Residual site
  cues (e.g. portable markers) cannot be fully removed; this is recorded as a
  limitation.
- Presentation order is randomised per reader, with sites interleaved.

## 5. Annotation form (per study)

| Field | Values |
|---|---|
| Image quality adequate for interpretation | yes / limited / no |
| Projection | AP / PA / other / indeterminate |
| Cardiomegaly | present / absent / indeterminate |
| Edema | present / absent / indeterminate |
| Consolidation | present / absent / indeterminate |
| Atelectasis | present / absent / indeterminate |
| Pleural effusion | present / absent / indeterminate |
| Confidence (each finding) | 1 (low) – 5 (high) |
| Support devices present | yes / no (descriptive only) |
| Comment | free text (no identifiers) |
| Reading time | recorded automatically |

Definitions follow CheXpert/CheXbert target definitions, which are circulated
to readers with ten worked examples from public sample images (not study data)
before reading begins. A calibration session on 30 practice studies (from the
model-train tier, outside the frames) precedes formal reading, and its
results are discarded.

## 6. Disagreement resolution

- Primary readers' labels are frozen before adjudication; inter-reader
  agreement (Cohen's κ per pathology, with 95% intervals) is reported on these
  frozen labels.
- Any finding with disagreement, or with "indeterminate" from either reader,
  goes to the adjudicator, who sees the two labels without reader identity and
  records the final label (present / absent / indeterminate).
- Final "indeterminate" cells are reported separately and analysed both
  excluded and as present/absent bounds.

## 7. Analysis plan (to be frozen before reading starts)

- Reference: adjudicated expert labels.
- Estimates use stratum weights (inverse inclusion probabilities, i.e.
  Horvitz–Thompson). Intervals come from a stratified, patient-clustered
  bootstrap with 2,000 replicates and seed 20261006.
- Primary estimand: weighted selective error of M4 among accepted studies at
  each site against the expert reference (study-level five-finding Hamming
  error; all five cells observed by construction), and the external-minus-source
  difference.
- Secondary estimands:
  - the same for M3;
  - per-pathology sensitivity and specificity of model decisions against the
    expert reference;
  - per-pathology agreement of report labels with the expert reference by label
    category (positive, negative, uncertain, unmentioned);
  - error among accepted label-less studies, which tests the original
    estimator's implicit assumption;
  - which label-handling variant of R1 is closest to the expert-reference
    estimate.
- Decision rule: none. This is an estimation study. The 0.02 materiality is
  reported for context only.
- The plan, the sampled study list (restricted data, stored in `data/`), and
  the seed are frozen and hash-recorded before any image is read. Any later
  change is logged as an amendment.

## 8. Governance

- MIMIC-CXR-JPG: every reader must hold PhysioNet credentialed access and sign
  the data use agreement. Images may not be sent to non-credentialed people or
  to external services.
- CheXpert Plus: readers must be covered by the Stanford AIMI research use
  agreement.
- An ethics determination (review or exemption) for expert review of
  de-identified images must be obtained by the authors' institution before
  reading. This protocol does not assert that one exists.
- Reader compensation, conflicts of interest and authorship or
  acknowledgement terms are to be agreed in advance.

## 9. What this protocol cannot do

It produces an image-based reference for a sample, not for the cohorts.
Uncommon findings will be estimated imprecisely. Image-only reading differs
from clinical reporting, which also draws on history and priors, so the expert
reference is a different construct from the report labels, not a corrected
version of them.
