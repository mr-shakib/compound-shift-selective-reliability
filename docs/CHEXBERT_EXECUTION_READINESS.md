# CheXbert Execution Readiness

Status: **NOT READY — two hard blockers.** This file records exactly what is missing, what
you must do, and the provenance record that must be filled in *before* the first execution.

Governing document: `CHEXBERT_ARTIFACT_PINNING_PLAN.md` (plan locked 2026-07-18). That plan
requires a 16-item provenance record before first run. This file operationalises it.

---

## 1. Environment audit (checked 2026-07-28)

| Requirement | Status |
|---|---|
| `torch` | **MISSING** |
| `transformers` | **MISSING** |
| `tokenizers` | **MISSING** |
| `scikit-learn` | present |
| `scipy` | present |
| CheXbert checkpoint on disk | **ABSENT** |
| Disk free | 671 GB |

Two blockers, both requiring your action:

**Blocker 1 — ML stack not installed.** `torch` and `transformers` are not in the project
virtualenv. Installing them pulls roughly 2–3 GB. The pinning plan requires exact versions be
recorded, so install deliberately and record what you get.

**Blocker 2 — RESOLVED 2026-07-29. The upstream checkpoint link is dead.**

The URL in the CheXbert README
(`https://stanfordmedicine.box.com/s/c3stck6w6dol3h36grdc97xoydzxd7w9`) returns **HTTP 404**.
This is a known, unresolved upstream problem: repository issues #9, #10, #11 and #12 all
report it, spanning 2025-08 through 2026-02, with #12 still open.

The checkpoint is available instead from **`StanfordAIMI/RRG_scorers`** on HuggingFace, as
`chexbert.pth`. This is not a third-party mirror: StanfordAIMI is the same Stanford lab, and
CheXbert is a standard report-generation scorer, which is why it is bundled there. Issue #11
records the same finding.

```bash
mkdir -p data/models/chexbert
curl -sSL -o data/models/chexbert/chexbert.pth \
  https://huggingface.co/StanfordAIMI/RRG_scorers/resolve/main/chexbert.pth
sha256sum data/models/chexbert/chexbert.pth
```

Acquired file: 1,314,414,442 bytes (model weights plus Adam optimizer state, consistent with
a training checkpoint), SHA-256
`6550703c92d640e1e04d8105a7a185d76ece0f25fcbf033d292785bf22c0fde1`.

**License review remains your action** (provenance item: "license/terms review"). The
substitute source changes where the bytes came from, not what the terms are — record the
review against the CheXbert license, not the HuggingFace repository.

## 2. What you need to do

Detected hardware: **NVIDIA GeForce GTX 1660 SUPER, 6 GB VRAM, driver 595.71.05**
(Turing, compute capability 7.5 — supported by all current PyTorch builds).

Install the **CUDA** build, not the CPU one. The pinning plan's cross-site identity rule
requires the same torch version for all four label sets. Installing a CPU build now and
swapping to CUDA later for image-model training would break that identity and force the MIMIC
labels to be regenerated.

The project virtualenv runs **Python 3.14.4**. The `cu124` wheel index predates Python 3.14
and carries no matching wheels — use **cu126**, which does (torch 2.9.0 through 2.13.0).

```bash
cd "$(git rev-parse --show-toplevel)/c3e_audit_toolkit"

# CUDA build - cu126 has Python 3.14 wheels; cu124 does not.
.venv/bin/pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu126

# Verify CUDA is actually visible, and that Turing sm_75 is in the build.
.venv/bin/python -c "
import torch
print('torch', torch.__version__)
print('cuda available:', torch.cuda.is_available())
print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')
print('arch list:', torch.cuda.get_arch_list() if torch.cuda.is_available() else 'NONE')
print('smoke:', (torch.randn(1000,1000,device='cuda') @ torch.randn(1000,1000,device='cuda')).sum().item())
"
```

The smoke test matters: it confirms the build actually contains `sm_75` kernels for Turing,
which a version number alone does not establish.

**Do not install `transformers` yet, and do not record provenance versions yet.** CheXbert is
BERT-era code written against `transformers` 2.x/3.x. The current release is 5.x, which has
substantial API changes and may not load the checkpoint. Once you have the CheXbert repo, we
pin `transformers` from *its* `requirements.txt` rather than taking the newest release and
discovering the break later. The pinning plan wants the versions that actually ran, so the
record is written after the stack is proven, not before.

If `torch.cuda.is_available()` prints `False`, stop and tell me — labelling on CPU under a
CUDA-build install would still satisfy identity, but the device must be recorded truthfully
in provenance item 10, and mixed-device runs across the four label sets are not acceptable.

### VRAM headroom

