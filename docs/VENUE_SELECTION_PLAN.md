# Venue Selection Plan

Target venue for the C3E manuscript, the evidence behind the choice, and the
work that submission requires.

- **Prepared:** 2026-08-13
- **Manuscript:** `paper/main.tex` — *Does multimodal selective reliability
  transport across hospitals when pre-diagnostic clinical context changes?*
- **Status:** venue fixed (JAMIA); manuscript not yet compressed to its limits.

---

## 1. Decision

**Target JAMIA. No reach attempt.**

1. **JAMIA** — Q1, h-index 184, free, 4,000 words, 10 display items
2. **Journal of Imaging Informatics in Medicine** — IF 3.1, free non-OA, fallback

Decided by the author on 2026-08-13, choosing probability of publication over a
higher-IF attempt. The paper is an informatics paper on the merits, so this is
the venue it belongs in, not merely the one it is likeliest to reach.

The reach attempt considered and declined was Radiology: AI (IF 20.1, free
non-OA). Under 30% acceptance after a major-revision invitation, before
accounting for desk rejection of a methodological paper in a clinical radiology
journal, and a failed attempt would have cost two to four months. Committing to
JAMIA directly also lightens the remaining work materially: 4,000 words rather
than 3,000, ten display items rather than five, no CLAIM checklist to produce,
and no double-anonymisation pass to strip self-identifying references to the
protocol registry.

Consequence to accept: the IF-20.1 outcome is off the table for this paper.

### Why NEJM AI is not in the sequence

The author's institution weights impact factor for assessment. That is also what
removed NEJM AI, independently of the decision above.

**NEJM AI has no impact factor** — too new to have entered Journal Citation
Reports. It is prestigious by association and PubMed-indexed, and its Original
Article scope names "rigorous evaluations of medical AI", which is exactly this
contribution type. On fit alone it would be the right first submission. On an
IF-based scorecard it counts as zero, so spending the first submission there
costs a high-IF attempt for a venue that was always the longest shot. Dropped
from the sequence; revisit only if the IF constraint goes away.

**JAMIA is the target.** The paper is an informatics paper
— a shipped artifact's operating point, silent degradation, why re-calibration
at the target site conceals it. Q1 in Health/Medical Informatics, h-index 184,
single authorship unremarkable, free to publish, and it allows 4,000 words and
10 display items against Radiology: AI's 3,000 words. Aggregators disagree on
its exact IF (5.01 in one JCR year, 7.1 in another); the Q1 ranking is the
stable fact.

---

## 2. Evidence

Checked 2026-08-13 against publisher pages, not from memory. Figures are the
2025 metrics released in the 2026 JCR/CiteScore cycle.

| Venue | Metric | Body limit | Cost to this author | Access model |
|---|---|---|---|---|
| **JAMIA** — target | Q1, IF 5–7 (source-dependent), h-index 184 | 4,000 w | **$0** | Subscription; OA optional |
| Radiology: AI | **IF 20.1**, Q1, #1 of 217 radiology journals | 3,000 w | **$0** non-OA | Hybrid — reach declined, see §1 |
| J. Imaging Informatics in Medicine | IF 3.1 / CiteScore 7.3 | — | **$0** non-OA | Hybrid |
| NEJM AI | **No JCR impact factor yet**; PubMed-indexed | 3,000 w | **$0** | Subscription; AAM deposit at acceptance — dropped from sequence, see §1 |
| npj Digital Medicine | CiteScore 23.6 | ~5,000 w | **$4,290** | Gold OA — **ruled out on cost** |
| Lancet Digital Health | — | — | **$7,860** | Gold OA — **ruled out on cost** |
| Nature Medicine | — | — | $0 hybrid | **Ruled out on scope** — requires prospective validation |
| Nature Machine Intelligence | — | — | $0 hybrid | **Ruled out on scope** — requires an ML advance |

Word limits count introduction through discussion/conclusion and exclude
abstract, references, figure legends and table notes.

### Why npj Digital Medicine is out

It is the closest scope match on the list and was the presumed target, but the
APC is unaffordable and no waiver applies. Springer Nature's waiver list is
World-Bank-based, not Research4Life-based:

- Full waiver: 24 low-income economies. **Bangladesh is not on it.**
- 50% discount: lower-middle-income economies with 2022 GDP below US$200bn.
  **Bangladesh is not on it** — lower-middle-income, but GDP far above the
  ceiling.

Cost would be the full $4,290. Waiver requests must be made at submission and
cannot be considered later, so there is no route to appeal after acceptance.

### Why not the Nature flagships

Asked and answered here so it does not resurface as an open question.

npj Digital Medicine *is* a Nature Portfolio journal, and it was the presumed
target. It is out on cost, above — not on fit.

Nature Medicine and Nature Machine Intelligence are both **hybrid**: the
subscription route costs nothing, and their $12,850 gold OA would simply not be
elected. Cost is not the barrier. Scope is:

