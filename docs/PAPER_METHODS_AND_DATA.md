# C3E — Paper Draft: Methods and Data

Status: **DRAFT, frozen inputs only.** Every number here comes from a hash-verified audit
artifact produced before any label, model, or metric existed. No results section is drafted,
and no expectation about outcomes is stated anywhere in this file.

Evidence: `results/c3e_mimic/stage3a`, `stage3b`, `stage3b2`, `stage3c`, `stage3e`,
`results/c3e_power/`, and `protocols/C3E6_stage2/` at `protocol_version: 0.3.0`.

---

## 1. Study design

We evaluate whether a *selective prediction policy* calibrated at one hospital remains
reliable at another when pre-diagnostic clinical context changes in availability or
alignment. The design is a retrospective pre-deployment evaluation. It is not a prospective
clinical study, a deployment study, or a regulatory validation, and it does not claim a new
architecture or a new uncertainty algorithm.

The contribution is the evaluation protocol itself: a *compound shift* design that varies
institution and context simultaneously, so that the interaction between the two can be
estimated rather than assumed away.

Two shifts are crossed:

- **Institutional shift** — source site versus external site.
- **Context shift** — three controlled interventions on pre-diagnostic text (below).

The full protocol was frozen in a machine-readable registry before any data was labelled,
and is validated by an automated checker (30 checks, all passing at v0.3.0).

## 2. Sites and roles

| Role | Dataset | Function | Tuning |
|---|---|---|---|
| Source | MIMIC-CXR-JPG v2.1.0 | development and internal evaluation | permitted |
| External | CheXpert Plus | locked external evaluation only | prohibited |

The external site is locked: architecture selection, early stopping, temperature selection,
threshold selection, text-cleaning rules, and context-state rules may not be revised using it.
These prohibitions are encoded in the registry and enforced by the protocol validator.

## 3. Data intake and integrity

MIMIC metadata and the report archive were verified against the official SHA-256 manifest
before use (4/4 files matching). The report archive was checked entry-by-entry: 227,835
members, zero CRC mismatches, zero read errors, zero undecodable members.

Three independent sources agree exactly on the study inventory — the study list, the report
archive members, and the checksum manifest — and the record list agrees exactly with the
manifest's DICOM entries (377,110 records; 604,945 manifest rows total).

The image metadata and official split files were cross-validated against the checksum-verified
record list: identifier sets match exactly and every row's patient and study identifiers agree.

**Patient disjointness across the official splits holds exactly** (0 patients and 0 studies
span splits).

## 4. Report structure and the permitted text policy

The protocol requires model input to be *pre-diagnostic*: text available before the
interpretation exists. Findings, impression, and full reports are prohibited as inputs and
may act only as label sources.

We parsed all 227,835 reports structurally, using a curated section-header vocabulary and
header-driven (not position-driven) extraction. Section availability:

| Section | Class | Coverage |
|---|---|---:|
| indication | pre-diagnostic | 72.80% |
| history | pre-diagnostic | 25.03% |
| comparison | pre-diagnostic | 71.92% |
| examination | pre-diagnostic | 44.97% |
| technique | pre-diagnostic | 35.71% |
| impression | label source | 83.15% |
| findings | label source | 65.72% |
| **wet read** | **post-diagnostic** | **7.70%** |

**Permitted context is `indication` + `history`**, the structural analogue of the external
site's two permitted sections. Widening the set was measured and rejected: adding
`examination` gains 0.11 percentage points of coverage, and adding `comparison` gains 1.49
points while admitting text that can quote prior diagnostic conclusions.

Three structural hazards were identified and are handled explicitly:

1. **Preliminary interpretations embedded in reports.** 17,551 reports (7.70%) contain a
   `WET READ` section — a preliminary radiologist reading. This is post-diagnostic text
   sitting inside the report body. Any extraction rule that takes "everything before
   FINDINGS" as context silently ingests it. We exclude these sections while retaining the
   study.
2. **Non-monotone section order.** 181 reports place a pre-diagnostic section *after* the
   first diagnostic section, so position-based splitting mis-assigns their text. Extraction
   is therefore header-driven.
3. **Non-separable label sections.** 134 reports merge findings and impression into one
   section, and 66 expose no recognised header. Both are excluded (200 studies, 0.09%).

## 5. Context states and interventions

Natural states are assigned by an *informativeness rule* defined on the source site. An
**effective token** is a whitespace-delimited token containing at least one alphanumeric
character, counted after de-identification placeholder runs are removed — so a body of
placeholders or punctuation does not count as context.

| State | Rule |
|---|---|
| N1 informative | effective tokens ≥ T |
| N2 low information | 0 < effective tokens < T |
| N3 absent | effective tokens = 0 |

**T = 3 primary; T = 5 and T = 10 as pre-specified sensitivity analyses.** The rule is fixed
on the source site and transferred to the external site without refitting, mirroring the
frozen threshold-transfer design.

Choosing T is consequential and was therefore pre-specified. Across the swept range the
confirmatory cohort spans 187,847 studies (T = 1) to 8,996 (T = 30) — a twentyfold range
driven by a parameter that no prior specification fixed. We report the full sensitivity curve.

Three controlled interventions are applied to N1 studies only:

- **C0 original context** — identity.
- **C1 no context** — all permitted context replaced by `[NO_CONTEXT]`.
- **C2 misaligned context** — deterministic permutation under constraints: same institution,
  same split, different patient, same context-length bin, seed 20260718.