CheXbert is BERT-base (~110M parameters), inference only. At batch 32 and sequence length
512 it needs roughly 2–3 GB, so 6 GB is comfortable for labelling.

6 GB does constrain the later image models, and this **resolves the open
`exact_backbones: PENDING_HARDWARE_GATE`** item. Realistic choices at 224x224 input:
DenseNet-121 (the CheXNet standard, ~8M parameters), ResNet-50, or EfficientNet-B0, at batch
sizes around 16-32. Large ViT or ConvNeXt backbones are not viable at this VRAM. Backbone
selection must still be recorded before any external result is inspected
(`architecture_selection_must_precede_external_results: true`).

Then obtain the CheXbert checkpoint from its official source, place it under a path inside
the gitignored data tree (for example `data/models/chexbert/`), and record its SHA-256:

```bash
sha256sum data/models/chexbert/<checkpoint-file>
```

Tell me when both are done and I will build the labelling harness against them.

## 3. Constraints that bind the run

From the pinning plan and the frozen protocol:

- **Local inference only.** No hosted inference, no external API. Report text must not leave
  the machine.
- **Cross-site identity.** The same code version, checkpoint bytes, tokenizer, package
  versions, preprocessing, section parser, label ontology and order, uncertainty mapping, and
  deterministic settings must be used for all four label sets: MIMIC impression, MIMIC
  findings, CheXpert Plus impression, CheXpert Plus findings. Mixing labeller families would
  confound the site effect with a labeller artefact — the exact failure the harmonisation plan
  exists to prevent.
- **MIMIC's shipped rule-based labels are not admissible** for the primary comparison. They
  are `official_mimic_labels_role: auxiliary_concordance_audit_only`.
- **Row-level outputs stay in the protected local data area.** Only aggregates reach `results/`.

## 4. Input definition (already fixed by protocol v0.3.0)

| Endpoint | Input section | Role |
|---|---|---|
| Impression | MIMIC `impression` section | primary label source |
| Findings | MIMIC `findings` section | sensitivity label source |

Section boundaries come from the frozen synonym map in
`experiment_registry.yaml: text_policy.source_section_synonyms`, using header-driven
extraction. Studies with merged findings/impression sections, or with no recognised header,
are already excluded from the cohort (200 studies).

Encoding, harmonised across sites: `1.0` positive, `0.0` negative, `-1.0` uncertain,
`null` unmentioned.

## 5. Provenance record template

Fill this in **before** the first execution and save it as
`logs/chexbert_provenance_<YYYY-MM-DD>.md`. All sixteen items are required by the pinning plan.

```
# CheXbert Provenance Record

## Artifact
 1. official repository URL:
 2. repository git commit hash or released version:
 3. model checkpoint filename:
 4. checkpoint SHA-256:
 5. tokenizer name and version:
 6. transformers version:
 7. pytorch version:
 8. python version:

## Execution
 9. inference batch size:
10. device:
11. deterministic settings (all seeds, deterministic-algorithm flags):
12. exact text-section input definition and normalization/preprocessing order:
13. label ontology and output order:
14. uncertain-label representation:
15. inference date:
16. SHA-256 of each row-level output (retained in protected local data area only),
    plus aggregate-safe output checksum:

## Additional (required by the pinning plan)
- package-lock / environment provenance:
- checkpoint acquisition source:
- license and terms review (date, reviewer, outcome):
- missing-section behaviour:
- maximum sequence length:
- truncation / padding behaviour:
- case and whitespace handling:
- mapping from raw model outputs to the four C3E label states:
```

## 6. What labelling unblocks

Once labels exist:

- **M2 (text-only) becomes runnable with no images and no GPU.** It is the
  `text_signal_and_shortcut_control`. If indication and history alone predict the five
  pathologies well, any later fusion gain is suspect as a text shortcut rather than
  multimodal reasoning — a result worth knowing *before* committing to the image download.
- **The power analysis sharpens.** Base risk is currently swept across 0.05–0.30. Measured
  label prevalence replaces that grid with a single row and narrows the reported MDE.

One caution: **M2 cannot carry the context-intervention experiment.** C1 replaces all
permitted context, and M2's only input *is* permitted context — so C1 on M2 leaves a model
with no input at all. The C0/C1/C2 contrasts genuinely require M3/M4, and therefore images.
M2 is a control, not a substitute for the multimodal arm.

## 7. Ordering

Labelling does **not** require images. It can proceed in parallel with, or entirely before,
any decision about the ~69–285 GB image download (see
`results/c3e_mimic/stage3e/stage3e_image_budget.csv`). Doing it first is the cheaper order:
it produces real results, sharpens the design, and de-risks the expensive path.
