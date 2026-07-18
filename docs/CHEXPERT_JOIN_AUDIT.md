# CheXpert Plus Join & Label-Resource Audit (C3E-E2)

Status: **row-level data inspected on 2026-07-18** (aggregate/schema only — no raw
text, no identifier values, source files unmodified). This supersedes the
"pending / file-index only" label rows in `CHEXPERT_SCHEMA_MAPPING.md`: the three
`labels/*_fixed.json` files are the actual pathology-label resources and have now
been opened and audited.

Machine-readable companions: `results/c3e_chexpert_plus/schema_join_audit.json` and
`results/c3e_chexpert_plus/study_key_correction.json`.

> **CORRECTION (2026-07-18, later same day).** An earlier draft of §2/§6 of this
> document concluded that *"no reliable study identifier exists."* **That conclusion
> is retracted.** A corrective audit confirmed a valid composite study key —
> `patient_folder + study_folder` (from the image path) — yielding **187,711** studies,
> exactly the officially documented count. See §2b and `study_key_correction.json`. The
> retracted conclusion came from misreading per-image variance of the full `report`
> field as an absence of study structure; the structured label sections
> (impression/findings) are ~97% duplicated within a study.

## 1. Files audited

| File | Rows/Records | Structure |
|---|---|---|
| `data/chexpert_plus/df_chexpert_plus_240401.parquet` | 223,462 rows × 27 cols | columnar table |
| `data/chexpert_plus/labels/findings_fixed.json` | 223,462 records | **JSON Lines** (one object per line) |
| `data/chexpert_plus/labels/impression_fixed.json` | 223,462 records | **JSON Lines** |
| `data/chexpert_plus/labels/report_fixed.json` | 223,462 records | **JSON Lines** |

Note: the three label files are JSON **Lines**, not single JSON documents
(parsing as one document fails with "Extra data: line 2"). Stream them line by line.

## 2. Verified join key

**`path_to_image`** is the join key.

- Parquet `path_to_image`: 223,462 unique / 223,462 rows, 0 null → **row-unique**.
- Parquet `path_to_dcm`: also row-unique (alternative image key, DICOM path).
- Each JSON record carries a `path_to_image` field; keys are unique within each file
  (0 duplicates) and the three files share an **identical, row-order-identical** key set.

### Join result (each JSON file → parquet)

| Metric | findings | impression | report |
|---|---|---|---|
| Label records | 223,462 | 223,462 | 223,462 |
| Unique keys | 223,462 | 223,462 | 223,462 |
| Duplicate keys | 0 | 0 | 0 |
| Matched main rows | 223,462 | 223,462 | 223,462 |
| Unmatched main rows | 0 | 0 | 0 |
| Unmatched label records | 0 | 0 | 0 |
| Expansion factor | 1.0 | 1.0 | 1.0 |
| **Cardinality** | **one-to-one** | **one-to-one** | **one-to-one** |

No unexplained many-to-many join exists or was accepted.

### Rejected join/key candidates

- **`section_accession_number`** — 175,848 unique / 223,462; contains a mega-bucket
  (one accession value maps to 776 images) and is **many-to-many** with the study key.
  Unusable as an image or study key. (Rejected as a *key*; this does not bear on the
  path-derived study key, which is valid — see §2b.)
- **`report` text** — near-unique per row (223,460 / 223,462) but text-valued; not a join
  key and cannot be exported.

### 2b. Composite study key — VERIFIED (2026-07-18 corrective audit)

The image path parses (via `PurePosixPath`) into exactly 4 components:
`split / patient_folder / study_folder / image_filename` (0 parse failures on 223,462 rows).
The `study_folder` label is **not** globally unique — it restarts within each patient — so it
must be combined with the patient component.

**Verified study key: `patient_folder + study_folder`** (equivalently `deid_patient_id +
study_folder`; all three tested candidates induce the *identical* partition):

| Metric | Value |
|---|---|
| Unique studies | **187,711** (= official count, not forced) |
| Parse/null keys | 0 |
| Images per study | min 1, median 1, mean 1.19, max 3 |
| Studies with >1 image | 33,973 |
| Studies spanning multiple patients | 0 |
| Studies spanning multiple splits | 0 |
| Studies with inconsistent `deid_patient_id` | 0 |

