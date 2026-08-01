# C3-E6 — Source Text Mapping and Context Informativeness Rule

Status: **PROPOSED — awaiting approval.** Nothing in `protocols/C3E6_stage2/` has been
modified. This document resolves the two placeholders that currently block Stage 3C.

Evidence base: `results/c3e_mimic/stage3a/`, `results/c3e_mimic/stage3b/`,
`results/c3e_mimic/stage3b2/` (all hash-verified, produced without images, labels, or models).

---

## 1. Why this is not an amendment

Two items are often mistaken for frozen scientific decisions. They are not.

`protocols/C3E6_stage2/config/experiment_registry.yaml` declares:

```yaml
text_policy:
  permitted_sections_external:
  - section_clinical_history
  - section_history
  permitted_sections_source:
  - PENDING_MIMIC_INTAKE_MAPPING
```

`permitted_sections_source` is an explicit pending slot, authored to be filled by the MIMIC
intake work. Filling it executes the protocol as written.

`context_interventions.yaml` defines state N1 as *"Permitted context exists and passes the
**frozen informativeness rules**."* Those rules are referenced but never defined anywhere in
the repository. Defining them completes the registry rather than revising it.

The frozen scientific decisions in `AGENTS.md` — target pathologies, label sources, bootstrap
replicates and seed, resampling unit, coverages, threshold transfer, C0/C1/C2 semantics — are
**untouched by this proposal**.

## 2. Site roles (restated, because they are easy to invert)

| Role | Dataset | Registry role | Tuning |
|---|---|---|---|
| **Source** | `mimic_cxr_jpg` v2.1.0 | `development_and_internal_evaluation` | permitted |
| **External** | `chexpert_plus` | `locked_external_evaluation_only` | `tuning_allowed: false` |

MIMIC is the **source** site. This matters for governance:
`governance.external_dataset_prohibited_uses` lists `context_state_rule_revision` and
`text_cleaning_rule_revision`. That prohibition binds **CheXpert Plus**, the external site.
Setting the informativeness rule on MIMIC is therefore permitted, and MIMIC is the only site
where it *may* be set. Deriving it from CheXpert Plus would violate the locked-external rule.

## 3. Proposed `permitted_sections_source`

| Proposed value | MIMIC section | External analogue | Coverage (source) |
|---|---|---|---|
| `indication` | `INDICATION`, `CLINICAL INDICATION`, `REASON FOR EXAMINATION`, `REASON FOR EXAM` | `section_clinical_history` | 72.80% |
| `history` | `HISTORY`, `CLINICAL HISTORY`, `PATIENT HISTORY`, `CLINICAL INFORMATION` | `section_history` | 25.03% |

Union coverage: **222,739 of 227,835 studies (97.76%)**; 5,096 studies (2.24%) have neither.

Three independent lines of evidence support the two-section set:

1. It is the structural analogue of `permitted_sections_external`
   (`section_clinical_history`, `section_history`) — same cardinality, same clinical role.
   Cross-site comparability requires matching section semantics, not matching header strings.
2. `context_interventions.yaml` N3 reads *"**Neither** permitted section contains usable
   text"* — wording that presumes exactly two permitted sections.
3. Measured cost of widening is negligible and the risk is not:

   | Candidate set | Studies with context | Gain vs two-section |
   |---|---:|---:|
   | `indication` + `history` | 222,739 (97.76%) | — |
   | + `examination` | 222,977 (97.87%) | +0.11 pp |
   | + `comparison` | 226,120 (99.25%) | +1.49 pp |
   | all pre-diagnostic | 226,711 (99.51%) | +1.75 pp |

   `examination` buys 0.11 pp. `comparison` buys 1.49 pp while admitting text that can quote
   prior diagnostic conclusions — a `prediction_time_requirement: pre_diagnostic_only`
   violation risk for a rounding error of coverage. **Recommend excluding both.**

## 4. Proposed informativeness rule (N1 / N2 / N3)

### 4.1 Effective token definition

> An **effective token** is a whitespace-delimited token containing at least one alphanumeric
> character, counted after de-identification placeholder runs (`_{2,}`) are removed.

This prevents a body of `___` or `//` from scoring as present context. Stage 3B measured 6
studies whose entire indication body is placeholders.

### 4.2 State assignment

Let `t` = effective tokens summed across the permitted sections.

| State | Rule |
|---|---|
| **N3** absent | `t == 0` |
| **N2** low_information | `0 < t < T` |
| **N1** informative | `t >= T` |

### 4.3 Proposed threshold `T`

Measured cohort at each candidate (source site, two-section set):

