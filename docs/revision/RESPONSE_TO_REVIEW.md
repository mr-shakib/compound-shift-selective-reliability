# Response to the review (Revision R1, 6 October 2026)

This responds point by point to the ten review items. Each response says what
was found, what changed, where the evidence is, and what remains. Issue IDs
refer to `ISSUE_REGISTER.md`; "R1" outputs are in `results/c3e_revision/`;
the revised manuscript is `paper/revision/main_revised.pdf` with
`supplement_revised.pdf`. The original draft (`paper/main.pdf`) and all
original artifacts are unchanged.

## 1. Audit before changing claims

- **Which PDF.** `paper/main.pdf` (built 21 Aug 2026) carries the reviewed
  title and is taken to be "c3e.pdf". Two items in the review do not occur in
  its source or in the JAMIA/npj builds: an abstract saying coverage "falls to
  zero", and 14,766 described as the development size (R-19). Please confirm
  which file was reviewed.
- **Code and artifacts correspond to the PDF.** Every Stage 10 estimate (63
  rows across primary, S1, T=5, T=10 and the seed replicate) was replayed
  exactly from the cached predictions. Every Stage 7 threshold and cutoff was
  re-derived exactly from fresh calibration-tier inference. Every cache was
  aligned row by row to a reconstruction of its cohort.
- **Isolation.** All work is on branch `revision/2026-10-audit`, with nothing
  committed. New code is in `c3e_audit_toolkit/c3e/revision/` and new
  manuscript files in `paper/revision/`.
- **Issue register.** 43 issues, each classed as implementation, reporting,
  interpretation, provenance or limitation, with evidence, remedy, status and
  remaining blocker. Status: 31 resolved, 4 partly mitigated, 8 unresolved.

## 2. What the primary endpoint measures

- **Labels.** Source labels come from a CheXbert port (checkpoint SHA-256
  `6550703c…`, upstream commit `6d22a96`), run on impression and findings
  sections separately. Its fidelity check covered only 4 public reports.
  External labels are the CheXbert outputs shipped with CheXpert Plus, with
  undocumented settings. In both, 1/0 are supervised and −1/blank are masked;
  neither is mapped to negative.
- **Loss.** The training loss is a masked BCE, micro-averaged over labelled
  cells of the batch's images, with no weights; images with no labelled cell
  contribute nothing (Methods, eq. 1).
- **Verified defect (I-01).** The evaluation endpoint averaged per-study
  Hamming error over studies and counted studies with **no** labelled target
  as error 0 (`max(n_i,1)`). These were 47.2% of source and 18.7% of external
  studies.
  - The original risk equals the evaluable-study risk × P(evaluable | accepted).
  - Corrected: the evaluable-study estimator is primary, with the original
    retained.
  - Sensitivities: cell-pooled, pathology-macro and per-pathology estimators.
  - Coverage is reported over all studies and over evaluable studies.
- **Counts.** Positive, negative, uncertain and unmentioned counts are given
  per pathology, site and label source, for the full cohort and for each
  model's accepted set (Table 3; `label_audit_by_pathology.csv`).
- **Mechanisms.** Similar aggregate positive rates (71.1% versus 70.0%)
  concealed different compositions. Case mix differs: effusion is 43.5% versus
  22.9% when unmentioned counts as negative. Documentation differs: label-less
  studies, the uncertain rate, and the presence of a findings section. Labeller
  error cannot be separated from these without an expert reference. Where both
  sections label a cell, they agree on 95–99.7% of cells.
- **Expert labels.** None were available, and none were simulated. A blinded,
  stratified adjudication protocol with form, disagreement procedure,
  precision-based sample size and weighting is provided
  (`EXPERT_ADJUDICATION_PROTOCOL.md`). Broad clinical claims were removed, and
  the endpoint is described as error over labelled cells.

## 3. Isolating the label-source effect

- **What S1 changed.** It changed labels, the source cohort (14,766 to 9,293),
  the thresholds and cutoffs (re-selected on findings labels) **and** the C2
  donor realisation (I-02, R-02). Model parameters did not change, and no
  calibration transform exists.
- **Controlled steps.** Studies, probabilities, thresholds and cutoffs were
  held fixed and one factor changed at a time: A0 → A1 (labels) → A2x/A2
  (cohort) → A3 (thresholds; reproduces the published S1). The order was also
  reversed (B2). A common-labelled-cell analysis (A1c) shows the two label sets
  give nearly identical contrasts where both exist. Its selection caveat is
  stated: these are cells both sections mention.
- **Corrected estimator.** The cohort contribution is exactly zero. Labels and
  thresholds both matter. The findings-label result does not reverse the
  primary; for M3 it is +0.0285 (+0.0192, +0.0382).
- **"Identical probabilities".** These agree only to 1.2×10⁻⁷. Under S1
  thresholds, M1's external decisions changed in 44,180 cells and its
  acceptance in 1,633 studies. The exclusive causal attribution to labels was
  removed. Both endpoints are preserved.

## 4. Statistical inference and verdicts

- **H4 rule.** H4 is registered as *secondary*, with direction ≥ 0 and no
  materiality. Its direction-only rule was implemented before results (commit
  `b6052a7`). "+0.0173 confirmed" and "+0.0060 confirmed" are therefore
  correct under H4's rule, and the manuscript's description of a single 0.02
  rule was a reporting error (P-01).
- **Registered estimands.** H2 registers only C1. The registered H3
  (MET006-based) is algebraically H2-C1, because M1 ignores context. The
  transfer-gap H3 and the H2-C2 rows were defined in code after inspection
  (P-02).