- **Nature Medicine** requires prospective or clinical validation for AI work.
  Retrospective-only studies do not meet its evidentiary bar, and the journal
  has publicly criticised the exact study shape here — retrospective,
  simulation-based, narrow in scope. This is a stated exclusion, not a judgement
  about quality.
- **Nature Machine Intelligence** selects for a machine-learning advance. This
  study deliberately uses stock DenseNet-121 and BERT-base, because a novel
  architecture would confound the question of whether a *shipped* policy
  survives a site change. Correct for the question, fatal for NMI.

NEJM AI is therefore the better reach at the same price. Both cost $0, but NEJM
AI's scope explicitly names "rigorous evaluations of medical AI" — the exact
contribution type — whereas Nature Medicine wants advances.

Nature Communications (gold OA only, ~$6,800, still novelty-selecting) and
Scientific Reports (~$2,690, weaker standing in clinical informatics than JAMIA,
which is free) are both dominated by options already on the shortlist.

The ceiling is set by the design, and the design was right for the question.
Preregistration, a frozen policy and standard backbones are what make the
negative result credible, and they are the same properties that make the
novelty-selecting flagships the wrong room.

### Why Lancet Digital Health is out

Gold OA at $7,860 with waivers only discretionary and negotiated after
acceptance. Accepting on the hope of a waiver is an unbounded liability.

### Radiology: AI, for the record

Reach attempt declined (§1). If it is ever reconsidered:

- Free to submit; **free to publish** under the subscription route. Gold OA is
  $3,500 and optional.
- Original Research: **3,000 words**, introduction through discussion.
- Structured abstract, **≤250 words**: Purpose / Materials and Methods /
  Results / Conclusion.
- **CLAIM checklist (2024 update) required** — Checklist for Artificial
  Intelligence in Medical Imaging, doi:10.1148/ryai.240300.
- Double-anonymised peer review. At most two first authors.
- Table and figure limit **not verified** — pubs.rsna.org is behind Cloudflare
  and blocks automated retrieval. Read
  <https://pubs.rsna.org/page/ai/author-instructions> directly if needed.

### NEJM AI, for the record

Dropped on the IF constraint (§1), not on fit. If that constraint is ever
lifted, it is the best-matched venue on the list and should be reconsidered
first:

- **No author-pays model of any kind** — no submission fee, no publication fee,
  no APC. Not a waiver; the charge does not exist.
- Original Article scope explicitly includes *"rigorous evaluations of medical
  AI"*, alongside trials and new applications.
- Publishes qualified and negative external validations. Precedent: the external
  validation of Epic's hospital-acquired AKI model
  (doi:10.1056/AIoa2300099), which reported moderate performance and declined
  to endorse clinical use.
- Indexed in PubMed (ISSN 2836-9386).
- Original Article: 3,000 words, ≤5 tables and figures, ≤50 references, ≤50
  authors, structured abstract (Background / Methods / Results / Conclusions),
  plus a 1–2 sentence description.

### Why JAMIA is the realistic target

The paper is an informatics paper, not a radiology paper. Its subject is a
shipped artifact's operating point: silent degradation under site transfer, why
re-calibrating at the target site conceals the failure, and why coverage
monitoring alone would not detect it. That is JAMIA's Research and Applications
track. Its stated scope covers clinical care, imaging, implementation science
and translational work.

- Research and Applications: 4,000 words, structured abstract ≤250 words,
  ≤4 tables, ≤6 figures.
- Subscription journal — publishing costs nothing.
- If OA is later wanted, OUP's LMIC programme has granted full waivers in 91
  countries and up to 75% discounts in 38 more since August 2025; Bangladesh's
  eligibility is unconfirmed and should be checked at submission rather than
  assumed.

### Why Radiology: AI is third despite IF 20.1

Highest impact factor on the shortlist — 20.1 in the 2025 JCR, up from 13.2,
ranking first of 217 radiology journals — and free to publish non-OA ($3,500
only if gold OA is elected). But under double-anonymised review, radiologist
reviewers will ask what the clinical question is, and the contribution is
deployment methodology with chest radiographs as the substrate. The journal
also reports that manuscripts returned for major revision have below a 30%
chance of final acceptance.

### Conferences: rejected

MLHC 2026 closed 17 April 2026 and the conference ran 12–14 August 2026. CHIL's
next cycle opens around February 2027. Both publish through PMLR rather than as
indexed journal articles. Neither is faster nor better than a journal
submission now.

---

## 3. What submission requires

### 3.1 Compress to 4,000 words

Current body is **8,430 words**:

| Section | Words |
|---|---:|
| `01_introduction` | 613 |
| `02_related_work` | 890 |
| `03_methods` | 2,012 |
| `04_results` | 2,171 |
| `05_discussion` | 2,249 |
| `06_limitations` | 495 |
| **Total** | **8,430** |

