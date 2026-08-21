# Venue Selection Plan

Target venue for the C3E manuscript, the evidence behind the choice, and the
work that submission requires.

- **Prepared:** 2026-08-13
- **Revised:** 2026-08-21 — cost constraint lifted by the author; target changed
  from JAMIA to npj Digital Medicine. See §1.
- **Manuscript:** `paper/main.tex` — full-length, venue-neutral, never compressed
- **Submission builds:** `paper/npjdm/` (primary) · `paper/jamia/` (fallback)
- **Status:** target npj Digital Medicine, JAMIA as fallback; neither build yet
  compressed to its limits.

---

## 1. Decision

**Revised 2026-08-21. Target npj Digital Medicine. JAMIA is the fallback.**

1. **npj Digital Medicine** — IF 12.4–18, ~$4,290 APC, 5,000 words + separate
   Methods, 10 display items
2. **JAMIA** — Q1, IF 7.1, free, 4,000 words, 4 tables + 6 figures — fallback
3. **Journal of Imaging Informatics in Medicine** — IF 3.1, free non-OA

The author lifted the cost constraint on 2026-08-21, which reopened the venue
this plan had already identified as the closest scope match and had ruled out
on the APC alone. Three findings made the change straightforward rather than a
gamble; they are set out in §2a.

**Consequence to accept:** ~$4,290 on acceptance, unless a case-by-case waiver
is granted. Nothing is owed on rejection.

### Superseded: the 2026-08-13 decision

Retained because the reasoning still governs the fallback.

> **Target JAMIA. No reach attempt.** Decided by the author on 2026-08-13,
> choosing probability of publication over a higher-IF attempt. The paper is an
> informatics paper on the merits, so this is the venue it belongs in, not
> merely the one it is likeliest to reach.

That decision was correct under a hard $0 constraint, and JAMIA remains the
right fallback for the same reasons. It was wrong only in one premise it could
not avoid at the time: it treated the APC as a cost incurred by *attempting* a
paid venue. It is not. APCs are charged on acceptance only, so a failed attempt
at a paid journal costs calendar time and nothing else.

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
| **npj Digital Medicine** — target | **IF 12.4–18**, CiteScore 23.6 | 5,000 w + separate Methods | **~$4,290** on acceptance | Gold OA |
| **JAMIA** — fallback | Q1, **IF 7.1**, CiteScore 9.6, h-index 184 | 4,000 w | **$0** | Subscription; OA optional |
| Radiology: AI | **IF 20.1**, Q1, #1 of 217 radiology journals | 3,000 w | **$0** non-OA | Hybrid — reach declined, see §1 |
| J. Imaging Informatics in Medicine | IF 3.1 / CiteScore 7.3 | — | **$0** non-OA | Hybrid |
| NEJM AI | **No JCR impact factor yet**; PubMed-indexed | 3,000 w | **$0** | Subscription; AAM deposit at acceptance — dropped from sequence, see §1 |
| Lancet Digital Health | **IF 15.30**, #1 of 54 medical informatics | 3,000 w | **$7,860** | Gold OA — reach above the target, see §2a |
| IEEE J. Biomedical & Health Informatics | IF 7.7–8.18 | 8 pp before charges | **$850–1,900** page charges | Hybrid — **ruled out**, see §2a |
| Nature Medicine | — | — | $0 hybrid | **Ruled out on scope** — requires prospective validation |
| Nature Machine Intelligence | — | — | $0 hybrid | **Ruled out on scope** — requires an ML advance |

Word limits count introduction through discussion/conclusion and exclude
abstract, references, figure legends and table notes.

## 2a. Evidence added 2026-08-21

Three findings drove the change of target. Verified against publisher pages and
the published literature on 2026-08-21.

### An APC is a cost of acceptance, not of attempting

