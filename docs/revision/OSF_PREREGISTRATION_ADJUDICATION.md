# OSF registration text: blinded expert adjudication

Paste into an OSF Registries "Secondary data preregistration" (or "OSF
Preregistration") form **before any image is read**. Fill the bracketed items
first. The full protocol is `EXPERT_ADJUDICATION_PROTOCOL.md`; attach it.

## Title
Blinded radiologist reference labels for a two-hospital evaluation of frozen
selective prediction in chest radiography

## Background and existing knowledge of the data
A completed evaluation (repository:
https://github.com/mr-shakib/compound-shift-selective-reliability; Zenodo
10.5281/zenodo.23213133) applied a selective-prediction policy, frozen at
MIMIC-CXR-JPG, unchanged to CheXpert Plus. With labels derived automatically
from report impressions, the external-minus-source difference in selective
error (H1) could not be determined: depending on how uncertain and unmentioned
report labels were treated, the feature-fusion model's difference ranged from
about −0.02 to +0.13. The authors have seen all report-label results. No
image-based expert label for any sampled study has been seen by the authors.

## Research questions (estimation, no hypothesis test)
1. Selective error of the feature-fusion model (M4) at the frozen policy,
   against an image-based expert reference, at each site, and the
   external-minus-source difference (primary).
2. The same for the late-fusion model (M3).
3. Per pathology and site, what each report-label category (positive,
   negative, uncertain, unmentioned) corresponds to on the image.
4. Which report-label handling used in the paper is closest to the expert
   estimate of question 1.
5. Selective error among accepted studies without any labelled target (the
   assumption the original estimator made implicitly).

## Data and sampling
- Frames: the 14,766 source evaluation studies and the 132,923 external
  studies of the primary analysis.
- Strata per site (8): at least one report-labelled target or none ×
  accepted or deferred by M4 × M4 calls any target positive or none.
- 600 studies per site: 300 accepted-labelled, 150 accepted-label-less, 150
  deferred, proportional to frame size within each group; random within
  strata, seed 20261006. Inclusion probabilities are recorded.
- Sample file SHA-256 (recorded after drawing, before reading):
  [paste from results/c3e_adjudication/sample_manifest.json].
- Separate item sets, not weighted into the estimates: the 200 CheXpert
  validation studies (three-radiologist consensus labels) as a hidden check
  of reader accuracy; 30 practice studies, discarded.

## Readers and blinding
Two board-certified radiologists read every study independently; a third,
senior radiologist resolves disagreements and "indeterminate" calls.
Readers see only the frontal images at full resolution, in randomised order
with sites interleaved, blinded to site, report, context, report labels,
model output and stratum. Per finding: present / absent / indeterminate, and
confidence 1–5. Readers: [names, specialty, years of practice].

## Variables
Reference label per study and finding: the adjudicated label. Model decisions
and acceptance come from the frozen policy (thresholds and cutoff selected at
the source in August 2026, unchanged).

## Analysis plan
- Horvitz–Thompson weighting by inverse inclusion probability; stratified,
  patient-clustered bootstrap, 2,000 replicates, seed 20261006; 95% percentile
  intervals.
- Primary estimand: weighted study-level five-finding Hamming error of M4
  among accepted studies at each site; the external-minus-source difference.
- Inter-reader agreement: Cohen's κ per pathology on the frozen primary-reader
  labels, before adjudication.
- Reader accuracy on the CheXpert validation items against their consensus
  labels, reported per reader.
- Final "indeterminate" cells: analysed excluded, and as present and as absent
  (bounds).
- No decision rule. The 0.02 materiality of the original protocol is reported
  for context only.

## Deviations
Any change after registration is logged with its date and reason in the
repository and reported in the paper.
