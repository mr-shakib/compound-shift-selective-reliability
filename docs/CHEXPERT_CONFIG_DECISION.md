# CheXpert Plus Configuration Decision (C3-E2)

Status: **decided and implemented 2026-07-18.** Two audit configurations exist and pass
schema validation, unit tests, and a dry-run against the real data (223,462 rows, 187,711
studies, one-to-one label join, 0 parse failures). The full CheXpert audit subsequently passed
for both sources on 2026-07-18. Model training remains **not run and not authorized**.

Companion docs: `CHEXPERT_SCHEMA_MAPPING.md`, `CHEXPERT_JOIN_AUDIT.md`,
`LABEL_HARMONIZATION_PLAN.md`. Config files:
`c3e_audit_toolkit/configs/chexpert_plus_impression.yaml`,
`c3e_audit_toolkit/configs/chexpert_plus_findings.yaml`.

## 1. Label-source decision

| Resource | Role | Config |
|---|---|---|
| `impression_fixed.json` | **Primary, full-cohort endpoint** | `chexpert_plus_impression.yaml` |
| `findings_fixed.json` | **Mandatory sensitivity endpoint** | `chexpert_plus_findings.yaml` |
| `report_fixed.json` | **Excluded** (direct input-target leakage) | none — the schema validator rejects it |

The two configs differ **only** in three fields: `dataset_name`, `label_source.path`, and
`output_dir`. Everything else (identifiers, study key, grouping, view, encodings, gate) is
identical, so the impression/findings comparison is a clean single-variable swap.

## 2. Observation, grouping, and clustering units

- **Observation unit: image.** One row per image; `path_to_image` is the row-unique image
  key and the label join key. No per-study image selection and no label aggregation are
  applied in this phase (`image_policy.select_one_per_study: false`,
  `image_policy.aggregate_labels: false`).
- **Grouping (split) unit: patient** (`deid_patient_id`). Leakage-safe train/eval splits must
  never place a patient on both sides. Non-negotiable.
- **Clustering (evaluation) unit: study** (the derived study key). Report sections are shared
  within a study, so intra-study images are correlated; evaluation must cluster by study.

## 3. Derived study-key rule

There is **no native study column.** The study grouping is derived from `path_to_image` with
`PurePosixPath`:

```
split / patient_folder / study_folder / image_filename
study key = patient_folder + "/" + study_folder
```

- `study_folder` alone is **not** globally unique (it restarts within each patient), so it is
  always paired with `patient_folder`.
- Derivation **fails closed**: a malformed path (wrong component count, `patient_folder` not
  matching `patient\d+`, `study_folder` not matching `study\d+`, empty filename) yields no key
  and is counted; a non-zero parse-failure count aborts a trusted run.
- The key is a quasi-identifier, so it lives **only** in an internal temporary column
  (`_c3e_study_key`) and is **never** written to any safe output. Grouping uses pandas
  groupby over the string key — never Python's process-randomised built-in `hash()`; where a
  stable digest is needed elsewhere, `hashlib.sha1` is used explicitly.
- Verified: 187,711 unique studies (= official count), 0 parse failures on the real data.

## 4. Label encoding (four-state, preserved)

`1` positive · `0` negative · `-1` uncertain · `null` unmentioned (`unmentioned_is_missing:
true`). The JSONL loader preserves all four states — `null` stays distinct from `0`.

## 5. Multiple-image policy — PREREGISTERED and executed (2026-07-18)

The policy is now locked in `CHEXPERT_MULTIPLE_IMAGE_POLICY.md` and encoded in both configs
(`analysis_policy` + `sensitivity_analyses`, schema-validated). Primary: frontal-image
observation unit, **study-equal weighting** (each study's frontal images share total weight 1),
retain all frontal images, no label aggregation, no image selection. Uncertainty (later): a
**patient-clustered bootstrap**, ≥ 1,000 replicates, whole clusters, fixed seed. Sensitivities:
(A) unweighted image-level, (B) one-frontal-per-study by a deterministic label-blind rule
(lowest view number, then stable lexical), (C) target-specific concordant-study subset.

Executed result: the choice barely matters — within-study disagreement ≤ 0.09% across 3,356
multi-frontal studies, and prevalence shifts < 0.1 pp across all four policies for every target
(`CHEXPERT_FULL_AUDIT_REPORT.md` §6, `image_policy_sensitivity.csv`).

## 6. Cross-site harmonization (MIMIC)

Required **only before cross-site experiments**, not for the CheXpert-only audit. The primary
cross-hospital comparison must use CheXbert impression labels at both sites and CheXbert
findings labels at both sites; MIMIC's default rule-based CheXpert-labeler output must not be
mixed into the primary tables. CheXbert is not run yet (MIMIC access pending). See
`LABEL_HARMONIZATION_PLAN.md`.

## 7. Safe-output guarantees (implemented + tested)

- Configs write to **separate** directories (`results/c3e_chexpert_plus/impression/` and
  `.../findings/`); a `source_marker.json` in each dir makes the writer **refuse** to
  overwrite another source's outputs.
- No patient-, study-, or image-level manifest is written (`safe_output.write_manifest:
  false`). The legacy `study_aggregate.csv` sensitive export is not produced by the `chexpert`
  command.
- Safe outputs contain only counts, percentages, column names, label names, distributions,
  aggregate disagreement statistics, and gate results. A unit test runs the full pipeline on a
  synthetic dataset seeded with sentinel identifier values and asserts none appear in any
  produced file.

## 8. New config schema fields (parser extended + tested)

`table_path`, `label_source{path,format,join_key,cardinality,on_duplicate_keys,on_unmatched}`,
`study_key{derived,source_column,method,internal_column}`,
`grouping{split_unit,cluster_unit,observation_unit}`, `ap_pa_column`,
`image_policy{select_one_per_study,aggregate_labels,frontal_only}`,
`safe_output{write_manifest,forbid_identifier_columns}`, `output_dir`.

All are validated by `c3e.config_schema.validate_chexpert_config` (unknown keys rejected;
`report_fixed.json` rejected; a native `id_columns.study` rejected). See
`tests/test_chexpert.py`.

## 9. Authorization status

- CheXpert-only **dry-run**: authorized and passing.
- CheXpert-only **full audit** (`c3e-audit chexpert` without `--dry-run`): **run 2026-07-18** for
  both sources; both pass the data-validity gate; outputs aggregate-safe and scan-clean
  (`CHEXPERT_FULL_AUDIT_REPORT.md`).
- **Cross-site** analysis: still blocked on MIMIC access + CheXbert harmonization (§6).
- **Model training / CheXbert / MIMIC processing / image download**: not run, not authorized.
- Before **modeling**: a proper patient-level resplit is required (the shipped `valid` split is
  only 202 frontal images / 200 patients).
