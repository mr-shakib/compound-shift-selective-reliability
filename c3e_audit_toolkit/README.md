# C3-E Dataset Census and Leakage Audit Toolkit

This toolkit performs the **report-only and metadata-only audit** required before image-model development for:

- MIMIC-CXR / MIMIC-CXR-JPG
- CheXpert Plus

It is deliberately designed to run **locally**. Do not upload raw reports, patient-level manifests, or credentialed files to external APIs or chat systems.

## What it computes

1. Report-section availability
2. Empty and low-information context rates
3. Context token-length distributions
4. Frontal-view study counts
5. Label prevalence and uncertainty counts
6. Direct target-term and synonym mention rates
7. Negated and speculative target mentions
8. Missingness by label and optional metadata groups
9. Patient-overlap checks across source splits
10. A machine-readable C3-E gate report

The toolkit **does not** train an image model. A lightweight text-only model is intentionally deferred until the lexical audit passes.

## Installation

```bash
cd c3e_audit_toolkit
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Required MIMIC files

From authorized local downloads:

- `mimic-cxr-reports.zip` or extracted report directory
- `mimic-cxr-2.0.0-chexpert.csv.gz`
- `mimic-cxr-2.0.0-metadata.csv.gz`
- `mimic-cxr-2.0.0-split.csv.gz`

MIMIC report files are expected to be named like `sNNNNNNNN.txt`. The parser extracts the numeric study ID.

## Required CheXpert Plus files

CheXpert Plus schemas may change. Prepare one CSV or Parquet table containing:

- patient identifier
- study identifier
- image identifier or path, when available
- view position, when available
- one or more pre-diagnostic text fields
- the 14 pathology labels

Copy `configs/chexpert_plus.example.yaml` and set the real column names after inspecting the downloaded tables.

## Run MIMIC audit

```bash
c3e-audit mimic \
  --reports /secure/path/mimic-cxr-reports \
  --labels /secure/path/mimic-cxr-2.0.0-chexpert.csv.gz \
  --metadata /secure/path/mimic-cxr-2.0.0-metadata.csv.gz \
  --splits /secure/path/mimic-cxr-2.0.0-split.csv.gz \
  --config configs/mimic.yaml \
  --output /secure/results/c3e_mimic
```

The `--reports` argument may point to an extracted directory or directly to a `.zip` archive.

## Run CheXpert Plus audit

```bash
c3e-audit table \
  --table /secure/path/chexpert_plus_merged.parquet \
  --config configs/chexpert_plus.yaml \
  --output /secure/results/c3e_chexpert_plus
```

CSV, CSV.GZ, and Parquet are supported.

## Compare hospitals

```bash
c3e-audit compare \
  --source /secure/results/c3e_mimic/study_aggregate.csv \
  --target /secure/results/c3e_chexpert_plus/study_aggregate.csv \
  --output /secure/results/c3e_cross_site
```

## Safe outputs to share

You may share aggregate files such as:

- `summary.json`
- `section_availability.csv`
- `label_prevalence.csv`
- `leakage_by_label.csv`
- `cross_site_comparison.csv`
- `gate_report.json`

Do **not** share:

- `study_aggregate.csv`
- raw text
- patient/study/image identifiers
- any extracted reports

## C3-E pass rules encoded by default

The default gate report checks whether:

- at least 3 target labels have adequate positive counts
- at least 40% of studies have usable context
- at least 5% have absent or low-information context
- direct positive target mentions do not exceed 70% for every viable label
- patient overlap across MIMIC splits is zero
- at least one meaningful cross-site difference in context availability or quality exists

These are research-protocol thresholds, not universal clinical standards. They can be changed in YAML.

## Important scientific caveat

The lexical audit cannot establish whether context is clinically legitimate or represents target leakage. It identifies risk. Human review and later text-only, masked-text, shuffled-text, and contradiction experiments remain mandatory.
