# CheXpert Plus Schema Mapping

Status: **row-level data inspected on 2026-07-18** (C3E-E2, aggregate/schema only — no raw text, no
identifier values printed, source files unmodified). The main parquet table and all three
`labels/*_fixed.json` files have now been opened and their schemas, encodings, join keys, and label
distributions verified. The join and label-resource analysis lives in `docs/CHEXPERT_JOIN_AUDIT.md`
with a machine-readable companion at `results/c3e_chexpert_plus/schema_join_audit.json`.

Earlier context (2026-07-15): the columns below were first confirmed from the Redivis schema export
(`chexpert_plus.json`, dataset `https://stanford.redivis.com/datasets/5yyj-1a9f6ap0x`, DOI
`10.57761/fzna-pm76`, Stanford AIMI). That export carried column names/types only; the `chexpert_labels`
entry was a file index, so the actual label columns were unknown until 2026-07-18. Rows below are now
upgraded to `confirmed` where verified against real values.

## Verified row-level facts (2026-07-18)

- **223,462 rows**, 27 columns. `split`: `train` (223,228) / `valid` (234) — no `test`.
- **Unit of observation: image-level** (one row per image). `path_to_image` and `path_to_dcm` are both
  row-unique (0 dup, 0 null). Report and all `section_*` text are denormalized onto each image row.
- **`frontal_lateral` values (exact casing): `Frontal` (191,071) / `Lateral` (32,391).**
- `ap_pa`: `AP` (161,622) / `PA` (29,432) / `LL` (16) / `RL` (1) / null (32,391 = all lateral rows).
- **Reliable composite study key: `patient_folder + study_folder`** (parsed from `path_to_image`) —
  **187,711 studies, matching the official count** (corrected 2026-07-18; the earlier "no study key"
  finding is withdrawn). `section_accession_number` is still unusable as a key (many-to-many, 776-image
  mega-bucket). Split at **patient** level (`deid_patient_id`); cluster/evaluate at **study** level.
- **Labels live in `labels/{findings,impression,report}_fixed.json`** — JSON Lines, 223,462 records
  each, keyed by `path_to_image`, joining **one-to-one** to the parquet (full match, 0 unmatched).
  14-label CheXpert ontology. **Encoding: `1.0`=positive, `0.0`=negative, `-1.0`=uncertain,
  `null`=unmentioned.**
- **Recommended label resource: `impression_fixed.json`** (no input leakage, dense). `report_fixed.json`
  is **rejected** (direct leakage — its text scope contains 100% of the permitted input sections).
  See `CHEXPERT_JOIN_AUDIT.md` §4–5.

## Source table inspected

`df_chexpert_plus_240401` (223,462 rows, 27 columns) — the main merged report+metadata table in the
CheXpert Plus Redivis dataset. Its confirmed columns (from schema metadata) are:

`path_to_image`, `path_to_dcm`, `frontal_lateral`, `ap_pa`, `deid_patient_id`,
`patient_report_date_order`, `report`, `section_narrative`, `section_clinical_history`,
`section_history`, `section_comparison`, `section_technique`, `section_procedure_comments`,
`section_findings`, `section_impression`, `section_end_of_impression`, `section_summary`,
`section_accession_number`, `age`, `sex`, `race`, `ethnicity`, `interpreter_needed`, `insurance_type`,
`recent_bmi`, `deceased`, `split`.

A separate `chexpert_labels` table exists in the dataset but is itself a **file-index table**
(`file_id`/`file_name`/`size`/`md5_hash`) in the schema export — it indexes a label file rather than
exposing label columns directly, so the actual pathology label column names remain unknown until that
file is opened.

## Mapping table