This is the premise the 2026-08-13 decision got wrong, and correcting it changes
the whole shape of the problem. No journal on this list charges for submission.
A rejected paper at npj Digital Medicine or Lancet Digital Health costs exactly
what a rejected paper at JAMIA costs: the calendar time.

That removes the reason to submit low first. It also makes npj Digital
Medicine's editorial speed decisive: its **median time to first decision is
about 5 days**, so a desk rejection costs roughly a week. Median submission to
acceptance is 126 days (IQR 80–183).

### npj Digital Medicine has published this exact study shape, four times

Scope statements are weak evidence; publication history is strong. npj Digital
Medicine has published:

- *Distribution shift detection for the postmarket surveillance of medical AI
  algorithms: **a retrospective simulation study*** (2024). Note the subtitle.
  §2 records that Nature Medicine "has publicly criticised the exact study shape
  here — retrospective, simulation-based, narrow in scope". npj Digital Medicine
  publishes that shape as a matter of course.
- *Evaluating deep learning sepsis prediction models in ICUs under distribution
  shift: a multi-centre retrospective cohort study* (2026) — compares
  generalization against retraining, fine-tuning and domain adaptation across
  MIMIC-IV, eICU and HiRID. Structurally the same question as H1.
- *Generalization — a key challenge for responsible AI in patient-facing
  clinical applications* (2024) — selective prediction and model-centric sample
  deferral for models that do not generalize.
- *Recalibration of deep learning models for abnormality detection in chest
  radiograph* (2021) — **MIMIC-CXR to CheXpert transfer, performance loss
  repaired by recalibration.**

The last is the strongest argument for the venue and for the cover letter. This
paper's central claim is that re-calibrating at the receiving site *conceals* a
transport failure rather than repairing it. That complicates a result this
journal published, in its own pages, on the same two datasets.

### The format is materially more generous than JAMIA's

From the official npj submission guide, Article type. The decisive line is that
**Methods is counted separately from the main text**:

| | npj Digital Medicine | JAMIA |
|---|---|---|
| Main text | 5,000 w | 4,000 w |
| Methods | separate, ≤3,000 typical, may exceed | inside the 4,000 |
| Abstract | ~150 w, unstructured | 250 w, structured |
| Display items | 10 combined | 4 tables + 6 figures |
| References | ~70 | unlimited |

Against the current draft that is a **1,329-word cut for npj against 4,720 for
JAMIA**, with 1,133 words of *headroom* left in Methods — so methodological
detail cut from the main text can move into Methods rather than out to the
supplement. The display-item limit is the one place npj is stricter in effect:
10 combined means converting tables into figures does not help, and six items
must actually leave.

npj also constrains the title to 15 words with no punctuation and no active
verbs, which rules out the question form used by the other two builds. See
`paper/npjdm/README.md`.

### IEEE JBHI: checked and ruled out

The only free-route venue with a higher impact factor than JAMIA (7.7–8.18
against 7.1), squarely in health informatics scope, and missed by the original
survey. It is not actually free. IEEE levies **mandatory, explicitly
non-negotiable** overlength charges above 8 pages: $250/page for pages 9–10 and
$350/page from page 11. This paper cannot fit 8 IEEE two-column pages, so a
realistic 11–12 pages costs $850–1,900 — a worse deal than npj Digital Medicine
for a much lower impact factor.

### Lancet Digital Health: the reach above the target

IF 15.30 and **first of 54 journals in medical informatics** — this paper's
actual field, unlike Radiology: AI's radiology ranking. It accepts retrospective
external-validation studies and requires **TRIPOD+AI**, which
`paper/supplement/tripod_ai_checklist.md` already satisfies.

Not chosen as the first submission: 3,000 words is *tighter* than JAMIA, so it
would demand harsher compression than either existing build, for a markedly more
selective journal. Hold it as an optional reach if npj Digital Medicine
declines, before falling back to JAMIA.

### Risk accepted in moving up-market