C2 feasibility was verified in advance: every context-length bin contains thousands of
distinct patients and no single patient holds more than 0.39% of any bin, so the
different-patient constraint is satisfiable throughout.

## 6. Cohort construction

| Step | Removed | Remaining |
|---|---:|---:|
| All studies | — | 227,835 |
| No recognised section | 66 | 227,769 |
| Merged label sections | 133 | 227,636 |
| Frontal view required | 9,688 | 217,948 |
| Official split assigned | 0 | 217,948 |
| Context informative (T = 3) | 15,001 | 202,947 |
| Impression label source present | 29,375 | **173,572** |

Final cohort: **173,572 studies, 58,689 patients, 193,282 frontal images.**

Eligible views are frontal (PA, AP). 15,769 images carry no view label and are treated as
non-frontal — the conservative reading, since assuming them frontal would admit views the
protocol excludes.

## 7. Evaluation partition

The official MIMIC test split yields only 282 patients within this cohort. A design-stage
power analysis (§9) showed this is materially underpowered for the primary hypothesis, so a
**prespecified patient-disjoint evaluation partition** was carved from the training split.

| Tier | Role | Patients | Studies |
|---|---|---:|---:|
| model train | model fitting | 49,959 | 146,253 |
| threshold calibration | frozen threshold selection | 3,000 | 9,233 |
| **prespecified eval** | **primary confirmatory evaluation** | **5,000** | **14,766** |
| official validate | secondary confirmation | 448 | 1,391 |
| official test | secondary confirmation | 282 | 1,929 |

Assignment used patient identifiers and the frozen seed only — no label, outcome, image, or
model output participated — so this is a design construction, not a data-dependent selection.
All tiers are verified patient-disjoint. The official splits are retained and reported as
secondary confirmation; primary estimates are consequently not directly comparable to
published official-split baselines, which we state as a limitation.

## 8. Models and selective policy

Four core models: image-only (M1, non-multimodal control), text-only (M2, text-signal and
shortcut control), probability late fusion (M3), and feature-concatenation fusion (M4).
Architecture selection must precede any inspection of external results.

Targets are five pathologies — Cardiomegaly, Edema, Pleural Effusion, Atelectasis,
Consolidation — with labels generated by a single labeller family applied identically at both
sites, to avoid confounding a site effect with a labeller artefact.

Selective policy: per-pathology confidence `|2p − 1|`; study confidence is the minimum across
pathologies; loss is five-label Hamming error; abstention means referral for human
interpretation. Thresholds are selected on the source calibration tier at 80% coverage
(primary; 90% and 70% sensitivity) and **transferred frozen** to the external site.

## 9. Statistical analysis

Inference is by patient-level bootstrap (2,000 replicates, seed 20260718, 95% percentile
intervals). Controlled context comparisons are paired within site; cross-institution
comparisons use independent within-site patient bootstraps. Per-pathology secondary analyses
use Holm correction; the primary estimand is the aggregate Hamming loss and does not pay a
multiplicity penalty.

A hypothesis is declared confirmed when its interval excludes zero **and** the point estimate
reaches the materiality threshold of 0.02 absolute.

**A note on that rule.** Because it requires the point estimate itself to reach materiality,
evaluating it at a true effect exactly equal to materiality yields rejection in only half of
repetitions — power is capped at 50% regardless of sample size. We verified this holds at an
implied n of order 10⁹. Materiality is therefore the smallest effect worth acting on, not the
design effect; the study is powered against the minimum detectable effect instead.

Design-stage power was computed over a declared grid of base risks, effect sizes,
intra-patient correlations, and coverages — swept, never fitted, since no outcome existed. On
the prespecified partition the minimum detectable effect at 80% power is 0.022–0.026 absolute
(1.1×–1.3× materiality), against 0.026–0.072 (1.3×–3.6×) on the official test split. The
normal approximation used for the grid agreed with the frozen bootstrap procedure to within
0.015 across validation cells.

Any hypothesis whose minimum detectable effect exceeds the achievable range is reported as
estimation with an interval rather than as a powered decision.

## 10. Preregistration and change control

The protocol is versioned, hash-manifested, and machine-validated. Every amendment is recorded
with its rationale and its confirmatory status. At the time of writing, all amendments are
recorded as **prespecified**: no label, model output, metric, or external result existed at
any site when they were made. Changes made after external-result inspection are automatically
labelled post-hoc exploratory by protocol rule.

## 11. Limitations

- Effective token count measures emptiness and brevity, not the vagueness the context registry
  names. A genuinely vague but lengthy indication scores as informative.
- The primary evaluation partition is not an official split, so primary estimates are not
  directly comparable to published official-split baselines.
- A reduced training budget (if adopted for image-download tractability) yields weaker models.
  The study measures whether selective reliability transports, not peak accuracy, but absolute
  performance will be below what full-data training would achieve.
- Studies whose only images lack a view label are excluded, which may not be missing at random.
- Section boundaries derive from a curated header vocabulary; reports outside that vocabulary
  are excluded rather than parsed heuristically.

---

## Drafting notes (remove before submission)

- Results, Discussion, and Conclusion are deliberately not drafted. Drafted expectations have
  a way of surviving into final text after the data disagrees.
- §4's three hazards are, in our view, the most transferable contribution to readers who use
  MIMIC reports as "pre-diagnostic context" — the `WET READ` finding in particular applies to
  any such pipeline, not only this one.
- §9's 50% ceiling generalises to any study using a "CI excludes zero AND estimate ≥ δ"
  decision rule. Worth stating as a standalone methodological point.
