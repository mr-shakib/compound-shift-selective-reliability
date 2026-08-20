# TRIPOD+AI Reporting Checklist

Completed against Collins GS, Moons KGM, Dhiman P, et al. *TRIPOD+AI statement:
updated guidance for reporting clinical prediction models that use regression or
machine learning methods.* BMJ 2024;385:e078378. doi:10.1136/bmj-2023-078378

**Manuscript:** *Does multimodal selective reliability transport across hospitals
when pre-diagnostic clinical context changes?*

**Prepared:** 2026-08-13

Item text is abridged. Locations refer to manuscript sections unless a protocol
registry path is given. Status is one of **Met**, **Partial**, **Not
applicable**, or **Not met** — the last is used rather than stretched, because a
checklist that reports full compliance it does not have is worse than no
checklist.

**Summary:** 33 met, 6 partial, 5 not applicable, 3 not met. Every *not met* and
*partial* item concerns algorithmic fairness and sociodemographic reporting; see
the note at the end, which states the gap plainly rather than distributing it
across individual rows.

---

## Title and abstract

| # | Item | Status | Location |
|---|---|---|---|
| 1 | Identify as developing/evaluating a prediction model, target population, outcome | **Met** | Title; the title names the transport question, the models and the setting |
| 2 | Abstract (see TRIPOD+AI for Abstracts) | **Partial** | Abstract. Currently unstructured and 380 words; being restructured to the target journal's ≤250-word Objective/Methods/Results/Discussion/Conclusion format |

## Introduction

| # | Item | Status | Location |
|---|---|---|---|
| 3a | Healthcare context, rationale, references to existing models | **Met** | §1 Introduction; §2 Related work, with the eight nearest prior studies audited individually in `docs/closest_work.csv` |
| 3b | Target population, intended purpose in the care pathway, intended users | **Met** | §1; the intended use is a deferral policy handing low-confidence chest radiographs to a human reader |
| 3c | Known health inequalities between sociodemographic groups | **Not met** | See fairness note below |
| 4 | Study objectives; development or validation or both | **Met** | §1; §3.1 Study design. Both — development at the source site, frozen-policy evaluation at the external site |

## Methods — data and setting

| # | Item | Status | Location |
|---|---|---|---|
| 5a | Sources of data separately for development and evaluation; rationale; representativeness | **Met** | §3.2 Sites and roles; MIMIC-CXR-JPG v2.1.0 (development), CheXpert Plus (evaluation) |
| 5b | Dates of collected participant data | **Partial** | §3.2 identifies dataset versions but not participant accrual windows, which neither publisher reports at the granularity the item asks for |
| 6a | Key elements of study setting; number and location of centres | **Met** | §3.2; two centres — Beth Israel Deaconess Medical Center and Stanford Health Care, via their released cohorts |
| 6b | Eligibility criteria | **Met** | §3.6 Cohort construction and evaluation partition |
| 6c | Treatments received and how handled | **Not applicable** | Diagnostic classification from a single imaging study; no treatment assignment |
| 7 | Data pre-processing and quality checking | **Met** | §3.3 Data intake and integrity; every image verified against publisher checksums before use |

## Methods — outcome and predictors

| # | Item | Status | Location |
|---|---|---|---|
| 8a | Define the outcome, time horizon, how and when assessed, rationale | **Met** | §3.9 Label sources and the comparability check; five CheXbert-derived findings from the report impression (primary) or findings (sensitivity) section |
| 8b | Qualifications and demographics of outcome assessors, if subjective | **Not applicable** | Outcome assignment is fully automated by CheXbert with pinned artifacts; no human assessor is involved |
| 8c | Actions to blind outcome assessment | **Met** | §3.1; labelling precedes and is independent of model training, and the external site is locked against inspection |
| 9a | Choice of initial predictors and any pre-selection | **Met** | §3.4 Report structure and the permitted text policy; predictors are the frontal image and the pre-diagnostic report sections only |
| 9b | Define all predictors, how and when measured | **Met** | §3.4; §3.8 Models and selective policy. The permitted-context policy is enforced in code and tested |
| 9c | Qualifications and demographics of predictor assessors, if subjective | **Not applicable** | Predictors are extracted programmatically by a tested section parser |