The fairness gap becomes more likely to be a review demand than it is at JAMIA.
npj Digital Medicine publishes heavily on equity in clinical AI, and this study
reports no sociodemographic subgroup analysis — a gap now named explicitly in
`paper/sections/06_limitations.tex`. The paper's own argument invites the
question: a policy that transports poorly between hospitals has no reason to
defer uniformly across patient groups within one.

The preregistration rationale for the omission is sound and should not be
abandoned. But decide in advance which answer to give — principled exclusion
with the protocol rule stated, or a clearly labelled post-hoc exploratory
addition — rather than deciding it under revision pressure.

---

### Superseded: why npj Digital Medicine was out

**Reversed 2026-08-21** when the author lifted the cost constraint. Retained
because the waiver analysis below is still accurate and still applies.

It is the closest scope match on the list and was the presumed target, but the
APC was unaffordable and no *country-based* waiver applies. Springer Nature's waiver list is
World-Bank-based, not Research4Life-based:

- Full waiver: 24 low-income economies. **Bangladesh is not on it.**
- 50% discount: lower-middle-income economies with 2022 GDP below US$200bn.
  **Bangladesh is not on it** — lower-middle-income, but GDP far above the
  ceiling.

Cost would be the full $4,290. Waiver requests must be made at submission and
cannot be considered later, so there is no route to appeal after acceptance.

**Correction, 2026-08-21.** The last sentence of that paragraph was too strong.
Springer Nature also grants waivers and discounts **case-by-case on demonstrated
financial need**, independently of the country list. That route was missed here.
It is still true that it must be requested at submission and cannot be
considered afterwards, so it costs nothing to ask and everything to forget.
Some 2026 sources also list the APC as **$3,590** rather than $4,290; budget for
the higher figure and confirm at submission.

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

Rewritten 2026-08-21. The 2026-08-13 figures here were stale: Results and
Limitations both grew when the seed replicate and the fairness limitation landed.

Two submission builds now exist. `paper/main.tex` stays full-length and is never
compressed — it is the supplement's source text, so material cut from a venue
build has somewhere to go.

### 3.1 Compress — the two budgets

Current full-length body is **8,720 words** as the venue builds count it:

| Section | Words |
|---|---:|
| background / opening | 1,495 |
| objective *(npj: folded into opening)* | 261 |
| methods | 1,801 |
| results | 1,876 |
| discussion *(incl. limitations)* | 2,962 |
| conclusion *(npj: folded into discussion)* | 325 |

| | npj (primary) | JAMIA (fallback) |
|---|---:|---:|
| Main text budget | 5,000 | 4,000 |
| Methods | counted separately | inside the budget |
| Have | 6,329 main + 1,867 Methods | 8,720 |
| **Cut** | **1,329** | **4,720** |
| Methods headroom | **+1,133** | none |

npj is a third of the work, and its Methods headroom means methodological detail
can move *into* Methods instead of out to the supplement. Discussion (2,962) is
the source in both builds; Results (1,876) carries the confirmatory contrasts,
the S1 reversal and the label-commensurability finding and should be protected.

Run `./budget.sh` in either build directory for live numbers.

### 3.1a Display items

**13 tables and 3 figures — 16 display items.** Both venues allow 10, but the
shape of the limit differs and it changes the tactic:

| | npj | JAMIA |
|---|---|---|
| Limit | 10 **combined** | 4 tables **+** 6 figures |
| Tactic | six items must actually leave | convert tables to figures |

At JAMIA the figure budget is underused while the table budget is over three
times, so converting dense tables into figures is nearly free. At npj that buys
nothing — the limit is combined. The four H-contrast tables collapse into one
forest plot either way, a net saving of three.

Decide the display set before compressing prose, since it determines what the
compressed Results can say.

### 3.2 Foreground the S1 reversal — done

Both build abstracts now lead the label-source sensitivity as a result rather
than burying it as a caveat, with the bit-identical image-only predictions as the
evidence. The supporting numbers:

- The two label sets are non-commensurable across sites — 4.9× labelling
  density, 35pp difference in positive rate.
- M1 produced **bit-identical** external predictions across both runs (mean
  0.603719 in each) while its gap flipped sign. Only the labels changed.
- The protocol's harmonisation plan prespecified this check; it was not found
  after the fact.

### 3.3 Outstanding analysis — none

Both sensitivities are complete and written up.

Threshold sensitivity: all 14 contrasts hold their verdict at T=3, T=5 and T=10.

Seed replicate: landed, and reported in `sections/04_results.tex`
("Seed replicate"). All seven available contrasts return the primary's verdict,
H3 included, so the reversal against the hypothesis is not an artifact of one
initialisation. Point estimates are uniformly smaller under the replicate, which
the write-up states rather than smooths over. Reproduce with:

```bash
cd ~/Workspace/Personal/Research/Research/c3e/c3e_audit_toolkit
.venv/bin/python -m c3e.calibration.runner --seed 20260719 --num-workers 3
.venv/bin/python -m c3e.evaluation.runner  --seed 20260719 --num-workers 3
.venv/bin/python -m c3e.external.evaluate  --seed 20260719 --num-workers 3
.venv/bin/python -m c3e.analysis.runner    --seed 20260719
```

### 3.4 Abstracts — both written

Each venue needs a different one, and they are not interchangeable:

- **npj:** ~150 words, unstructured, unreferenced. Written, 148 words.
- **JAMIA:** ≤250 words, structured under Objective / Materials and Methods /
  Results / Discussion / Conclusion. Written, exactly 250 words.

### 3.5 Author-owned decisions

- Department, degrees, postal address, institutional email, ORCID iDs.
- Repository URL or DOI for the data and code availability statements.
- Author contributions and competing-interests statements.
- **Whether to request the Springer Nature financial-need APC waiver** at npj
  submission. It must be requested at submission and cannot be considered
  afterwards. Costs nothing to ask.
- Whether to attempt Lancet Digital Health before falling back to JAMIA.
- Whether to answer the fairness gap with a principled exclusion or a labelled
  post-hoc subgroup analysis (§2a).

---

## 4. Sources

Verified 2026-08-13 unless marked otherwise.

### Added 2026-08-21

- npj submission guide (Article limits) — https://www.nature.com/documents/npj-submission-guide.pdf
- npj Digital Medicine open access / APC — https://www.nature.com/npjdigitalmed/open-access
- npj Digital Medicine metrics, decision times — https://www.journalmetrics.org/journal/npj-digital-medicine
- npj DM, distribution shift postmarket surveillance (2024) — https://www.nature.com/articles/s41746-024-01085-w
- npj DM, sepsis models under distribution shift (2026) — https://www.nature.com/articles/s41746-026-02364-4
- npj DM, generalization and selective prediction (2024) — https://www.nature.com/articles/s41746-024-01127-3
- npj DM, recalibration for chest radiograph abnormality detection (2021) — https://www.nature.com/articles/s41746-021-00393-9
- JAMIA general instructions (4,000 w / 250 w structured / 4 tables / 6 figures) — https://academic.oup.com/jamia/pages/General_Instructions
- JAMIA, negative-results perspective (2026;33:926–929) — https://academic.oup.com/jamia/article-abstract/33/4/926/8429559
- JAMIA metrics (IF 7.1, CiteScore 9.6) — https://researcher.life/journal/journal-of-the-american-medical-informatics-association/5037
- IEEE JBHI submission guidelines — https://www.embs.org/jbhi/prepare-and-submit-your-manuscript/
- IEEE mandatory overlength charges — https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-voluntary-page-and-overlength-article-charges.pdf
- Lancet Digital Health, about and APC — https://www.thelancet.com/landig/about

### Verified 2026-08-13

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