- **Verdict function.** One machine-readable function
  (`c3e.revision.verdict`) separates five verdict categories. It reports
  separately whether the interval clears materiality and whether it lies
  within ±0.02. Its 16 test functions (19 cases) cover sign handling, equality at thresholds,
  intervals crossing zero, invalid values and reversed direction. All tables,
  figure inputs, abstract numbers and replication statements were regenerated
  from it.
- **Multiplicity.** The original multiplicity rules were Holm across
  pathologies (registry) and per-hypothesis families across pathologies (SAP).
  Neither was executed. Holm had been applied to four H4 p-values at the
  bootstrap floor (I-05). Post hoc, we added Holm across pathologies and a
  Bonferroni (k=6) sensitivity for the confirmatory contrasts, both labelled as
  not prespecified.
- **Bootstrap checks.** We verified patient clustering, pairing within site,
  independence across sites, and the H3 shared draw (the fast replay
  reproduces Stage 10 exactly; unit tests). Intervals are now stated to
  condition on fitted models, the realised calibration sample and the C2
  realisation.
- **Calibration uncertainty.** Calibration-sample uncertainty was quantified
  at 1.5–3.4× the evaluation SD (Table 11). The training seed is distinguished
  from evaluation precision.
- **The 50% property.** Restated correctly: at most 1/2, equal to 1/2 once
  δ ≥ 1.96·SE. It is an elementary boundary property and is not presented as
  a contribution.

## 5. Selective policy

- **Confidence score.** The |2p−1| score is centred at 0.5, while thresholds
  span 0.41–0.99. It ranks study-level correctness weakly (failure AUROC
  0.60–0.65), and per-cell results are mixed (supplement).
- **Comparators.** All are fitted on the source calibration tier only: a
  per-pathology temperature-scaled margin (registry-required), a decision-aware
  Platt expected-loss score, and split-conformal singleton acceptance
  (registry-required). The expected-loss score ranks errors better (AUROC
  0.69–0.76), but its coverage drifts more externally (M4: 0.855). Conformal
  cannot reach 80% calibration coverage.
- **Curves and operating points.** Risk–coverage curves are shown with the
  observed operating points (Fig. 4). Per-pathology sensitivity, specificity,
  FN/FP and positive-call rates are given, and frozen thresholds shifted
  operating points (M4 cardiomegaly specificity 0.82 → 0.44).
- **Coverage.** Source target and realised external coverage are reported
  separately.
- **Selection versus prediction.** These are separated for the interventions
  in both orders, plus the full cohort (Table 10). Accepted-set Jaccard is
  0.64–0.85.
- **Recalibration.** It was not evaluated, because external tuning is
  prohibited. The unsupported "recalibration would conceal" claim was removed.

## 6. Cohorts, interventions, robustness

- **Counts.** All counts were reconciled to the artifacts (Table 1). We
  corrected 200 → 199 excluded studies and 134 → 133 in the waterfall, and
  explained the external natural-state off-by-one. The disjointness of the
  tiers is verified by construction and by the partition audit.
- **WET READ.** The 17,551 (7.70%) figure was verified. Extracted context was
  inspected without exporting text. No section headers appear in extracted
  context; conclusion-like phrases occur in 0.45% (source) and 0.02%
  (external) of contexts. Temporal claims are qualified.
- **C2 audit.** All 6 + 34 "retained" rows are identical text from a
  **different** patient, with zero same-patient donors (I-03). C2 is per
  image. Two additional source permutations and one external permutation
  leave H4 essentially unchanged for every text-using model.
- **Seeds.** The M1/M4 second seed was re-analysed under the corrected
  estimator, and M2 was retrained under the same seed so that M3 could be
  replicated. The second seed moved the corrected H1 by about −0.04 for both
  multimodal models (M4 −0.002 → −0.047; M3 −0.004 → −0.040). It also removed
  M3's external context effect: H4 is +0.0011 (−0.0010, +0.0031) against
  +0.0263. The manuscript's within-site claim is narrowed to the source site.
  Magnitudes, not only verdicts, are reported.
- **Exploratory strata.** View (AP/PA) and external demographic strata are
  reported as exploratory.
- **Not run, with reasons** (`EXPERIMENT_LEDGER.md`): a third site and reverse
  transfer.

## 7. Manuscript contradictions

Each listed contradiction was checked against the artifacts and corrected with
recomputed numbers, not hedged prose: R-01, R-08–R-15, R-17, R-18, R-22,
R-23. Every headline number in the revision is a generated macro traceable to
`results/c3e_revision/`.

## 8. Novelty

All citations were re-verified on 6 Oct 2026 (bibliography notes say where
only an abstract could be read). Closer work was added: failure-detection
evaluation and benchmarks, rejection for multi-label CXR, and label-validity
studies. Claims that prior studies "usually" or "typically" re-fit thresholds
were removed. The framing is now both a scoped compound-shift evaluation and a
controlled demonstration of endpoint-dependent cross-site benchmarking.
Data-integrity checks are not described as clinical validation.

## 9. Manuscript and reproducibility materials

- **Rewritten.** Title, abstract, objectives, methods (with equations),
  results, discussion, limitations and conclusion.
- **Protocol history.** Dated, including the two pre-data planning documents
  and the post-inspection decisions. Hashes are described as content identity
  only.
- **Training and evaluation details.** Recovered from code and logs.
- **Back matter.** Ethics, funding, competing interests, contributions and
  repository URL are explicit placeholders (`SUBMISSION_CHECKLIST.md`).
- **Builds.** The PDF compiles with no undefined references and no overfull
  boxes.

## 10. Readiness

See `READINESS_ASSESSMENT.md`.