| `T` | N1 | N1 % | N1 + impression label |
|---:|---:|---:|---:|
| 1 | 222,739 | 97.76% | 187,847 |
| **3** | **212,022** | **93.06%** | **180,087** |
| 5 | 192,479 | 84.48% | 166,087 |
| 10 | 115,258 | 50.59% | 101,217 |
| 20 | 36,027 | 15.81% | 26,161 |

**Recommendation: `T = 3` primary, with `T = 5` and `T = 10` as pre-specified sensitivity
analyses.**

Rationale:

- The registry's N2 wording is *"boilerplate, vague, or clinically insufficient."* A token
  count detects emptiness and brevity — it does **not** detect vagueness. Choosing a high `T`
  overstates what the measure can support, and silently discards genuinely informative short
  indications (median indication length is 8 effective tokens).
- `T = 3` excludes degenerate bodies (`None.`, `___`, single-word fragments) while retaining
  93% of studies. The confirmatory cohort stays large enough that selective-prediction
  coverage strata at 80/90/70% remain populated.
- The primary-plus-two-sensitivity structure mirrors the protocol's existing treatment of
  coverage (80% primary; 90% and 70% sensitivity). Pre-specifying all three converts the most
  dangerous residual degree of freedom into a reported robustness curve.

**This threshold must be fixed before any label is generated or any model is run.** The
confirmatory cohort spans 187,847 to 8,996 studies across the swept range; chosen after
effect sizes exist, it is a garden of forking paths and the first thing a reviewer will
attack. `governance.post_target_inspection_changes_label: post_hoc_exploratory` already
encodes this consequence.

### 4.4 Cross-site application

The rule above is defined on the source site and applied **unchanged** to CheXpert Plus.
Re-fitting `T` on the external site is prohibited by
`external_dataset_prohibited_uses.context_state_rule_revision`. Any site difference in N1
share is a **result**, not a parameter to equalise.

## 5. Proposed exclusion rules

Stage 3B surfaced four structural populations that need explicit handling. Silence here
becomes an implementation default, which is exactly what preregistration is meant to prevent.

| Population | Studies | Proposed rule |
|---|---:|---|
| `WET READ` present | 17,551 (7.70%) | **Never** admit into `context_text`. Preliminary interpretation is post-diagnostic. Study remains eligible; the section is dropped. |
| `PROVISIONAL FINDINGS IMPRESSION` | 199 | Same as `WET READ`. |
| Findings and impression merged in one section | 134 (0.06%) | **Exclude the study.** The frozen primary/sensitivity label separation is not recoverable. |
| No recognised section header | 66 (0.03%) | **Exclude the study.** Cannot be split into pre-diagnostic and diagnostic parts. |
| Pre-diagnostic section after first label section | 181 (0.08%) | **Retain.** Extraction is header-driven, not position-driven, so ordering is immaterial. Recorded because a position-based extractor would silently corrupt these. |

Total hard exclusions: **200 studies (0.09%)**.

## 6. Deliberately not decided here

- **Label generation.** Already fixed by `docs/LABEL_HARMONIZATION_PLAN.md` (approved
  2026-07-18): CheXbert on the MIMIC impression scope (primary) and findings scope
  (sensitivity). MIMIC's shipped rule-based labels remain
  `official_mimic_labels_role: auxiliary_concordance_audit_only`. No change proposed.
- **View filtering.** `eligible_view: frontal` is frozen and unambiguous. It is unenforceable
  only because `mimic-cxr-2.0.0-metadata.csv.gz` is not yet downloaded — an access gap, not a
  decision gap.
- **Splits.** `official_splits_required: true` is frozen. Blocked on the same download.
- **Context length bins for C2.** Stage 3B-2 verified that all six provisional bins admit
  different-patient pairing at corpus level (largest single patient holds ≤0.39% of any bin).
  Bin edges should be fixed alongside `T`, and re-verified within split once splits exist.

## 7. Acceptance criteria

This proposal is complete when, and only when:

1. `permitted_sections_source` is set to `[indication, history]` with the header synonym map
   from §3 recorded in the protocol config.
2. The effective-token definition and `T` (primary and both sensitivity values) are recorded.
3. The §5 exclusion rules are recorded.
4. `protocol_version` is incremented and `MANIFEST.sha256` regenerated.
5. `validate_protocol.py` passes and a new validation report is written.

Steps 1–5 modify frozen protocol artifacts and are **not** authorised by the current
`AGENTS.md`. They require explicit sign-off before execution.

## 8. Open risks carried forward

- Effective token count is a proxy for informativeness. It measures emptiness and brevity,
  not vagueness or clinical insufficiency. The gap between the measure and the registry's
  wording should be stated as a limitation in the paper.
- All cohort figures are upper bounds until the frontal-view filter can be applied.
- C2 pairing feasibility is verified at corpus level only; the frozen constraint also
  requires pairing within split.