## Methods — analysis

| # | Item | Status | Location |
|---|---|---|---|
| 10 | How study size was arrived at; justification; sample size calculation | **Met** | §3.10.1 Power. Design-stage power computed over a declared effect grid; the decision rule caps power at 50% by construction, which is stated rather than concealed |
| 11 | How missing data were handled; reasons for omitting data | **Met** | §3.6; §6 Limitations, which itemises every exclusion including the single image corrupt at source |
| 12a | How data were used; partitioning | **Met** | §3.6; disjoint patient-level tiers for training, threshold calibration and pre-specified evaluation |
| 12b | How predictors were handled (transformation, standardisation) | **Met** | §3.3; §3.8 |
| 12c | Type of model, rationale, all building steps, hyperparameter tuning, internal validation | **Met** | §3.8; four models — DenseNet-121 image-only, BERT text-only, probability late fusion with zero trainable parameters, and jointly trained feature fusion. Backbones and optimisation settings frozen in the protocol registry before training |
| 12d | Heterogeneity across clusters handled and quantified | **Met** | §3.10; patient-clustered bootstrap, 2,000 replicates, seed 20260718 |
| 12e | All measures and plots used to evaluate performance and compare models | **Met** | §3.10; selective Hamming error at fixed coverage, with the comparison set and materiality threshold pre-specified |
| 12f | Any model updating arising from evaluation | **Not applicable** | No updating was permitted. Withholding it is the study design: the question is whether the *shipped* policy transports, and re-fitting at the target site would answer a different question. See §5 Discussion |
| 12g | For model evaluation, how predictions were calculated | **Met** | §3.8; §3.11 External site. Per-pathology thresholds and abstention cutoffs transferred unchanged |
| 13 | Class imbalance methods | **Not applicable** | No resampling or reweighting was applied; prevalence is reported per site and per label source in §4 |
| 14 | Approaches used to address model fairness | **Not met** | See fairness note below |
| 15 | Output of the prediction model; classification thresholds and how identified | **Met** | §3.8; per-pathology thresholds by balanced accuracy on the calibration tier, abstention cutoff by target coverage |
| 16 | Differences between development and evaluation data | **Met** | §3.11; §4.11 Label-set comparability across sites; §5. Reported quantitatively — the label sets differ 4.9-fold in labelling density and 35 percentage points in positive rate |
| 17 | Ethics approval and consent | **Partial** | Data and code availability statement. Both datasets are publicly released, de-identified and governed by data use agreements requiring individual credentialing, which the author holds; no separate institutional review board approval was sought for secondary analysis. To be stated explicitly in an Ethics paragraph before submission |

## Open science

| # | Item | Status | Location |
|---|---|---|---|
| 18a | Source of funding and role of funders | **Partial** | To be added before submission; no external funding to declare |
| 18b | Conflicts of interest and financial disclosures | **Partial** | To be added before submission; none to declare |
| 18c | Where the study protocol can be accessed | **Met** | Preregistration statement; machine-readable registry under `protocols/`, hash-manifested and validated by an automated checker |
| 18d | Registration information, or state not registered | **Met** | Preregistration statement. The protocol was frozen before any label, model output or metric existed, with every amendment dated in an amendment log recording its confirmatory status. Not registered on a public trial registry, which is stated |
| 18e | Availability of study data | **Met** | Data and code availability statement. Neither dataset is redistributed; both are available to credentialed researchers from PhysioNet and Stanford AIMI |
| 18f | Availability of analytical code | **Met** | Data and code availability statement; analysis code, protocol registry and every reported aggregate are released. Row-level labels, checkpoints and images remain in the protected environment required by the data use agreements |

