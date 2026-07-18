# CheXbert Artifact Pinning Plan

Status: **PLAN LOCKED; NO DOWNLOAD OR EXECUTION AUTHORIZED**

Date: **2026-07-18**

CheXbert may not be run until MIMIC access/DUA verification, local environment preparation, artifact
provenance review, and the recording gate below are complete. All report text processing and inference
must remain local; no hosted inference or external API is allowed.

## Required pre-execution record

Before the first execution, create a dated local provenance record containing:

1. official repository URL;
2. exact repository Git commit hash or released version;
3. model checkpoint filename;
4. checkpoint SHA-256;
5. tokenizer name and version;
6. Transformers version;
7. PyTorch version;
8. Python version;
9. inference batch size;
10. device;
11. deterministic settings, including all random seeds and applicable deterministic-algorithm flags;
12. exact text-section input definition and normalization/preprocessing order;
13. label ontology and output order;
14. uncertain-label representation;
15. inference date; and
16. SHA-256 of each local row-level output, retained only in the protected local data area, plus a
    separate aggregate-safe output checksum where applicable.

The record must also include package-lock/environment provenance, checkpoint acquisition source,
license/terms review, missing-section behavior, maximum sequence length, truncation/padding behavior,
case/whitespace handling, and mapping from raw model outputs to the four C3E label states.

## Cross-site identity requirement

The same verified CheXbert code/version, checkpoint bytes, tokenizer, package versions,
preprocessing, section parser, ontology/order, uncertainty mapping, batch-independent inference logic,
and deterministic settings are required for all locally generated endpoint labels:

- MIMIC Impression sections;
- MIMIC Findings sections;
- CheXpert Plus Impression sections; and
- CheXpert Plus Findings sections.

MIMIC Impression and CheXpert Plus Impression must share one pinned pipeline; MIMIC Findings and
CheXpert Plus Findings must share that same pinned pipeline with only the declared input section
changed. Any unavoidable difference is a harmonization failure or a preregistered sensitivity—not an
unreported implementation detail.

## Supplied CheXpert Plus label artifacts

CheXpert Plus currently supplies precomputed Impression- and Findings-derived label artifacts. Record
the CheXpert Plus dataset release/version, filenames, file checksums in the protected local provenance
record, documented label ontology/encoding, and all Stanford AIMI metadata available about their
generation.

Do **not** claim that these supplied artifacts were generated with the future locally pinned
checkpoint, tokenizer, or preprocessing unless Stanford AIMI provenance verifies that exact identity.
Exact upstream checkpoint reproducibility may depend on metadata that Stanford AIMI does not provide.

For the primary cross-site claim, artifact identity must be established by one of two routes before
evaluation: (a) upstream metadata verifies equivalence to the pinned local pipeline, or (b) under
separate authorization, both institutions' Impression and Findings sections are relabeled locally
with the identical pinned pipeline. Until one route passes, the supplied labels remain valid for the
completed CheXpert feasibility audit but exact cross-site labeler harmonization is unresolved.

## Execution gate

Before any CheXbert run, verify:

- MIMIC access and DUA status;
- local-only text handling and access-controlled outputs;
- complete artifact record and matching SHA-256;
- a synthetic, non-clinical dry-run;
- no cloud telemetry or remote inference;
- identical preprocessing across sites/scopes except the declared section field; and
- a dated authorization for the local labeling step.

No CheXbert artifact is downloaded, no report is parsed, and no inference is performed in C3-E4.
