# C3E Research Project Brief

**Role of this document:** Long-term research partner brief for Shakib Howlader's C3E project. Intended as Project knowledge for Claude — update it as the project state changes rather than relying on chat memory for live status.

---

## 1. Researcher Profile

- **Name:** Shakib Howlader, Bangladesh
- B.Sc. in Computer Science and Engineering — CGPA 3.92/4.00
- Currently pursuing/preparing for advanced study in Data Science
- One published dataset paper
- Prior research in computer vision and real-time sign-language recognition
- Experience: Machine learning, computer vision, NLP/RAG, Flutter/mobile deployment, Python, data analysis
- Hardware: Ryzen 5 5500, 16 GB RAM, GTX 1660 Super (6 GB VRAM)
- **Goal:** Q1-quality research → fully funded Master's or PhD scholarship → long-term AI/ML research career
- **Target destinations:** USA, Europe, Germany, Japan, Korea, Canada, Australia, UK

Operating model: Shakib is the human researcher; Claude serves as research-planning, literature, engineering, analysis, writing, and reviewer partner. Shakib retains responsibility for scientific accountability, implementation, data governance, authorship, and final decisions.

---

## 2. Locked Research Domain

**Domain (locked ≥12 months):** Reliable multimodal learning under incomplete, conflicting, noisy, and shifted evidence

- **Primary application:** Biomedical and health data
- **Career identity:** Trustworthy multimodal AI researcher
- **Methodological themes:** Missing modalities, low-quality modalities, contradictory evidence, distribution shift, external institutional validation, uncertainty estimation, calibration, selective prediction, safe abstention, data quality, reliability transfer, human escalation

**Rule:** Rejecting one candidate paper/task must NOT trigger a domain change. The RQ, task, dataset, or method may be modified while staying within the domain. Do not pivot to quantum ML, molecular AI, generic LLM apps, or multi-agent systems unless a formal feasibility gate fails.

### Why this domain
Strong intersection of: durable unresolved research problems, strong international funding, large supervisor pool, compatibility with Shakib's CV (NLP/CV/mobile/data science), public biomedical datasets, Q1 publication pathways, manageable first-paper compute, long-term PhD extensibility.

Rejected alternatives: quantum ML (hardware/theory barriers), molecular AI (needs chemistry/assay expertise), generic healthcare classification (too crowded), accessibility-only (narrow funding pool), multi-agent systems (moving too fast, previously abandoned).

---

## 3. Research Decision Protocol — Six Gates

Every candidate decision must be scored against all six gates before implementation begins:

| Gate | Requirement | Minimum |
|---|---|---|
| 1. Importance | Real scientific/clinical/deployment consequence | 8/10 |
| 2. Novelty | Closest-work matrix shows no paper combines mechanism + data setting + evaluation | 7.5/10 |
| 3. Data validity | Available data genuinely supports the scientific claim | 8/10 |
| 4. Methodological contribution | New method, new formal problem, new benchmark/protocol, or new finding existing eval can't reveal | 7.5/10 |
| 5. Feasibility | Achievable with compute, time, data access, expertise | 8/10 |
| 6. Publication pathway | Realistic venues + reviewer expectations + required experiments identified before full development | 7.5/10 |

No implementation begins just because an idea sounds interesting.

---

## 4. Candidate Development History

Initial broad formulation — *Robust multimodal biomedical learning under joint modality missingness and domain shift* — was **rejected**: recent literature already covers missing modalities + distribution bias, non-random missingness, missingness-as-shift, incomplete multimodal open-set domain generalization, uncertainty-aware fusion, modality-pattern mismatch.

So the contribution cannot simply be: another missing-modality model, domain-generalization model, uncertainty-aware fusion mechanism, modality-dropout architecture, or open-set detector.

---

## 5. Current Research Question

**Provisional RQ:** Does the selective reliability of a multimodal chest-X-ray classifier survive when pre-diagnostic clinical context becomes missing, incomplete, or differently distributed, and the model is transferred to another hospital?

**Operational version:** Can a multimodal clinical model still rank unsafe predictions correctly and know when to abstain after both hospital distribution and clinical-context availability change?

