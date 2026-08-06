# C3E — Paper Draft: Introduction and Related Work

Status: **DRAFT, written before any external result was inspected.** Every claim
about prior work here traces to a row marked `verified` in `closest_work.csv`;
one candidate (CW08) remains unverified and is deliberately not cited. No
sentence in this file anticipates a result, and the Results and Discussion
sections are not drafted.

---

## 1. Introduction

A chest-radiograph classifier that knows when to defer is more useful in a
hospital than one that is merely accurate. Selective prediction formalises
this: the model returns a decision only when its confidence clears a threshold,
and refers the remainder to a human reader. The threshold fixes an operating
point — a coverage — and with it the workload the system imposes on radiology.

That operating point is chosen once, on data from the hospital where the system
was developed. It is then deployed somewhere else. Whether it survives the move
is an empirical question that is rarely asked, and the way it is usually asked
answers something narrower than intended: models are re-evaluated at a second
site, but the abstention threshold is re-fitted there too. A re-fitted threshold
tests whether a *method* transfers. It cannot test whether a *deployed policy*
transfers, because the policy that would actually be deployed is the frozen one.

There is a second shift that travels with the first, and it is usually left
implicit. Multimodal chest-radiograph models increasingly consume clinical
context alongside the image — the indication, the referring history, the reason
the study was ordered. This text is not a stable input. Its availability is a
property of how a particular hospital documents care, and it varies across
institutions in ways that have nothing to do with the patient. A model that
learned to lean on the indication field at one site may find it thin, absent, or
differently written at the next.

Institution and context therefore shift together. Studies that vary one hold the
other fixed: cross-institution work is typically image-only, and multimodal
context work is typically single-institution. Holding one fixed cannot reveal
whether they interact, and interaction is precisely what determines deployment
risk. If a multimodal model is more accurate at the source site *because* of
context, and context is scarcer at the target site, then the measured benefit
and the unmeasured fragility are the same phenomenon observed from two sides.

This paper contributes an evaluation protocol that crosses the two shifts
deliberately, so their interaction can be estimated rather than assumed away.
Concretely:

- **Two sites.** A source hospital, where models are developed and the selective
  policy is calibrated, and an external hospital used only for evaluation.
- **Three controlled context states at each site.** Context left intact,
  context removed, and context replaced with another patient's — the last
  separating *absence* of information from *wrong* information.
- **A frozen policy.** Per-pathology thresholds and abstention cutoffs are
  selected once at the source site and transferred unchanged, so what is
  evaluated is the policy that would actually ship.
- **Preregistration in a machine-readable, hash-manifested protocol**, with
  every amendment dated and its confirmatory status recorded, so the boundary
  between prespecified and post-hoc is auditable rather than asserted.

The contribution is the protocol and what it measures. We do not propose a new
architecture or a new uncertainty algorithm; the backbones are deliberately the
conventional ones, held constant so that architecture cannot serve as a
competing explanation for any effect observed. Nor is this a prospective
clinical study or a regulatory validation.

Two further contributions emerged from building the protocol and are reported
because they generalise beyond it. First, a structural hazard in deriving
pre-diagnostic context from radiology reports: a substantial minority of reports
embed a preliminary interpretation inside the report body, so any pipeline that
takes "everything before the findings section" as context silently ingests
post-diagnostic text. Second, a property of the decision rule this literature
commonly uses — requiring both that a confidence interval exclude zero and that
the point estimate reach a materiality threshold — which caps statistical power
at 50% when the true effect equals that threshold, regardless of sample size.

## 2. Related work

### 2.1 Selective prediction under distribution shift

Selective classification has been extended to distribution shift outside
medicine. The closest methodological work generalises selective classification
so that a model rejects not only ambiguous in-distribution inputs but
label-shifted and covariate-shifted ones, using margin-based confidence scores
that require no access to training data, evaluated on ImageNet, ImageNet-C,
OpenImage-O, iWildCam, Amazon and CIFAR [CW01].

That line establishes the machinery this paper applies. It does not take it to a
clinical setting, does not involve a second hospital, and does not transfer a
threshold frozen at one site to another. The question of whether an abstention
policy remains at its intended operating point after institutional transfer is
not addressed there, and is the question we ask.

