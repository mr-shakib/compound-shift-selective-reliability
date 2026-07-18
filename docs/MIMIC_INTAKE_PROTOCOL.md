# MIMIC Intake Protocol

Status: **READY FOR CONDITIONAL METADATA/REPORT INTAKE; NO INTAKE PERFORMED**

Date: **2026-07-18**

This protocol applies when authorized MIMIC-CXR access arrives. It does not assert that any expected
file is currently present and does not authorize image downloading or model training.

## Expected authorized inputs

The intake expects the actual versioned files supplied through the authorized PhysioNet release:

- MIMIC-CXR report archive or its locally extracted report tree (commonly distributed as
  `mimic-cxr-reports.zip`).
- `mimic-cxr-2.0.0-metadata.csv.gz`.
- `mimic-cxr-2.0.0-split.csv.gz`.
- `mimic-cxr-2.0.0-chexpert.csv.gz` for distribution/reference comparison only; its rule-based labels
  are not the primary cross-site labels.
- The official checksum manifest(s) accompanying the authorized downloads.

Release names and checksums must be confirmed against the files visible to the authorized researcher
at intake time. No empty or placeholder file may be created to satisfy a check.

## Ordered intake procedure

The steps are sequential and fail closed. A later step is not authorized until the earlier step has
passed and been logged.

1. **Verify access and DUA status.** Confirm the named researcher has current individual PhysioNet
   credentialing, required training, accepted DUA(s), and access to the intended MIMIC-CXR resources.
   Record confirmation without storing credentials or access tokens.
2. **Download reports and metadata only.** Download only the report archive, metadata, official split,
   reference label file, and checksum manifest to access-controlled local storage. Do not download
   JPG/DICOM images.
3. **Verify checksums.** Validate every downloaded file against the publisher-provided checksum before
   extraction or parsing. A missing manifest or mismatch stops intake; do not invent a checksum.
4. **Inspect schema locally.** Record only filenames, sizes, compression types, column names, dtypes,
   row counts, null/unique counts, and safe categorical counts. Do not emit report examples or
   identifier values.
5. **Derive patient/study/image hierarchy.** Verify the patient, study, and image keys; join
   cardinalities; split integrity; duplicate keys; unmatched rows; and expansion factors. Reject
   unexplained many-to-many joins. Keep row-level linkage local and unshared.
6. **Audit Clinical History availability.** Parse only permitted pre-diagnostic Clinical History /
   Indication / Reason-for-exam content locally. Quantify absent, low-information, and usable context
   using the frozen rule. Do not send text to cloud services.
7. **Parse Findings and Impression.** Use a versioned local parser; preserve missing sections and
   write no report text to shareable outputs. Findings and Impression are label sources only, never
   model inputs.
8. **Run CheXbert locally on Findings and Impression.** Use a pinned local environment and model
   artifact permitted by the applicable terms. Record version, weights digest, parser version,
   report scope, encoding, and date. No hosted inference or external API is allowed.
9. **Compare label distributions.** Compare MIMIC CheXbert Findings versus Impression, and separately
   compare the official rule-based labels as a secondary reference. Preserve 1/0/-1/unmentioned
   states and report only safe aggregates.
10. **Confirm harmonization with CheXpert Plus.** Require CheXbert Impression at both sites for the
    primary endpoint and CheXbert Findings at both sites for sensitivity. Verify the same five target
    names, text scopes, encoding, uncertainty policy, and known-label rules. Do not mix the official
    MIMIC CheXpert-labeler output with CheXpert Plus CheXbert labels in primary tables.
11. **Run the MIMIC data-validity gate.** Verify context availability/quality, viable labels, direct
    leakage, patient-level split integrity, safe outputs, hierarchy, joins, and the planned cross-site
    context-shift comparison. Record GO/MODIFY/REJECT with unresolved risks.
12. **Authorize image downloading only after the gate passes.** Image download requires a separate,
    explicit dated authorization that also verifies DUA scope, required disk capacity, storage
    controls, exact image subset, and an analysis plan. Passing this protocol alone does not download
    or train on images.

## Outputs and logging

Raw reports, identifiers, linkage tables, parsed sections, and CheXbert row-level outputs remain under
the access-controlled local data area and are never committed or shared. Only aggregate outputs
approved by `DATA_SAFETY.md` may enter `results/c3e_mimic/` or `results/c3e_cross_site/`. Each step's
status, checksum verification, software versions, and gate decision must be recorded in the research
log without raw values.

## Current authorization

- Steps 1–2: **conditionally authorized when access arrives**, beginning with human verification of
  access/DUA and limited to reports, metadata, split, reference labels, and checksum manifests.
- Steps 3–11: authorized only sequentially after prior checks pass, using local processing.
- Step 12 / image download: **not authorized now**.
- Model training: **not authorized now**.