**Provisional title (not final):** *When Clinical Context Disappears: Selective Reliability of Multimodal Chest-X-Ray Models Across Hospitals*

**Exact contribution claim:** External transport of selective reliability under clinical-context availability and quality shift.

This is distinct from (all have close prior work): adding clinical history to CXR, showing text improves AUROC, showing text dominates images, entropy-based abstention alone, missing modalities alone, hospital shift alone, calibration alone.

**Intersection defining the candidate:** chest radiographs + pre-diagnostic clinical history + missing/low-quality history + cross-hospital transfer + selective prediction + error ranking + leakage-controlled clinical text + class-specific reliability.

Novelty is provisional and must keep being challenged.

---

## 6. Datasets

### Source: MIMIC-CXR / MIMIC-CXR-JPG
- Institution: Beth Israel Deaconess Medical Center
- Modalities planned: frontal chest X-ray + pre-diagnostic clinical history/indication
- Access: requested via PhysioNet, **pending**

### External target: CheXpert Plus
- Institution: Stanford Health Care
- Access: **granted** (AIMI membership complete, Stanford Research Agreement complete, data access 2/2 complete, data exports unrestricted)
- Dataset DOI: 10.57761/fzna-pm76

**Resources visible in CheXpert Plus:**
| Resource | Details |
|---|---|
| CheXpert Labels (file index) | 5 variables, 3 referenced files |
| df_chexpert_plus_240401 | 27 variables, 223,462 rows |
| DICOM_compressed (file index) | 18 files |
| DICOM_train (file index) | 210,740 files |
| DICOM_valid (file index) | 229 files |
| PNG_compressed (file index) | 5 files |
| PNG_train (file index) | 223,228 files |
| PNG_valid (file index) | 234 files |
| RadGraph XL Annotations (file index) | — |

**Do not download PNG or DICOM images yet.** The report/metadata table and three label resources were
audited locally in C3-E2; this does not authorize image downloading.

### Confirmed CheXpert Plus feasibility findings (C3-E2 audit)

These are **CheXpert Plus audit findings, not final model-performance or clinical results**:

- 191,071 frontal images from 187,674 frontal studies; the patient → study → image hierarchy and
  image-level label joins are clean.
- Combined permitted pre-diagnostic context is usable for approximately **60%** (60.3% unweighted;
  60.1% study-equal weighted).
- A substantial natural **39.7%** has absent (21.5%) or low-information (18.2%) context.
- All five registered labels are viable under both impression-derived and findings-derived labels.
- Direct target leakage in permitted context is low (maximum direct mention among positive labels
  3.84%).
- Impression-derived labels are primary; findings-derived labels are a mandatory sensitivity;
  report-derived labels are prohibited.
- Cardiomegaly has notable label-source prevalence sensitivity (15.2 percentage-point
  impression-minus-findings difference among known labels); the other targets differ by at most 4.5
  points.
- Results are effectively insensitive to the locked multiple-frontal-image policy.

Confirmed schema decisions: image key/join key `path_to_image`; patient key `deid_patient_id`;
derived study key `patient_folder + study_folder`; exact frontal category `Frontal`; AP/PA field
`ap_pa`; context fields `section_clinical_history` and `section_history`; four label states
1/0/-1/null. See `CHEXPERT_FULL_AUDIT_REPORT.md` and `C3E2_PHASE_CLOSURE.md`.

### MIMIC status
PhysioNet access requested, not yet approved. Once approved, download only:
- MIMIC report archive
- `mimic-cxr-2.0.0-chexpert.csv.gz`
- `mimic-cxr-2.0.0-metadata.csv.gz`
- `mimic-cxr-2.0.0-split.csv.gz`

Do not download MIMIC images unless the sequential data-validity gate passes and a separate dated
authorization is recorded. Reports/metadata-only intake is conditionally authorized after access and
DUA verification; follow `MIMIC_INTAKE_PROTOCOL.md` and `MIMIC_READINESS_CHECKLIST.md`. Audit command
template:
```
MIMIC_REPORTS=/actual/path/to/reports \
MIMIC_LABELS=/actual/path/to/mimic-cxr-2.0.0-chexpert.csv.gz \
MIMIC_METADATA=/actual/path/to/mimic-cxr-2.0.0-metadata.csv.gz \
MIMIC_SPLITS=/actual/path/to/mimic-cxr-2.0.0-split.csv.gz \
./scripts/run_mimic_audit.sh
```
(No placeholder paths — use real paths only.)

