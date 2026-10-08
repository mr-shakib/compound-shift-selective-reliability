# Independent verification of the JAMIA manuscript

This procedure checks the numbers in `main_jamia_r1.pdf` using only this public
repository. It needs **no** MIMIC-CXR or CheXpert Plus access: everything below
reads code and aggregate results. Do not open or request the restricted
`data/` tree. That needs your own PhysioNet credentials.

Allow two to four hours. Record what you ran and what you saw. The last
section says what to send back.

## 1. Install (once)

```bash
git clone https://github.com/mr-shakib/compound-shift-selective-reliability.git
cd compound-shift-selective-reliability
python3 -m venv .venv
.venv/bin/pip install -e c3e_audit_toolkit pytest matplotlib pyarrow
.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

On Windows, use `.venv\Scripts\python` and `.venv\Scripts\pip` instead of
`.venv/bin/...`. Python 3.10 or newer is required.

## 2. Run the test suite

```bash
.venv/bin/python -m pytest -q c3e_audit_toolkit/tests
```

Expected: `224 passed`.

## 3. Regenerate every number, table and figure

```bash
.venv/bin/python -m c3e.revision.report
git status --porcelain
```

Expected:
- the first command prints `416 macros; tables and figures written`;
- `git status` lists only the five `paper/revision/figures/*.pdf` files.

Their pixels are identical; only the embedded creation date changes. Any change
under `paper/revision/generated/` means a number in the paper no longer matches
the results files. Report it.

## 4. Trace the headline claims to the results files

The manuscript does not hand-type numbers. Each one is a macro in
`paper/revision/generated/numbers.tex`, generated from
`results/c3e_revision/`.

For each claim below:
1. Find the number in the PDF.
2. Find the matching row in the results file.
3. Confirm they agree after rounding.
4. Confirm the sentence says what the number shows.

| # | Claim (where in the PDF) | File in `results/c3e_revision/` | Rows to select |
|---|---|---|---|
| 1 | Studies with no labelled target, source vs external (Abstract; Results; Figure 1) | `label_audit_by_study.csv` | `label_source=impression`, `scope=all_eligible`; column `fraction_no_labelled_cell` |
| 2 | Original transfer gaps for M3 and M4 (Abstract; Table 2) | `hypotheses.csv` | `analysis=primary`, `label_variant=primary`, `hypothesis=H1`, `estimator=original` |
| 3 | Corrected gaps, with intervals inside ±0.02 (Abstract; Table 2) | `hypotheses.csv` | as row 2, with `estimator=evaluable_study`; columns `point_estimate`, `ci_low`, `ci_high` |
| 4 | Label handling moves M4's gap (Abstract; Figure 2) | `hypotheses.csv` | `analysis=primary`, `hypothesis=H1`, `model=M4`, `estimator=evaluable_study`, `label_variant` = `uncertain_positive` and `unmentioned_negative` |
| 5 | Second training seed shifts the gaps (Abstract; Figure 2) | `followup_m2m3_contrasts.csv` (all four models) | `hypothesis=H1`, `estimator=evaluable_study`; compare with row 3 |
| 6 | M4 cardiomegaly specificity, source vs external (Abstract; Figure 3) | `operating_characteristics.csv` | `model=M4`, `pathology=Cardiomegaly`, `condition=C0`, `scope=accepted`, `label_variant=primary` |
| 7 | Coverage stays within 0.05 of target (Abstract; Results) | `coverage_gap.csv` | `analysis=primary`, `condition=C0`; compare `coverage_source` and `coverage_external` with 0.80 |
| 8 | Findings labels do not reverse H1 after correction (Results; Table 3) | `label_source_contrasts.csv` | `config=A3_published_S1`, `hypothesis=H1`, `estimator=evaluable_study` |
| 9 | M3 H4 within each site, and the external result under seed 2 (Abstract; Figure 5) | `hypotheses.csv` (seed 1; add `analysis=primary`, `label_variant=primary`) and `followup_m2m3_contrasts.csv` (seed 2) | `hypothesis=H4`, `model=M3`, `estimator=evaluable_study`, by `site` |
| 10 | Calibration resampling vs evaluation bootstrap (Results; Table 4) | `calibration_uncertainty.csv` | `estimator=evaluable_study`; column `h1_sd_calibration` |

Example lookup for rows 2 and 3:

```bash
.venv/bin/python - <<'EOF'
import pandas as pd
h = pd.read_csv("results/c3e_revision/hypotheses.csv")
q = h[(h.analysis == "primary") & (h.label_variant == "primary") & (h.hypothesis == "H1")]
print(q[["model", "estimator", "point_estimate", "ci_low", "ci_high", "verdict"]])
EOF
```

## 5. Read the interpretation critically

Answer these in writing:
- Does every sentence in the Abstract, Results and Discussion follow from
  Tables 2–4 and Figures 1–5? Is anything stated more strongly than the
  intervals allow?
- Is every analysis added after the external results were seen labelled post
  hoc? Is the original estimate kept beside the corrected one?
- Is the explanation of the estimator defect (Materials and Methods)
  correct and understandable to a JAMIA reader?
- Is an important limitation missing, or an existing one understated?

## 6. What to send back

Send a short note to the corresponding author covering:
1. the outputs of steps 2 and 3;
2. for each of the 10 claims, whether it matched, with any mismatch quoted;
3. your answers to step 5, with suggested changes.

Every mismatch or disagreement is fixed in the analysis or the text before
submission.
