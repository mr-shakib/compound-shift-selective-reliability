# Manual Access Tasks

**Claude/Codex cannot complete any of the tasks below.** They require account-level actions in a
browser (identity verification, clicking through data-use agreements, institutional review, uploading
training certificates, etc.) that only you can perform. This file is a checklist to track progress; it
does not grant, request, or simulate access on your behalf.

Update the checkboxes below yourself as you complete each step outside of this tool.

## PhysioNet (MIMIC-CXR / MIMIC-CXR-JPG)

- [ ] Account created
- [ ] Credentialing submitted
- [ ] Academic reference verified
- [ ] CITI training completed
- [ ] Full CITI training report uploaded
- [ ] MIMIC-CXR DUA accepted
- [ ] MIMIC-CXR-JPG DUA accepted
- [ ] Access approved
- [ ] Report archive downloaded
- [ ] Metadata files downloaded
- [ ] Full images not downloaded (confirm — this project does not need or want bulk image downloads yet)

## CheXpert Plus (Stanford AIMI / Redivis)

- [ ] Stanford AIMI page opened
- [ ] Redivis account created
- [ ] Dataset terms reviewed
- [ ] Access requested or granted
- [ ] Report-section table inspected
- [ ] Label table inspected
- [ ] Patient metadata inspected
- [ ] DICOM metadata inspected
- [ ] Relevant tables downloaded
- [ ] Full image collection not downloaded (confirm — this project does not need or want bulk image downloads yet)

## After access is granted

Once the checklists above are complete, return to this workspace and:

1. Update `docs/CHEXPERT_SCHEMA_MAPPING.md` with the real CheXpert Plus table/column names.
2. Finalize `c3e_audit_toolkit/configs/chexpert_plus.yaml`, resolving every `TODO` comment.
3. Run `scripts/run_mimic_audit.sh` and `scripts/run_chexpert_audit.sh` with your real local file paths.
4. Run `scripts/run_cross_site_comparison.sh`.
5. Run `scripts/collect_safe_outputs.sh` before sharing any results, and consult
   `docs/C3E_DECISION_GATE.md` to interpret the gate outcome.