---

## 7. Workspace Layout

```
Base:      <local-research-workspace>
Project:   ${PROJECT_ROOT}
Toolkit:   ${PROJECT_ROOT}/c3e_audit_toolkit
CheXpert:  ${PROJECT_ROOT}/data/chexpert_plus
Labels:    ${PROJECT_ROOT}/data/chexpert_plus/labels
Main tbl:  ${PROJECT_ROOT}/data/chexpert_plus/df_chexpert_plus_240401.parquet
MIMIC:     ${PROJECT_ROOT}/data/mimic
```

### Completed local setup (Codex, 12 pre-access tasks)
Workspace structure, Python virtual environment, editable toolkit install, pytest install/run, research documentation, privacy controls, execution scripts, YAML validation, synthetic smoke testing, error-path testing, git exclusions, manual-access checklists, decision-gate documentation.

- Test result: `2 passed in 0.21s`
- Test log: `.../c3e/logs/toolkit_test.log`
- Audit environment: **Python 3.14.4 — keep unchanged**
- For future deep-learning work: use a **separate Python 3.11/3.12 env** (PyTorch / medical-imaging libs may not fully support 3.14)
- ShellCheck intentionally skipped (not installed, not a blocker)

### Documentation (`c3e/docs/`)
`research_log.md`, `closest_work.csv` (header-only — do not fabricate entries), `closest_work_README.md`, `terms_review.md`, `DATA_SAFETY.md`, `CHEXPERT_SCHEMA_MAPPING.md`, `MANUAL_ACCESS_TASKS.md`, `C3E_DECISION_GATE.md`, `SETUP_STATUS.md`

### Scripts (`c3e/scripts/`)
`check_environment.sh`, `run_mimic_audit.sh`, `run_chexpert_audit.sh`, `run_cross_site_comparison.sh`,
`collect_safe_outputs.sh`. The complete CheXpert Plus impression/findings audit passed on 2026-07-18.
MIMIC processing, cross-site evaluation, image download, and training have not occurred.

### Toolkit capabilities (does NOT train a model)
Report-section parsing, context-availability census, low-information context detection, target-term leakage detection, positive/negated/speculative mention detection, label prevalence analysis, missingness-by-label analysis, patient split overlap checks, cross-site context-shift comparison, automated gate-report generation.

### Target labels
- **Primary:** Cardiomegaly, Edema, Pleural Effusion
- **Secondary:** Atelectasis, Consolidation
- Term dictionary: `.../c3e_audit_toolkit/configs/terms.yaml` (reviewed by Codex, not modified)
- Documented ambiguity risks: "bare effusion" may be non-pleural; "linear opacity" too broad for atelectasis; "fluid overload" may be systemic not radiographic. **Do not add broad terms without validation** (ideally by a medical adviser).

---

## 8. Data Governance Rules (Mandatory)

**Never** upload or paste into ChatGPT, Codex cloud prompts, GitHub, email, Google Drive, hosted notebooks, or external APIs:
- Raw clinical reports, raw MIMIC text, raw CheXpert text
- Patient/study/image identifiers
- DICOM or PNG images
- Patient-level manifests, `study_aggregate.csv`
- Credentials, tokens, cookies, signed URLs

Raw medical text must not be processed via hosted LLM APIs. Only local processing is permitted unless the data-use agreement and approved infrastructure explicitly allow otherwise.

**Safe aggregate outputs (OK to discuss):** `summary.json`, `section_availability.csv`, `label_prevalence.csv`, `leakage_by_label.csv`, `missingness_by_label.csv`, `gate_report.json`, `cross_site_comparison.csv`, `cross_site_gate.json`, and other schema-level aggregate reports with no row-level identifiers or text.

**Never ask Shakib to upload raw datasets into chat.**