JAMIA Research and Applications allows 4,000 words. Cut **4,430 words**, a
little over half the body. Methods detail and the sensitivity analyses move to
supplementary material; the protocol registry and amendment log carry the rest.

Discussion (2,249) and Methods (2,012) are the two largest sections and the
obvious sources. Results (2,171) should be protected — it carries the
confirmatory contrasts, the S1 reversal and the label-commensurability finding,
which are the paper.

### 3.1a Display items

The paper has **12 tables and 3 figures — 15 display items**. JAMIA allows
**4 tables and 6 figures**, so five must move to supplement, and the mix
matters: eight of the twelve tables have to go or become figures.

| Limit | JAMIA | Have | Action |
|---|---:|---:|---|
| Tables | 4 | 12 | cut or convert 8 |
| Figures | 6 | 3 | room for 3 more |
| Words | 4,000 | 8,430 | cut 4,430 |
| References | — | 10 | no constraint |

The figure budget is underused while the table budget is over by three times.
Converting dense tables to figures is therefore the cheapest route to
compliance, and it also reads better: forest plots and paired-bar charts carry
contrast-with-interval data more legibly than a table of six numbers.

Decide the display set before compressing prose, since that choice determines
what the compressed Results can say. The seed replicate adds at most one small
table; reserve for it.

### 3.2 Foreground the S1 reversal

Reviewers at any of these venues will go straight at the label-source
sensitivity, where H1 reverses from +0.047 to −0.132. The current abstract
states it in a way that reads as a weakness. It is a strength and should be
presented as one:

- The two label sets are non-commensurable across sites — 4.9× labelling
  density, 35pp difference in positive rate.
- M1 produced **bit-identical** external predictions across both runs (mean
  0.603719 in each) while its gap flipped sign. Only the labels changed.
- The protocol's harmonisation plan prespecified this check; it was not found
  after the fact.

### 3.3 Outstanding analysis

Threshold sensitivity is complete and written up
(`sections/04_results.tex`, "Informativeness-threshold sensitivity"). All 14
contrasts hold their verdict at T=3, T=5 and T=10.

The seed replicate is not yet run — no seed caches exist and there is no
`stage7_thresholds_seed20260719`. Stages 7, 8 and 9b each loaded all four
checkpoints unconditionally and died on the missing `m2_best_seed20260719.pt`;
fixed by routing every stage through `scored_models(seed)`, so a replicate
scores M1 and M4 only:

```bash
cd ~/Workspace/Personal/Research/Research/c3e/c3e_audit_toolkit
.venv/bin/python -m c3e.calibration.runner --seed 20260719 --num-workers 3
.venv/bin/python -m c3e.evaluation.runner  --seed 20260719 --num-workers 3
.venv/bin/python -m c3e.external.evaluate  --seed 20260719 --num-workers 3
.venv/bin/python -m c3e.analysis.runner    --seed 20260719
```

Once it lands, add the seed-replicate subsection to Results. Do not compress
before then: compression is a choice about what survives, and if the replicate
disagrees with the primary the claims change.

### 3.4 Structured abstract

JAMIA requires a structured abstract of **≤250 words**. The current abstract is
a single unstructured block of roughly 400 words and needs restructuring into
Objective / Materials and Methods / Results / Discussion / Conclusion.

### 3.5 Author-owned decisions

- Final author list and affiliation.
- Whether to elect gold OA (JAMIA publishes free under the subscription route;
  OA is optional and an OUP LMIC waiver may apply — check at submission, do not
  assume).

---

## 4. Sources

Verified 2026-08-13.

- NEJM AI article types and submission — https://ai.nejm.org/author-center/article-types-and-submission-information
- NEJM AI business model — https://ai.nejm.org/about/business-model
- NEJM AI, Epic AKI external validation — https://ai.nejm.org/doi/full/10.1056/AIoa2300099
- RSNA author instructions — https://pubs.rsna.org/page/ai/author-instructions
- RSNA open access policy — https://pubs.rsna.org/page/openaccess
- RSNA 2025 impact factors — https://www.rsna.org/news/2026/june/2025-journals-impact-factors
- JAMIA general instructions — https://academic.oup.com/jamia/pages/General_Instructions
- OUP LMIC waiver programme — https://corp.oup.com/feature/opening-the-doors-to-trusted-research-worldwide/
- OUP APC waiver policy — https://academic.oup.com/pages/open-research/open-access/charges-licences-and-self-archiving/apc-waiver-policy
- Springer Nature APC waiver countries — https://www.springernature.com/gp/open-science/policies/journal-policies/apc-waiver-countries
- npj Digital Medicine open access — https://www.nature.com/npjdigitalmed/open-access
- J. Imaging Informatics in Medicine, how to publish — https://link.springer.com/journal/10278/how-to-publish-with-us
- Lancet APC schedule — https://www.thelancet.com/landig/about
- MLHC call for papers — https://mlhc.org/paper-submission
- CHIL call for papers — https://chil.ahli.cc/submit/call-for-papers/
