# Revision R1 experiment ledger (2026-10-06)

Every analysis below was run after the external results of 2026-08-07 were
inspected and is post hoc unless marked otherwise. Bootstrap: 2,000
patient-clustered replicates, seed 20260718, in the Stage 10 draw order,
unless stated. Commands run from the project root with
`c3e_audit_toolkit/.venv/bin/python` (written `python` below).

## Completed

| # | Analysis | Inputs | Command | Seeds | Output | Notes / limitations |
|---|---|---|---|---|---|---|
| 1 | Protocol validation; full test suite | registry; toolkit | `python protocols/C3E6_stage2/scripts/validate_protocol.py`; `cd c3e_audit_toolkit && python -m pytest -q` | — | 30/30 checks; 224 tests pass (187 original + 37 revision) | — |
| 2 | Study-identity alignment of all Stage 8/9b caches | caches; label CSVs/JSON; manifests; report archive; metadata | `python -m c3e.revision.runner --only alignment` | — | `results/c3e_revision/alignment_checks.csv`; row-level parquet in `data/revision/alignment/` | 10/10 caches reproduced exactly. One external image was lost after the primary run and is restored for alignment only. |
| 3 | Stage 10 replay (original estimator) | caches; Stage 7 JSON | `--only hypotheses` | 20260718 | `stage10_reproduction.csv` | 63/63 rows identical at 6 decimals |
| 4 | Stage 7 re-selection from fresh calibration-tier inference | calibration tier (purpose=calibration) | `python -m c3e.revision.inference --site source --tier threshold_calibration ...` (GPU, ~10 min); `--only comparators` | — | `stage7_reproduction.csv` | M1–M4 primary and M1/M4 replicate thresholds and cutoffs identical |
| 5 | Hypothesis family × estimators (original, evaluable-study, cell, pathology-macro) × label variants (primary, unmentioned→neg, uncertain→pos/neg); coverage 70/90; T=5/10; S1; seed replicate | caches; frozen Stage 7 | `--only hypotheses` | 20260718 | `hypotheses.csv`, `levels.csv`, `coverage_gap.csv` | Evaluable-study is the bug-corrected primary. Label variants are sensitivity brackets, not reference standards. |
| 6 | Pathology-specific contrasts with Holm across pathologies | as 5 | `--only pathology` | 20260718 | `pathology_contrasts.csv` | SAP requirement, run post hoc |
| 7 | Controlled label-source decomposition (A0, A1, A1c-I/F, A2x, A2, A3, B2) | impression + findings caches; both Stage 7 | `--only label_source` | 20260718 | `label_source_contrasts.csv`, `label_source_levels.csv`, `label_source_meta.json` | Reproduces published S1 exactly (A3). Under the corrected estimator the cohort effect is exactly 0. |
| 8 | Label audit (pos/neg/unc/unm by site × source × pathology; before/after abstention; cross-section agreement) | aligned cohorts | `--only label_audit` | — | `label_audit_*.csv`, `label_agreement.csv` | Aggregates only |
| 9 | Selective diagnostics: risk–coverage, AURC, AUGRC, failure AUROC (study, cell), operating characteristics (primary and unmentioned→neg) | as 5 | `--only selective` | 20260718 | `rc_curves.csv`, `threshold_free.csv`, `failure_detection.csv`, `operating_characteristics.csv` | AURC/AUGRC over evaluable studies |
| 10 | Context selection vs prediction decomposition | as 5 | `--only context` | 20260718 | `context_decomposition.csv` | Both orders; not unique |
| 11 | C2 donor audit (replay verified against `apply_c2`) | image-level N1 frames | `--only c2` | C2 seed 20260718 | `c2_audit.csv` | 0 same-patient donors; per-image assignment documented |
| 12 | View strata (AP-only / PA-only) at both sites; external demographic strata (MET016/017) | aligned cohorts; metadata; CheXpert Plus demographics | `--only subgroups` | 20260718 | `view_strata.csv`, `external_demographics.csv`, `external_demographic_disparity.csv` | Exploratory; no source demographics |
| 13 | Comparator policies: temperature-scaled margin, decision-aware expected loss (Platt), split-conformal singletons | calibration-tier caches (source only) | `--only comparators` | — | `comparators.csv`, `comparator_ranking.csv`, `comparator_fits.json` | Fitted on the source calibration tier only. Conformal cannot reach 80% calibration acceptance. |
| 14 | Calibration-sample uncertainty (re-apply frozen selection rule to resampled calibration patients) | calibration-tier caches | `--only calibration_uncertainty` | 20260718, 200 replicates | `calibration_uncertainty.csv` | Not nested with evaluation bootstrap |
| 15 | Stage 6 runs recovered from logs | `logs/stage6_*.log` | `--only stage6_curves` | — | `stage6_runs_from_logs.json` | Corrects the spliced M2 curve |
| 16 | Additional source C2 permutations (M2, M3, M4) | eval tier; primary checkpoints | `scripts/run_revision_gpu_queue.sh` step 2; `--only followup` | C2 seeds 20260719, 20260720 | `followup_c2_permutations.csv` | H4 for M3/M4 stable across three permutations |
| 17 | Tables, number macros, figures | all of the above | `python -m c3e.revision.report` | — | `paper/revision/generated/`, `paper/revision/figures/` | No hand-typed numbers in the revision |
| 18 | Revised manuscript and supplement | 17 | `cd paper/revision && latexmk -pdf main_revised.tex supplement_revised.tex` | — | `main_revised.pdf` (20 pp), `supplement_revised.pdf` | Zero overfull boxes or undefined references |