### 2.2 Clinical context as a model input

Clinical history improves chest-radiograph classification. The most directly
comparable work fuses view-specific image encoders with clinical history through
an attention-refinement mechanism on MIMIC-CXR-JPG, and reports 135,682 images
with clinical history alongside a further 59,846 without [CW02].

That paper is a premise for ours rather than a competitor, and the distinction
is worth stating precisely. It is single-institution, evaluated on held-out
splits of one source, with no abstention policy, no audit of whether the
diagnosis leaks into the history text, and no calibration transfer. Its 59,846
context-free images are an *observation* of naturally occurring missingness. We
*intervene* on context under a frozen informativeness rule, which is what allows
an effect to be attributed to the manipulation rather than to whatever else
distinguishes patients whose indication field happens to be empty.

Related multimodal work reports clinically grounded alignment on MIMIC-CXR and
CXR-LT [CW03], though whether it examines context ablation or cross-institution
transfer is not determinable from its abstract and we do not claim otherwise.

### 2.3 Missing modalities as an architectural problem

A body of work treats missing modalities as something to engineer around.
Transformer-based bi-modal fusion modules combined into a tri-modal framework,
trained with multivariate losses for robustness to missing modalities on a
14-label diagnosis task over MIMIC-IV and MIMIC-CXR, is representative [CW04];
so is a mixture-of-experts framework that selects experts according to which
modalities are present, for mortality, length-of-stay and readmission
prediction [CW05].

The orientation differs from ours in a way that matters. There, missingness is
an obstacle and robustness is the objective; the natural question is how to keep
performance up when a modality drops out. Here, missingness is the *estimand*.
We are not asking how to build a model that resists context loss, but how much
reliability a conventionally built model loses when context degrades, and
whether that loss is larger at a hospital the model has never seen. Both
approaches also evaluate within a single source, so neither can speak to
transfer.

### 2.4 Cross-institution generalisation in chest radiography

Cross-domain generalisation for chest-radiograph models is well studied.
Foundational work across multiple datasets argues that cross-domain failure is
driven by label shift rather than image shift, observing that models with strong
individual performance disagree substantially with one another [CW06]. More
recent multi-center benchmarking over 145,000 images from PadChest and NIH Chest
X-ray evaluates head-versus-tail performance, calibration and cross-center
generalisation gaps, and concludes that detecting rare findings under
multi-center shift remains challenging [CW07].

This line is image-only. It varies institution while holding input availability
fixed, which is the mirror image of §2.2, and it does not evaluate abstention.
That the most recent multi-center benchmark still names calibration and
cross-center generalisation as open problems supports treating the crossed
question as unresolved rather than assuming it has been answered piecemeal.

### 2.5 The gap

Each axis has been studied in isolation. Selective prediction under shift exists
outside medicine [CW01]; clinical context helps within a single hospital
[CW02, CW03]; missing modalities are handled architecturally within a single
source [CW04, CW05]; institutional shift is characterised for image-only models
[CW06, CW07].

What is absent is the crossing: an evaluation in which institution and
pre-diagnostic context availability vary together, under a selective policy
frozen at the source site and transferred without refitting, with the
interaction estimated rather than assumed. That is the design this paper
specifies and reports.

---

## Drafting notes (remove before submission)

- Every citation traces to a `verified` row in `closest_work.csv`. CW08 is
  `unverified` because medRxiv refused automated retrieval; it is not cited, and
  must be inspected manually before submission in case it bears on §2.4.
- §2.2 deliberately frames CW02 as a premise rather than a competitor. That is
  the honest reading and it is also the stronger position: the claim that
  context helps is one we rely on, not one we need to displace.
- CW03's row carries `unclear` in several fields because only its abstract was
  inspected. The text above says only what the abstract supports. If the full
  paper turns out to include a context ablation, §2.2 needs revising and the
  claim of novelty narrows accordingly.
- No sentence here states or implies an expected result. The Introduction lists
  what the protocol measures, never what it found.