Within-study **normalized** section consistency (sha1 over whitespace-collapsed, lowercased
text — hashes computed locally, never exported):

| Section | Studies consistent |
|---|---|
| `section_clinical_history` | 99.3% |
| `section_history` | 99.1% |
| `section_impression` | 97.1% |
| `section_findings` | 96.5% |
| complete section tuple | 96.1% |
| full `report` field | 81.9% |

The prior "path `studyN` is just a per-image counter" claim is **withdrawn**: the folder is a
genuine study grouping. The apparent inconsistency was driven by the **full `report` field**,
which is captured per-image and therefore varies across ~all 33,973 multi-image studies — even
after normalization (33,971 before and after). The label-relevant sections are ~97% shared
within a study. A real minority (~16% of multi-image studies, 5,462) pair genuinely different
impression text; documented as a caveat, it does not invalidate the key.

## 3. The three label resources

All three files have the **same 15 fields**: `path_to_image` + 14 standard CheXpert
pathologies (`Enlarged Cardiomediastinum, Cardiomegaly, Lung Opacity, Lung Lesion, Edema,
Consolidation, Pneumonia, Atelectasis, Pneumothorax, Pleural Effusion, Pleural Other,
Fracture, Support Devices, No Finding`). Same ontology, same identifier, same key set.

### Label encoding (verified, all three files)

| Value | Meaning |
|---|---|
| `1.0` | positive |
| `0.0` | negative |
| `-1.0` | uncertain |
| `null` (missing) | unmentioned in the labeled text scope |

### They differ only by source-text scope (label density)

Non-`unmentioned` counts rise monotonically **findings < impression < report**, and the
files disagree on tens of thousands of the five target labels each (e.g. Pleural Effusion:
125,763 findings-vs-impression disagreements). They are **not** copies — they are the same
labeler applied to different text scopes.

Five-target positive counts:

| Label | findings pos | impression pos | report pos |
|---|---|---|---|
| Cardiomegaly | 10,971 | 30,558 | 36,172 |
| Edema | 12,148 | 53,011 | 54,255 |
| Pleural Effusion | 24,511 | 89,267 | 94,076 |
| Atelectasis | 9,136 | 33,851 | 38,283 |
| Consolidation | 4,159 | 13,702 | 14,709 |

`findings` is sparse because `section_findings` is null in 163,993 / 223,462 rows (73%);
`impression`/`report` are dense because `section_impression` is present in 99.9% of rows.

### Inferred meaning (INFERRED — not confirmed by in-file metadata)

- **`findings_fixed`** — labels extracted from the **findings** section text scope.
- **`impression_fixed`** — labels extracted from the **impression** section text scope.
- **`report_fixed`** — labels extracted from the **full report** text scope.

This matches the CheXpert Plus design (a CheXbert-style labeler run over each scope) and is
consistent with the density ordering and with substring containment (see §4), but the files
themselves carry no explicit scope metadata, so the interpretation is marked **inferred**.
The label file is **not** selected from its filename alone — the selection below rests on the
verified leakage and density evidence.

## 4. Leakage assessment

Permitted model inputs: `section_clinical_history`, `section_history`.
Excluded from input: `section_narrative`, findings, impression, any target-source text.

Substring containment (aggregate, verbatim):

- The **`report`** field contains **100%** of non-empty `section_clinical_history`,
  `section_history`, `section_findings`, `section_impression`, and `section_narrative`.
  → `report` is the concatenated superset of every section, including the permitted inputs.
- The permitted inputs almost never appear inside the label sections:
  `clinical_history ⊂ impression` = 0.011%, `⊂ findings` = 0.011%;
  `history ⊂ impression` = 0.008%, `⊂ findings` = 0.0%.

| Label resource | Verdict |
|---|---|
| **`findings_fixed`** | **No apparent input leakage.** Labels come from `section_findings`, which is excluded from input and effectively never contains the input text. Indirect derivation (target built from a section we exclude) must be documented. |
| **`impression_fixed`** | **No apparent input leakage.** Labels come from `section_impression`, excluded from input, effectively never contains the input text. Indirect derivation must be documented. |
| **`report_fixed`** | **DIRECT input-target leakage / circular evaluation.** The report scope contains 100% of both permitted input sections, so its labels are derived from text that *includes* the model input. **Reject** for this design. |

