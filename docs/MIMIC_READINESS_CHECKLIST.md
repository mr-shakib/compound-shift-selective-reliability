# MIMIC Readiness Checklist

Status: **PROTOCOL-READY; ACCESS AND INPUTS NOT YET VERIFIED**

Date: **2026-07-18**

Checkboxes document real state only. Do not mark an expected file or command as present until it is
verified locally.

## Access and governance

- [ ] Individual PhysioNet account and identity verification current.
- [ ] Required human-subject/privacy training current.
- [ ] MIMIC-CXR DUA accepted and access approved.
- [ ] MIMIC-CXR-JPG DUA accepted before any later image access.
- [ ] Local storage is encrypted or access-controlled as required by the DUA.
- [ ] No credentials, cookies, tokens, signed URLs, or raw data will enter source control or logs.
- [ ] No cloud text processing, hosted LLM, external API, hosted notebook, email, or unapproved cloud
      storage will receive report text, identifiers, parsed sections, or row-level labels.
- [ ] Every researcher who can access the data is independently authorized.

## Expected directory structure

The following is the intended structure, not a claim that the files exist:

```text
c3e/
├── data/
│   └── mimic/                         # local, credentialed, gitignored
│       ├── downloads/                 # original archives/CSV.GZ/checksum manifests
│       ├── reports/                   # optional local extraction; sensitive
│       ├── derived/                   # row-level parses/labels; sensitive
│       └── checksums/                 # publisher manifests + local verification log
├── results/
│   ├── c3e_mimic/                     # approved aggregate outputs only
│   └── c3e_cross_site/                # approved cross-site aggregates only
├── logs/                              # no text or identifiers
├── scripts/
└── c3e_audit_toolkit/
```

- [ ] Directories are local and have restrictive ownership/permissions.
- [ ] `data/mimic/` and all row-level derivatives remain excluded by `.gitignore`.
- [ ] No placeholder input files are created.

## Required free-space check

- [ ] Run `df -Pk` on the exact destination filesystem before downloading.
- [ ] Record available bytes, expected report/metadata download size, extraction size, derived-output
      allowance, and at least 20% working headroom.
- [ ] Confirm the report/metadata-only intake fits before step 2.
- [ ] Recalculate separately before any future image request; the current 5 GB environment warning
      threshold is not an authorization or an estimate of image-storage needs.
- [ ] Fail closed if size requirements are unknown or free space is insufficient.

## Expected files and checksum procedure

- [ ] Actual MIMIC-CXR report archive or extracted report tree verified.
- [ ] Actual `mimic-cxr-2.0.0-metadata.csv.gz` verified.
- [ ] Actual `mimic-cxr-2.0.0-split.csv.gz` verified.
- [ ] Actual `mimic-cxr-2.0.0-chexpert.csv.gz` verified as secondary reference labels.
- [ ] Publisher-provided checksum manifest obtained through authorized access.
- [ ] Release filenames/version checked against the authorized source at intake time.
- [ ] Compute the checksum algorithm named by the publisher locally (for example,
      `sha256sum -c <publisher-manifest>` only when the manifest actually uses SHA-256).
- [ ] Save a local verification log containing filenames, expected/observed digests, time, and
      pass/fail—never report text or identifiers.
- [ ] Any missing checksum, mismatch, unexpected file, partial download, or decompression error stops
      the intake. Redownload from the authorized source; never waive or fabricate verification.

## Python environments

- [ ] Audit environment present at `c3e_audit_toolkit/.venv` and `c3e-audit` import/CLI succeeds.
- [ ] Audit dependencies match `c3e_audit_toolkit/pyproject.toml` (Python ≥3.10, pandas, NumPy,
      PyYAML); record exact installed versions. The existing audit environment was built with Python
      3.14.4 and should remain isolated.
- [ ] Tests pass before intake, including synthetic safety tests.
- [ ] A separate Python 3.11/3.12 environment is created for local CheXbert/PyTorch work; do not
      retrofit deep-learning dependencies into the audit environment.
- [ ] CheXbert package/code, model weights, tokenizer, and PyTorch versions are pinned and their
      provenance/digests recorded before labeling.
- [ ] Network access is disabled during report parsing and CheXbert inference after required software
      artifacts have been obtained in a terms-compliant way.

## Expected scripts and commands

Present project entry points to verify before use:

- [ ] `scripts/check_environment.sh` — environment and free-space readiness.
- [ ] `scripts/run_mimic_audit.sh` — local reports/metadata audit with actual paths.
- [ ] `scripts/run_cross_site_comparison.sh` — aggregate cross-site comparison after both gates.
- [ ] `scripts/collect_safe_outputs.sh` — allowlisted aggregate collection.
- [ ] `c3e-audit mimic` — local MIMIC parser/auditor.

Required capabilities before their respective stage (these names are capabilities, not claims that
new placeholder scripts exist): checksum verification; schema-only inspection; hierarchy/join audit;
Findings/Impression parsing; pinned local CheXbert inference; label-distribution comparison; safe-output
scan; and MIMIC gate reporting.

- [ ] Each capability is implemented or mapped to a reviewed existing command before use.
- [ ] Commands fail on absent inputs and never fall back to placeholder/default data.
- [ ] A synthetic dry-run passes without writing identifiers or text to aggregate outputs.

## Safe output locations

- [ ] Safe MIMIC aggregates go only to `results/c3e_mimic/`.
- [ ] Safe cross-site aggregates go only to `results/c3e_cross_site/`.
- [ ] Shareable copies are created only through the reviewed allowlist in
      `scripts/collect_safe_outputs.sh` and manually inspected.
- [ ] Raw archives, extracted reports, linkage tables, section parses, per-study/per-image manifests,
      and row-level CheXbert labels remain under `data/mimic/` or another approved sensitive local
      path—never in shareable results.
- [ ] Logs contain counts/status only, no paths that expose identifiers, text snippets, or row-level
      values.

## Fail-closed conditions

Stop immediately if any of the following occurs:

- Access, training, DUA acceptance, or researcher authorization is missing/expired/unclear.
- Required checksums are unavailable or mismatched.
- Free disk space, storage controls, or file versions are insufficient/unknown.
- Patient/study/image keys cannot be verified; duplicates, unmatched records, split leakage, or
  unexplained many-to-many expansion remains.
- Clinical History scope is ambiguous or diagnostic Findings/Impression leaks into model inputs.
- A parser or output writes raw text, identifiers, row-level labels, or images outside the sensitive
  local area.
- CheXbert would call a cloud endpoint or use unpinned/unknown artifacts.
- Label encodings or report scopes cannot be harmonized with CheXpert Plus.
- MIMIC's data-validity gate fails or safe-output scanning fails.

## Authorization boundary

- [x] Protocol authorizes **reports-and-metadata intake only after access/DUA verification**.
- [ ] MIMIC access and DUA have been verified in this workspace session.
- [ ] Reports/metadata have been downloaded and checksummed.
- [ ] MIMIC data-validity gate has passed.
- [ ] Separate dated authorization for image download exists.
- [ ] Separate dated authorization for model training exists.

Until the final two authorizations are explicitly recorded: **no image download and no model
training**.
