# Provenance and Versioning Policy

Status: **LOCKED 2026-07-18**

## Repository boundary

Git tracks only reproducibility and review artifacts:

- source code;
- configuration files;
- synthetic tests;
- executable project scripts;
- protocol, policy, audit, and phase-closure documentation;
- environment and package specifications; and
- reviewed aggregate-safe outputs and their checksum manifests.

Git never tracks raw medical data, report text, images, DICOM, raw label files, row-level patient /
study / image exports, temporary manifests, credentials, tokens, cookies, signed URLs, local virtual
environments, caches, downloaded archives, model checkpoints, or weights. `.gitignore` is a safety
boundary, not permission to use unrestricted staging. Every staging operation must use an explicit
allowlist; `git add .` is prohibited for this project.

## Phase checkpoints

Every major research phase receives a named commit or an annotated tag after its allowlist and staged
content pass safety review. The checkpoint record includes commit hash, branch/tag, commit date,
committed-file count, safety result, and working-tree state. A checkpoint message contains no private
absolute path, credential, identifier, or outcome-dependent claim.

The C3-E2/C3-E3 baseline is commit
`6b02a62de50ffe36fc336eb3201ababbd109f19b` on `main`. The original C3-E2 SHA-256 manifest predates
repository initialization and is retained unchanged as historical evidence; subsequent amendments
are represented by Git commits rather than rewriting the historical manifest.

## Hash retention

Configuration hashes and aggregate-safe output hashes are retained with their phase. A historical
manifest is immutable. If a later phase intentionally changes a hashed configuration or policy, the
new phase records the change and may create a new manifest; it never overwrites the earlier digest.
Raw data files are neither hashed into a shareable manifest nor listed in it.

## Version records

Before each experiment, record at minimum:

- dataset name, institution, release/version, authorized acquisition date, and publisher checksum
  status without raw paths or identifiers;
- source commit and clean/dirty state;
- configuration file digest;
- Python and package versions plus environment lock/specification;
- model architecture/version, initialization/pretraining provenance, and checkpoint SHA-256;
- labeler/model version, tokenizer, preprocessing, deterministic settings, and output digest; and
- hardware/device class, random seeds, execution date, and safe result checksum.

Dataset version records never include credentials, signed URLs, local private paths, report text, or
patient/study/image identifiers.

## Protocol amendments

Any change after protocol lock requires a dated amendment document or a clearly identified amendment
section in the affected policy. It must state what changed, why, whether outcomes had been viewed, and
which hypotheses/endpoints are affected. The amendment is committed before execution when possible.

Preregistered decisions must not be silently overwritten, deleted, backdated, or presented as if the
new choice were original. If model or external-evaluation results influenced a change, the affected
analysis is labeled exploratory and is separated from the locked confirmatory analysis.

## Pre-commit safety gate

Before every checkpoint:

1. verify raw-data exclusions with `git check-ignore`;
2. stage explicit approved paths only;
3. list staged names and sizes;
4. scan staged content for identifiers, path patterns, images/DICOM references, split paths,
   internal keys, secrets, cookies, and unusually long text;
5. distinguish clearly marked synthetic/schema fixtures from real values;
6. unstage and investigate any unsafe file; and
7. commit only after the index is clean and reviewed.

Failure or ambiguity is fail-closed. No remote upload is implied or authorized by a local commit.