Per the project rules, deriving labels from findings or impression while those sections are
excluded from model input is **permitted but must be documented** — it is not itself invalid.

## 5. Recommended label resource

**Primary: `impression_fixed.json`.** No input leakage, dense labels (impression present in
99.9% of rows), and all five targets have thousands of positives — comfortably above the
gate's `min_target_positive` (200).

**Mandatory sensitivity endpoint: `findings_fixed.json`** — cleanest imaging-observation
target but sparse (73% of rows lack a findings section → mostly `unmentioned`); it cannot be
the primary, but every primary result is re-checked against it.

**Reject: `report_fixed.json`** (leakage).

Status: **APPROVED (2026-07-18).** `impression_fixed.json` = primary full-cohort endpoint,
`findings_fixed.json` = mandatory sensitivity endpoint, `report_fixed.json` = excluded. This
supersedes the earlier "pending sign-off" note. Cross-site labeler harmonization applies —
see `LABEL_HARMONIZATION_PLAN.md`.

## 6. Observation hierarchy

`df_chexpert_plus_240401` is an **image-level table**: one row per chest-X-ray image,
uniquely keyed by `path_to_image` / `path_to_dcm` (0 duplicates, 0 nulls). Report and all
`section_*` text are **denormalized** onto each image row. Confirmed hierarchy:

```
patient (deid_patient_id, 64,725)
  └─ study / report  (patient_folder + study_folder, 187,711 — matches official count)
       ├─ image 1  (path_to_image)
       └─ image 2  (path_to_image)   [median 1, mean 1.19, max 3 images per study]
```

The three JSON label files are also **image-level** (one record per `path_to_image`) and
join one-to-one. A **reliable study key exists** (§2b) — `patient_folder + study_folder`.
For leakage-safe splits, group at the **patient** level (`deid_patient_id`); for evaluation,
cluster at the **study** level (report sections are shared within a study).

## 7. Frontal-image structure per study

Among the 187,711 studies (frontal = `frontal_lateral == "Frontal"`):

| Category | Studies |
|---|---|
| Zero frontal images (lateral-only) | 37 |
| Exactly one frontal image | 184,318 |
| More than one frontal image | 3,356 |
| AP-only (frontal) | 158,938 |
| PA-only (frontal) | 28,614 |
| Both AP and PA frontal | 122 |

98.2% of studies have a single frontal image. A study-equal-weighted all-frontal primary policy and
three sensitivities were subsequently locked in `CHEXPERT_MULTIPLE_IMAGE_POLICY.md`; audit estimates
were effectively insensitive to that choice.

## 8. Authorization

- A safe merged manifest **can** be created (verified 1:1 label join + verified study key;
  no text/IDs need to be printed). Not created yet, per task instructions.
- **Configs built (2026-07-18):** `chexpert_plus_impression.yaml` (primary) and
  `chexpert_plus_findings.yaml` (sensitivity) now exist, pass schema validation and unit
  tests, and pass a **dry-run against the real data** — 223,462 rows, 187,711 studies, 0
  study-key parse failures, one-to-one label join with 0 unmatched. They are consumed by the
  new `c3e-audit chexpert --config <file> [--dry-run]` command, which loads the JSONL labels,
  derives the study key into an internal-only column, verifies cardinality, and writes only
  aggregate-safe reports to isolated per-source directories. See `CHEXPERT_CONFIG_DECISION.md`.
- `scripts/run_chexpert_audit.sh` (legacy `c3e-audit table` path) still points at the old
  single-table `chexpert_plus.yaml` and is superseded for CheXpert Plus by the `chexpert`
  command. The CheXpert-only **full audit was run on 2026-07-18** for both label sources under
  the preregistered multiple-image policy; both pass the data-validity gate and all outputs are
  aggregate-safe and scan-clean (`CHEXPERT_FULL_AUDIT_REPORT.md`,
  `CHEXPERT_MULTIPLE_IMAGE_POLICY.md`). Cross-site analysis remains blocked on MIMIC access +
  CheXbert harmonization.