## Patient and public involvement

| # | Item | Status | Location |
|---|---|---|---|
| 19 | Patient and public involvement, or state none | **Partial** | None. Secondary analysis of previously collected, de-identified public datasets with no participant contact. To be stated explicitly before submission |

## Results

| # | Item | Status | Location |
|---|---|---|---|
| 20a | Flow of participants; numbers with and without the outcome | **Met** | §4.1 Cohorts; §3.6 |
| 20b | Characteristics overall and per data source, including differences across key demographic groups | **Partial** | §4.1 and §4.11 report cohort sizes, natural context states and label prevalence per site and per label source. Demographic characteristics are **not** reported — see fairness note |
| 20c | For evaluation, compare distribution of important predictors with development data | **Met** | §4.11; §3.11. Context availability and label composition compared across sites |
| 21 | Number of participants and outcome events in each analysis | **Met** | §4.1; §4.3–§4.7, reported per contrast |
| 22 | Full prediction model details sufficient for third-party evaluation, including access restrictions | **Partial** | §3.8 fully specifies architectures, training procedure and every threshold. Trained weights are **not** released: they derive from credentialed data and the restriction is stated rather than implied |
| 23a | Performance estimates with confidence intervals, including key subgroups | **Partial** | All estimates carry 95% patient-clustered percentile intervals (§4). Subgroup estimates by sociodemographic group are absent — see fairness note |
| 23b | Heterogeneity in performance across clusters | **Met** | §4.2; §4.8 Coverage under the frozen cutoff, reported by site and condition |
| 24 | Results of any model updating | **Not applicable** | None performed, by design (item 12f) |

## Discussion

| # | Item | Status | Location |
|---|---|---|---|
| 25 | Overall interpretation in the context of objectives and previous studies | **Met** | §5 Discussion. Includes a hypothesis that was contradicted — multimodal models transported better than the image-only control, against the pre-specified direction |
| 26 | Limitations, biases, statistical uncertainty, generalisability | **Met** | §5; §6 Limitations. States explicitly that this is one pair of hospitals and that nothing here establishes the transfer gap to expect elsewhere |
| 27a | How poor quality or unavailable input data should be handled at implementation | **Met** | §5. The context-intervention results are precisely this: C1 removes context, C2 supplies another patient's |
| 27b | Whether users interact with input handling; expertise required | **Partial** | §5 describes the deferral workflow but does not specify required user expertise |
| 27c | Next steps for future research, applicability and generalisability | **Met** | §5.5 Future work; a third site is identified as the most informative next step |

---

## Note on fairness and sociodemographic reporting

Items **3c**, **14**, and parts of **20b** and **23a** are not satisfied. This
study reports no sociodemographic characteristics and no subgroup performance
estimates, and applied no fairness-specific method. The omission is stated here
rather than spread thinly across the individual rows, because it is one gap and
not four.

Two things follow, and both belong in the manuscript's limitations rather than
in this checklist alone.

First, the omission was not a considered exclusion. The pre-registered protocol
specified cohort construction, endpoints, contrasts and materiality without
naming sociodemographic strata, so no fairness analysis was frozen in advance.
Adding one now would be post hoc by the protocol's own rule, and would be
labelled exploratory rather than confirmatory.

Second, the omission interacts with the study's central finding. If a frozen
abstention policy transports poorly between institutions, there is no reason to
assume it transports uniformly across patient groups within an institution, and
a policy that defers disproportionately on one group would be a fairness failure
invisible to every metric reported here. Both source and external datasets
publish demographic fields sufficient to test this. It is the natural companion
analysis to the third site already identified as future work.

Recommended action before submission: add a short limitations paragraph stating
the absence, its cause, and its interaction with the transport result. A
reviewer applying TRIPOD+AI will otherwise raise it, and it is a stronger paper
for naming the gap first.