## GPU queue (complete 2026-10-07 03:04)

| # | Analysis | Command | Est. time | Status / how to finish |
|---|---|---|---|---|
| 19 | M2 retrained, seed 20260719 (model-train tier; frozen v0.4.2 settings) | `bash scripts/run_revision_gpu_queue.sh` (step 3) | 6.1 h | **done** 2026-10-06 21:42: early stop after 5 epochs, best epoch 2, internal-validation AUROC 0.7683 (`stage6_runs_from_logs.json`) |
| 20 | M2/M3 replicate: calibration, source, external inference; family analysis | queue step 4; then `python -m c3e.revision.runner --only followup` and `python -m c3e.revision.report` | 3.5 h | **done** 2026-10-07 01:11. Thresholds by the frozen rule on the calibration tier (`followup_m2m3_selection.json`); replicate M1/M4 rows reproduce the earlier seed analysis exactly (21/21). Corrected H1 M3 −0.0402 (−0.0503, −0.0298) vs −0.0042 primary; H4 M3 external +0.0011 (−0.0010, +0.0031) vs +0.0263. Main text updated. |
| 21 | External C2 permutation (seed 20260719) | queue step 5; then `--only followup` and `python -m c3e.revision.report` | ~1.5 h | **done** 2026-10-07 03:04 (M4 pass rerun after a session interruption). H4 external, corrected: M2 +0.0068, M3 +0.0252 (+0.0228, +0.0275), M4 −0.0063 (−0.0086, −0.0039), against +0.0076, +0.0263 and −0.0077 with the frozen draw. No conclusion depends on the donor draw. |

## Failed or abandoned attempts (kept for the record)

| Attempt | What happened | Resolution |
|---|---|---|
| External alignment, first pass | 132,922 vs 132,923 rows: one image lost from storage after the primary run | Exact-match search over missing paths; only the lost image's restoration reproduces the cache |
| Runner, first full pass | Collation bug in label-source levels (`config` keyword duplicated) | Fixed; rerun |
| Split-conformal at 80% coverage | With one α across pathologies, calibration acceptance peaks at 47–59% (atelectasis sets rarely singleton) | Reported at the closest achievable acceptance; not comparable at equal coverage |
| Figure 3 operating-point marker | Plotted at all-study coverage on an evaluable-coverage axis | Evaluable coverage added to `levels.csv`; regenerated |
| GPU queue, 2026-10-07 ~02:25 | Session interrupted during the M4 external C2 pass; partial M4 work lost (M2/M3 caches intact) | Queue resumed 02:39; cached steps skipped |
| Follow-up with partial external caches | `_aligned_common` decompressed the `.npz` array once per row (>20 min) | Array loaded once; 37 s |

## Not run (with reason)

| Analysis | Reason | What would be needed |
|---|---|---|
| Expert adjudication | Requires radiologists, data-use coverage and ethics determination | `docs/revision/EXPERT_ADJUDICATION_PROTOCOL.md` |
| One-image-per-study, concordant-study (SAP) | Caches are study-level; image-level predictions were never saved | New inference at both sites for all models × conditions (~8 h GPU) with image-level caching |
| Per-study C2 re-implementation | Would change the frozen intervention; needs new inference | ~4 h GPU (both sites, M2–M4) |
| Target-site recalibration comparator | Protocol and AGENTS.md prohibit external-site tuning | Explicit authorisation and a held-out external split |
| Reverse transfer (CheXpert Plus → MIMIC) | Training on the external site is not authorised; ~2–3 GPU-days | Authorisation and compute |
| Third compatible site | No locally available dataset with pre-diagnostic text and comparable labels | New data access |
| Further training seeds (≥3 per model; two now exist for all four) | Compute: M4 ≈ 12 h, M1 ≈ 6 h, M2 ≈ 6 h per seed | Run `python -m c3e.training.runner --models M1,M2,M4 --seed <s>` then the revision inference steps |
| Nested calibration × evaluation × training uncertainty | Compute and design | Combine 14 with additional seeds |
| Source-site demographics | MIMIC-IV not acquired | Acquire `patients`/`admissions` under the existing credential |