| Required concept        | Actual table              | Actual column                          | Status            | Notes |
|--------------------------|----------------------------|------------------------------------------|-------------------|-------|
| Patient identifier       | df_chexpert_plus_240401    | `deid_patient_id`                        | confirmed         | De-identified patient ID. 64,725 unique, 0 null. Aligns 1:1 with the `patientN` path folder (0 crossovers). Use for patient-level grouping/splits. |
| Study identifier         | df_chexpert_plus_240401    | **derived: `patient_folder` + `study_folder`** (from `path_to_image`) | confirmed | **CORRECTED 2026-07-18** (was `not_available`). Composite key parsed from the path yields **187,711** studies = official count; 0 multi-patient, 0 multi-split, 0 inconsistent-patient; median 1 / mean 1.19 / max 3 images per study. `study_folder` alone is not global (restarts per patient), so it must be paired with the patient component. The earlier "no study key" call was a misread of per-image `report`-field variance. `section_accession_number` remains unusable as a key (many-to-many, 776-image mega-bucket). See `CHEXPERT_JOIN_AUDIT.md` §2b + `results/c3e_chexpert_plus/study_key_correction.json`. |
| Image identifier         | df_chexpert_plus_240401    | `path_to_image` (and `path_to_dcm`)      | confirmed         | Both row-unique (223,462 unique, 0 dup, 0 null). `path_to_image` is the verified image ID and the JSON join key. |
| View position             | df_chexpert_plus_240401    | `frontal_lateral` (view) / `ap_pa`       | confirmed         | `frontal_lateral` = `Frontal` (191,071) / `Lateral` (32,391) — exact casing confirmed. Used as the toolkit's `view_column`; `frontal_values: [Frontal]` is correct. `ap_pa` (AP/PA/LL/RL, null on all lateral rows) is orthogonal and unused. |
| Clinical History          | df_chexpert_plus_240401    | `section_clinical_history`               | confirmed         | In `context_columns`. Non-empty in 138,860 rows (62%); null 84,596; median 6 tokens. Permitted model input. |
| History                   | df_chexpert_plus_240401    | `section_history`                        | confirmed         | In `context_columns`. Non-empty in only 38,191 rows (17%); null 185,270; median 6 tokens. Distinct from `section_clinical_history` (near-disjoint presence). Permitted model input. |
| Indication                 | df_chexpert_plus_240401    | *(none found)*                           | not_available     | No "indication" column. `section_narrative` (present 97.5%) and `section_procedure_comments` (present 11%) exist but are **excluded** from model input — narrative is the full free-text report body (leakage risk); procedure comments are post-hoc. |
| Cardiomegaly (label)       | labels/*_fixed.json         | `Cardiomegaly`                          | confirmed         | Present in all 3 JSONs. impression pos=30,558 / neg=16,160 / unc=3,921 / unmentioned=172,823. |
| Edema (label)              | labels/*_fixed.json         | `Edema`                                 | confirmed         | impression pos=53,011 / neg=21,229 / unc=12,217 / unmentioned=137,005. |
| Pleural Effusion (label)   | labels/*_fixed.json         | `Pleural Effusion`                      | confirmed         | impression pos=89,267 / neg=36,290 / unc=7,614 / unmentioned=90,291. |
| Atelectasis (label)        | labels/*_fixed.json         | `Atelectasis`                           | confirmed         | impression pos=33,851 / neg=727 / unc=34,401 / unmentioned=154,483. |
| Consolidation (label)      | labels/*_fixed.json         | `Consolidation`                         | confirmed         | impression pos=13,702 / neg=31,452 / unc=26,627 / unmentioned=151,681. |
| Label encoding             | labels/*_fixed.json         | (values)                                | confirmed         | `1.0`=positive, `0.0`=negative, `-1.0`=uncertain, `null`=unmentioned. Matches config `positive/negative/uncertain` = 1/0/-1 and `unmentioned_is_missing: true`. |
| Label join key             | df ↔ labels/*_fixed.json    | `path_to_image`                         | confirmed         | One-to-one, full match (223,462 ↔ 223,462, 0 unmatched, 0 dup, expansion 1.0). |
| Split                      | df_chexpert_plus_240401    | `split`                                  | confirmed         | `train` (223,228) / `valid` (234). No `test` split. `split_column: split` correct. |

## Status values

- `pending` — not yet inspected at all
- `schema_confirmed` — column name/existence verified from the dataset's published schema metadata, but
  real row values (exact strings, encodings, uniqueness) have not been checked
- `confirmed` — verified against real row-level data (reserve for after credentialed access + row
  inspection)
- `not_available` — this concept does not exist in CheXpert Plus in this form; closest substitute (if
  any) noted
- `ambiguous` — multiple candidate columns exist, or the mapping requires a judgment call; documented in
  Notes

## Process — remaining steps (post 2026-07-18 audit)

Schema, identifiers, view casing, split values, label columns, encoding, the join key, **and the
composite study key** are all `confirmed`. The label-source decision is **approved** (see
`LABEL_HARMONIZATION_PLAN.md`): `impression_fixed.json` = primary, `findings_fixed.json` = mandatory
sensitivity, `report_fixed.json` = excluded (leakage).

**Configs built and validated (2026-07-18):** `configs/chexpert_plus_impression.yaml` (primary) and
`configs/chexpert_plus_findings.yaml` (sensitivity) now exist. Each declares `table_path`,
`label_source` (path + `join_key: path_to_image` + one-to-one/`fail`-on-duplicate/`fail`-on-unmatched
policy), a **derived** `study_key` block (`patient_folder + study_folder`, internal column
`_c3e_study_key`), `grouping` (split=patient, cluster=study, observation=image), the 5 targets, the
1/0/-1/null encoding, an `image_policy` (no selection/aggregation this phase), and `safe_output`
(no manifest). They pass `c3e.config_schema.validate_chexpert_config`, the unit tests in
`tests/test_chexpert.py`, and a dry-run against the real data (223,462 rows, 187,711 studies, 0 parse
failures, one-to-one join). Run via `c3e-audit chexpert --config <file> [--dry-run]`.

The `study` mapping is `confirmed` (composite key, derived — never a native column). Split at patient
level; do not split within a study. Remaining before a full CheXpert audit / cross-site run:

1. **Pre-register the multiple-image sensitivity plan** (image-level clustered bootstrap; study-level
   aggregation; one-frontal-per-study) — see `CHEXPERT_CONFIG_DECISION.md` §5. No image-selection rule is
   locked in yet.
2. **Cross-site labeler harmonization** before any cross-hospital experiment: CheXbert impression/findings
   at both MIMIC and CheXpert Plus; never mix MIMIC rule-based CheXpert-labeler output with CheXpert Plus
   CheXbert output. CheXbert is **not** run yet (MIMIC access pending).

Note: `scripts/run_chexpert_audit.sh` still targets the legacy single-table `chexpert_plus.yaml`
(`c3e-audit table`) and is superseded for CheXpert Plus by the `chexpert` command.

**Full audit executed 2026-07-18.** Both endpoints were audited under the preregistered
multiple-image policy; both pass the data-validity gate (combined usable context 60.3%, 5 viable
labels, direct-mention leakage ≤ 3.84% among positives, 0 train/valid patient overlap, image-policy
sensitivity < 0.1 pp). Aggregate-safe outputs are in `results/c3e_chexpert_plus/{impression,findings}/`
and summarised in `docs/CHEXPERT_FULL_AUDIT_REPORT.md`.
