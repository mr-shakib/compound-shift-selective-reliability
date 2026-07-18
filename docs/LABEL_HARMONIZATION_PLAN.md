# Cross-Site Label Harmonization Plan (C3E)

Status: **approved research decision recorded 2026-07-18.** No labeler has been run yet
(MIMIC data access is still pending). This document fixes the label-source and
labeler-harmonization policy so that later CheXbert runs are reproducible and
cross-site-comparable.

## 1. Label-source decision (CheXpert Plus)

| Resource | Role | Rationale |
|---|---|---|
| `impression_fixed.json` | **Primary, full-cohort label endpoint** | Dense (impression present in 99.9% of rows), no input-target leakage; standard CheXpert Plus target. |
| `findings_fixed.json` | **Mandatory sensitivity endpoint** | Purest imaging-observation target; sparse (findings section present in ~27% of rows) so it cannot be the primary, but every primary result must be re-checked against it. |
| `report_fixed.json` | **Excluded** | Direct input-target leakage: the full-report scope contains 100% of the permitted model-input sections (`section_clinical_history`, `section_history`). See `CHEXPERT_JOIN_AUDIT.md` §4. |

Encoding (all resources): `1.0`=positive, `0.0`=negative, `-1.0`=uncertain, `null`=unmentioned.

## 2. Cross-site labeler harmonization (MIMIC ↔ CheXpert Plus)

The primary cross-hospital experiment compares CheXpert Plus against MIMIC-CXR. Label
distributions are **only comparable when produced by the same labeler on the same report
scope.** Mixing labeler families silently confounds any cross-site effect with a
labeler-artifact effect.

**Rules (binding for the primary experiment):**

1. Use **CheXbert impression** labels at **both** MIMIC and CheXpert Plus.
2. Use **CheXbert findings** labels at **both** MIMIC and CheXpert Plus.
3. **Do not** mix MIMIC CheXpert-labeler (rule-based) outputs with CheXpert Plus CheXbert
   outputs in the primary experiment.

Consequence for MIMIC: MIMIC-CXR ships with **CheXpert-labeler** (rule-based) outputs by
default. Those are **not** admissible for the primary comparison — CheXbert must be run on
the MIMIC free-text reports (impression scope and findings scope separately) to match the
CheXpert Plus CheXbert labels. Rule-based MIMIC labels may be retained only as a clearly
segregated secondary/robustness comparison, never merged into the primary tables.

## 3. Endpoint × site matrix (target state)

| Endpoint | CheXpert Plus source | MIMIC source (to generate) | Labeler |
|---|---|---|---|
| Impression (primary) | `impression_fixed.json` (CheXbert) | CheXbert on MIMIC impression section | CheXbert |
| Findings (sensitivity) | `findings_fixed.json` (CheXbert) | CheXbert on MIMIC findings section | CheXbert |
| Report (excluded) | — | — | — |

Five target pathologies (both endpoints, both sites): Cardiomegaly, Edema, Pleural Effusion,
Atelectasis, Consolidation. Encoding harmonized to 1/0/-1/null as above.

## 4. Execution gate

- **CheXbert is NOT run now** — MIMIC row-level access is pending. Running CheXbert on only
  one site would produce a non-comparable half-experiment.
- When MIMIC access lands: run CheXbert on MIMIC impression and findings scopes, verify the
  five-label encoding matches (1/0/-1/null), then compare distributions site-to-site.
- CheXpert Plus side needs no labeler run — `impression_fixed.json` / `findings_fixed.json`
  are already CheXbert outputs; they join one-to-one on `path_to_image`.

### CheXpert Plus side is config-ready (2026-07-18)

The two CheXpert Plus endpoints are wired and validated:
`configs/chexpert_plus_impression.yaml` (primary) and `configs/chexpert_plus_findings.yaml`
(sensitivity), consumed by `c3e-audit chexpert`. Cross-site harmonization is required **only
before the cross-site experiment**, not for the CheXpert-only audit — the CheXpert side can be
audited independently now. See `CHEXPERT_CONFIG_DECISION.md`.

## 5. Provenance to record per label table (when generated)

Labeler name + version, report scope (impression | findings), input section field, site,
encoding map, and generation date. No raw report text or identifiers in provenance records.
