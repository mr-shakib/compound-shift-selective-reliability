# C3-E Access Checklist

## MIMIC-CXR / MIMIC-CXR-JPG

- [ ] Create or verify PhysioNet account
- [ ] Complete the required human-research/data-privacy training
- [ ] Upload the full CITI training report, not only the certificate
- [ ] Sign the credentialed-data agreement
- [ ] Obtain approval for MIMIC-CXR
- [ ] Obtain approval for MIMIC-CXR-JPG
- [ ] Download reports archive first
- [ ] Download label, metadata, and split CSVs
- [ ] Do not download full image collection yet
- [ ] Store files on an encrypted or access-controlled local disk
- [ ] Do not send raw reports to hosted LLMs or external APIs

## CheXpert Plus

- [ ] Open the Stanford AIMI / Redivis dataset page
- [ ] Review and accept the current dataset terms
- [ ] Inspect the table schema before downloading images
- [ ] Download report-section, label, patient-metadata, and DICOM-metadata tables first
- [ ] Create `configs/chexpert_plus.yaml` from the example
- [ ] Export only the columns needed for C3-E
- [ ] Delay image download until the gate passes

## Outputs we need from you after running the audit

Share only these aggregate files:

- `summary.json`
- `section_availability.csv`
- `label_prevalence.csv`
- `leakage_by_label.csv`
- `missingness_by_label.csv`
- `gate_report.json`
- `cross_site_comparison.csv`
- `cross_site_gate.json`