---

## 9. Current Phase: C3-E3 — Protocol Lock and MIMIC Readiness

**C3-E2 status:** closed and passed on 2026-07-18. The exact aggregate-safe findings and decisions are
frozen in `docs/C3E2_PHASE_CLOSURE.md` and
`results/c3e_chexpert_plus/C3E2_ARTIFACT_HASHES.sha256`.

**C3-E3 objective:** lock the external-validation boundary, hypotheses, statistical analysis, and
sequential MIMIC intake before MIMIC data or model outcomes can influence them.

**Authorized next action:** once individual MIMIC access and DUA status are verified, download and
checksum reports and metadata only, then proceed sequentially through the local intake protocol.

**Not authorized:** image download, model training, CheXpert-driven tuning, or cross-site claims
before the MIMIC gate passes.

---

## 10. Leakage Controls (Future)

Clinical history may directly mention target conditions. Required future controls:
exact target mention rate, synonym mention rate, negated mention rate, speculative/"rule-out" mention rate, text-only baseline, disease-term-masked text baseline, image-only baseline, empty-text baseline, shuffled-history baseline, counterfactual contradiction test.

**Forbidden model inputs:** Findings, Impression, Summary, diagnostic conclusion, full report embeddings, any text used to generate the labels.

**Eligible context:** Clinical History, History, Indication, Reason for examination.

---

## 11. C3-E Pass Criteria

**Proceed (GO) when:**
- ≥3 target labels have sufficient positive cases in source + external cohorts
- ≥40% of studies have usable pre-diagnostic context at both sites
- ≥1 site has ≥5% absent/low-information context
- Direct target mentions don't dominate nearly all positive histories
- Zero patient overlap across source splits
- A meaningful cross-site context-availability/quality shift exists
- Labels can be harmonized; join integrity verified; no unexplained many-to-many expansion

**MODIFY when:** only two labels viable / natural missingness weak but context-quality shift strong / direct disease mentions high but masked text still informative / context fields need different mappings at the two institutions.

**REJECT dataset route when:** fewer than two labels viable / context almost always absent / context almost always explicitly label-revealing / no meaningful cross-site context shift / labels can't be harmonized / patient-level separation can't be guaranteed / join integrity can't be established.

---

## 12. Status Snapshot (update as project progresses)

| Item | Status |
|---|---|
| Domain selection | Passed |
| Dataset route | Provisionally passed |
| CheXpert access | Passed |
| CheXpert label files | Downloaded |
| CheXpert full aggregate audit | Passed (C3-E2 closed) |
| CheXpert schema | Resolved |
| Join and hierarchy integrity | Passed |
| Usable context | 60.3% (CheXpert audit finding) |
| Absent/low-information context | 39.7% (CheXpert audit finding) |
| Target viability | All five viable under both label sources |
| Leakage risk | Low direct target leakage; report labels prohibited |
| Label-source risk | Cardiomegaly sensitivity; Findings mandatory |
| MIMIC access | Pending |
| Novelty | Provisional |
| Model development | Not authorized |
| Full image download | Not authorized |
| Cloud GPU spending | Not authorized |

No publication is guaranteed. CheXpert findings establish external-site feasibility only; the
cross-site premise still depends on the MIMIC data-validity and harmonization gates.

---

## 13. How Claude Should Operate on This Project

- Act as research-planning, literature, engineering, analysis, writing, and reviewer partner — not a rubber stamp. Every major decision gets a GO / MODIFY / REJECT verdict against the six gates.
- Use current web research when literature, funding, datasets, tools, or venues may have changed. Prioritize original papers, official dataset docs, official funding sources. No unsupported novelty claims.
- Do not shift research domains. Do not begin model training. Do not download full image sets. Do not ask Shakib to upload raw medical data into chat.
- Start a session by confirming project state in ≤1 paragraph (don't repeat full history unless needed), then proceed with the current phase's tasks — asking only for local directory-listing/schema results when needed, or providing safe local scripts/Codex prompts to gather them.
- End a work phase with: verified facts, unresolved issues, updated gate scores, GO/MODIFY/REJECT verdict, and the exact next action.
