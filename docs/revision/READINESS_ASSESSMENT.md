# Final adversarial review and submission-readiness assessment (R1, 2026-10-06)

## Verdict

**Not ready for submission.** The revision fixes the reporting and
implementation problems I could verify. The study it now describes is honest
and internally consistent. But the paper's original central question, whether
the frozen policy's error degrades across hospitals, is **not answerable** with
the available labels. Two things also remain open: mandatory author statements,
and the venue builds, which still carry the withdrawn conclusions. The M2/M3
replicate is complete (2026-10-07) and has been folded into the manuscript.

A submission now would rest on two defensible claims. First, a controlled
demonstration that report-derived label availability and handling decide the
sign of a cross-site selective-risk contrast; the published headline was an
estimator artifact. Second, within-site context-intervention results that are
stable across specifications. Reviewers will scrutinise a post hoc correction
that reverses the preregistered primary result. The revision addresses this by
retaining both estimators, dating every decision, and showing the defect
mechanically (an identity plus a synthetic unit test). Even so, reviewers may
discount the paper for it.

The strongest available upgrade is the expert adjudication protocol in this
folder. It is the only analysis that could turn "not identified" into an
answer.

## Concern-by-concern status

| # | Review concern | Status | Evidence / remaining blocker |
|---|---|---|---|
| 1 | Audit before changing claims; isolate work; issue register; code ↔ PDF correspondence | **Resolved** | 63/63 Stage 10 rows and all Stage 7 selections reproduced exactly; 10/10 caches aligned; branch `revision/2026-10-audit`; 43-issue register. Two quoted statements not found in any source (R-19); needs the user to confirm which PDF was reviewed. |
| 2 | What the endpoint measures (labels, loss, masks, label-less studies, coverage definitions, counts, mechanisms, expert labels) | **Resolved**, except expert labels | Verified defect I-01 corrected; equations in Methods; full count tables; agreement 95–99.7% on common cells. **Blocker:** no expert reference (L-01); adjudication protocol prepared, not run. |
| 3 | Isolate the label-source effect | **Resolved** | Steps A0–A3, A1c, A2x, B2 with sizes, densities, thresholds, coverage, intervals; cohort effect is 0 under the corrected estimator; labels and thresholds both matter; not additive in general (two orders reported). |
| 4 | Inference and verdicts | **Resolved**; uncertainty **partly mitigated** | Authentic H4 rule recovered (pre-results commit); single tested verdict function; post hoc multiplicity sensitivities; conditioning stated; calibration-sample SD 1.5–3.4× the evaluation SD. **Remaining:** no nested calibration × evaluation × training interval. |
| 5 | Selective policy validity | **Resolved** | Failure AUROC 0.60–0.65; threshold-centred, temperature, decision-aware and conformal comparators (calibration tier only); risk–coverage curves; per-pathology sensitivity/specificity; realised vs target coverage; selection/prediction split; recalibration not evaluated (prohibited) and the related claims removed. |
| 6 | Cohorts, interventions, robustness | **Partly mitigated** | Counts reconciled; WET READ verified; context scan; C2 audit (no violations; per-image assignment); 2 extra source permutations; second seed for all four models; one extra external permutation (H4 unchanged). **Remaining:** one-image and concordant sensitivities unrun; no third site; source demographics unavailable. |
| 7 | Manuscript contradictions | **Resolved** | R-01, R-08–R-15, R-17, R-18, R-22, R-23 corrected; every headline number is a generated macro. |
| 8 | Novelty and literature | **Resolved** | All references re-verified; closer work added; contribution restated as protocol plus endpoint-dependence demonstration. One journal version (Aperstein et al., Sci. Rep.) could not be retrieved. |
| 9 | Rewrite and reproducibility materials | **Partly mitigated** | Full manuscript and supplement rebuilt; protocol history and amendment log; commands, tests, environment. **Remaining:** ethics, funding, conflicts, contributions, repository URL (author input); venue builds stale. |
| 10 | Deliverables and readiness | **This document** | — |

## Major claims of the revised manuscript, re-checked

| Claim | Supported? | Basis |
|---|---|---|
| Original H1 confirmation was produced by counting label-less studies as correct | Yes | Identity R_orig = R_eval·P(evaluable\|accepted); 47.2% vs 18.7% label-less; corrected H1 ≈ 0; synthetic test reproduces the mechanism |
| Corrected H1 not confirmed; intervals exclude a material increase | Yes, **conditionally** | Conditional on the calibration sample and training run; the calibration SD (≈0.010) is wider than the evaluation SD |
| Cross-site sign not identified across defensible choices | Yes | M4 −0.018 to +0.131 across label handling; seed 2 moves corrected H1 to −0.047 (M4) and −0.040 (M3); AP vs PA differ |
| Published S1 reversal produced by the defect plus asymmetric cohorts | Yes | A0–A3 decomposition; corrected findings H1 is +0.0285 (M3) and +0.0048 (M4) |
| Frozen thresholds did not preserve operating points | Yes, with **verification-bias caveat** | Specificity drop under both primary and unmentioned→negative handling |
| Coverage within 0.05 at C0 | Yes | Both seeds |
| M3: misaligned context worse than absent | **At the source only** (revised 2026-10-07) | Source: every specification, 3 C2 permutations, both seeds. External: every specification for seed 1, but seed 2 gives +0.0011 (−0.0010, +0.0031). M4 holds at the source except seed 2 |
| C2 constraints held | Yes | 0 same-patient donors at both sites |

## Remaining blockers to the original central conclusion

1. No dense, cross-site-comparable reference standard (adjudication needed).
2. Training-seed variability: two seeds per model, and the second moves both
   multimodal transfer gaps by about 0.04.
3. One pair of hospitals in one direction.

## Venue

No venue change is recommended as a way around these issues. The existing
venue plan (`docs/VENUE_SELECTION_PLAN.md`) was made for the superseded
conclusions and should be revisited after the author decides whether to run
the adjudication.
