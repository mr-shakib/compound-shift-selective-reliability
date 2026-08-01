"""Faithful port of the CheXbert labeler to a modern transformers stack.

The upstream repository pins `transformers==2.5.1` / `torch==1.4.0` / Python 3.7,
which cannot be installed on this project's Python 3.14 environment. The model
itself is small and its API surface is narrow: a `BertModel` encoder plus 14
linear heads over the CLS token. Every call it makes is still stable in
`transformers` 5.x, so the architecture is reproduced exactly here rather than
the environment being downgraded.

Fidelity is not assumed. `validate_against_reference()` runs the port over the
reports shipped in the upstream repository and compares against the reference
labels shipped alongside them. The port must reproduce those labels before any
project label is generated.

Upstream: https://github.com/stanfordmlgroup/CheXbert
Commit:   6d22a96d73f18d0a7cf5b0dbebdac50cf8e4c1aa (2025-07-31)

Differences from upstream, all deliberate and provenance-relevant:

1. The encoder is built from an explicit `BertConfig` rather than
   `BertModel.from_pretrained('bert-base-uncased')`. Upstream downloads
   pretrained weights and then overwrites every one of them with the
   checkpoint's `state_dict`, so the download is redundant. Building from
   config makes the run independent of any remote weight host.
2. `nn.DataParallel` is not used. The checkpoint's `module.` key prefix is
   stripped explicitly instead, which yields identical weights on one device.
3. Inference runs under `torch.inference_mode()` with deterministic algorithms
   enabled and seeds fixed, as required by the artifact pinning plan.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
from pathlib import Path
import random
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import torch
import torch.nn as nn
from transformers import BertConfig, BertModel, BertTokenizer

# Upstream src/constants.py, reproduced verbatim. Order is load-bearing: it
# determines which linear head corresponds to which observation.
CONDITIONS = (
    "Enlarged Cardiomediastinum",
    "Cardiomegaly",
    "Lung Opacity",
    "Lung Lesion",
    "Edema",
    "Consolidation",
    "Pneumonia",
    "Atelectasis",
    "Pneumothorax",
    "Pleural Effusion",
    "Pleural Other",
    "Fracture",
    "Support Devices",
    "No Finding",
)
CLASS_MAPPING = {0: "Blank", 1: "Positive", 2: "Negative", 3: "Uncertain"}

# C3E label encoding, harmonised across sites (LABEL_HARMONIZATION_PLAN.md):
# 1.0 positive, 0.0 negative, -1.0 uncertain, None unmentioned.
CHEXBERT_CLASS_TO_C3E: dict[int, float | None] = {0: None, 1: 1.0, 2: 0.0, 3: -1.0}

# The five frozen C3E target pathologies, with their upstream head indices.
C3E_TARGETS = OrderedDict(
    (
        ("Cardiomegaly", 1),
        ("Edema", 4),
        ("Consolidation", 5),
        ("Atelectasis", 7),
        ("Pleural Effusion", 9),
    )
)

MAX_SEQUENCE_LENGTH = 512
PAD_IDX = 0
TOKENIZER_NAME = "bert-base-uncased"


class BertLabeler(nn.Module):
    """Architecture of upstream `src/models/bert_labeler.py`."""

    def __init__(self, p: float = 0.1) -> None:
        super().__init__()
        # bert-base-uncased geometry. Weights come entirely from the checkpoint.
        config = BertConfig(
            vocab_size=30522,
            hidden_size=768,
            num_hidden_layers=12,
            num_attention_heads=12,
            intermediate_size=3072,
        )
        self.bert = BertModel(config)
        self.dropout = nn.Dropout(p)
        hidden_size = self.bert.pooler.dense.in_features
        # 13 observations with 4 classes each, then 'No Finding' with 2.
        self.linear_heads = nn.ModuleList(
            [nn.Linear(hidden_size, 4, bias=True) for _ in range(13)]
        )
        self.linear_heads.append(nn.Linear(hidden_size, 2, bias=True))

    def forward(self, source_padded: torch.Tensor, attention_mask: torch.Tensor) -> list[torch.Tensor]:
        final_hidden = self.bert(source_padded, attention_mask=attention_mask)[0]
        cls_hidden = final_hidden[:, 0, :].squeeze(dim=1)
        cls_hidden = self.dropout(cls_hidden)
        return [self.linear_heads[i](cls_hidden) for i in range(14)]


@dataclass(frozen=True)
class LabelerProvenance:
    checkpoint_path: str
    checkpoint_sha256: str
    tokenizer_name: str
    transformers_version: str
    torch_version: str
    python_version: str
    device: str
    max_sequence_length: int
    batch_size: int
    deterministic: bool
    upstream_commit: str = "6d22a96d73f18d0a7cf5b0dbebdac50cf8e4c1aa"

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _set_determinism(seed: int = 20260718) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.benchmark = False


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def normalise_report(text: str) -> str:
    """Upstream `get_impressions_from_csv` normalisation, applied per string."""
    import re

    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def tokenize_reports(reports: Sequence[str], tokenizer: BertTokenizer) -> list[list[int]]:
    """Upstream `bert_tokenizer.tokenize`, including its truncation rule."""
    encoded: list[list[int]] = []
    for report in reports:
        pieces = tokenizer.tokenize(normalise_report(report))
        if pieces:
            # Upstream called `tokenizer.encode_plus(pieces)['input_ids']`, which
            # was removed in transformers 5.x. For a pre-tokenized list that call
            # was exactly: convert tokens to ids, then wrap in [CLS] ... [SEP].
            # Written out explicitly so no further API churn can change it.
            ids = (
                [tokenizer.cls_token_id]
                + tokenizer.convert_tokens_to_ids(pieces)
                + [tokenizer.sep_token_id]
            )
            if len(ids) > MAX_SEQUENCE_LENGTH:
                # Upstream keeps the first 511 ids and forces a final [SEP].
                ids = ids[:MAX_SEQUENCE_LENGTH - 1] + [tokenizer.sep_token_id]
        else:
            ids = [tokenizer.cls_token_id, tokenizer.sep_token_id]
        encoded.append(ids)
    return encoded


class CheXbertLabeler:
    """Loads the pinned checkpoint and labels reports."""

    def __init__(
        self,
        checkpoint_path: str | Path,
        *,
        device: str | None = None,
        batch_size: int = 32,
        tokenizer_dir: str | Path | None = None,
    ) -> None:
        _set_determinism()
        self.checkpoint_path = Path(checkpoint_path)
        if not self.checkpoint_path.exists():
            raise FileNotFoundError(
                f"CheXbert checkpoint not found at {self.checkpoint_path}. "
                "Download it from the upstream repository before labelling."
            )
        self.batch_size = batch_size
        self.device = torch.device(
            device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        )
        source = str(tokenizer_dir) if tokenizer_dir else TOKENIZER_NAME
        self.tokenizer = BertTokenizer.from_pretrained(source)

        self.model = BertLabeler()
        checkpoint = torch.load(self.checkpoint_path, map_location="cpu", weights_only=False)
        state = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint
        # Upstream saved under nn.DataParallel, which prefixes every key.
        cleaned = OrderedDict(
            (k[len("module."):] if k.startswith("module.") else k, v) for k, v in state.items()
        )
        missing, unexpected = self.model.load_state_dict(cleaned, strict=False)
        self.missing_keys = list(missing)
        self.unexpected_keys = list(unexpected)
        self.model.to(self.device).eval()

    def provenance(self) -> LabelerProvenance:
        import platform
        import transformers

        return LabelerProvenance(
            checkpoint_path=self.checkpoint_path.name,
            checkpoint_sha256=sha256_file(self.checkpoint_path),
            tokenizer_name=TOKENIZER_NAME,
            transformers_version=transformers.__version__,
            torch_version=torch.__version__,
            python_version=platform.python_version(),
            device=str(self.device),
            max_sequence_length=MAX_SEQUENCE_LENGTH,
            batch_size=self.batch_size,
            deterministic=True,
        )

    def predict_classes(self, reports: Sequence[str],
                        progress: Callable[[int, int], None] | None = None) -> np.ndarray:
        """Return an (n_reports, 14) array of upstream class indices.

        `progress` is an optional observer called with (completed, total) after
        each batch. It receives counts only, never report text, and cannot
        affect the computation.
        """
        encoded = tokenize_reports(reports, self.tokenizer)
        out = np.zeros((len(encoded), 14), dtype=np.int64)
        for start in range(0, len(encoded), self.batch_size):
            chunk = encoded[start:start + self.batch_size]
            tensors = [torch.tensor(ids, dtype=torch.long) for ids in chunk]
            padded = nn.utils.rnn.pad_sequence(tensors, batch_first=True, padding_value=PAD_IDX)
            mask = (padded != PAD_IDX).long()
            padded = padded.to(self.device)
            mask = mask.to(self.device)
            with torch.inference_mode():
                heads = self.model(padded, mask)
            for j, logits in enumerate(heads):
                out[start:start + len(chunk), j] = logits.argmax(dim=1).cpu().numpy()
            if progress is not None:
                progress(min(start + len(chunk), len(encoded)), len(encoded))
        return out

    def label_c3e_targets(self, reports: Sequence[str],
                          progress: Callable[[int, int], None] | None = None
                          ) -> list[dict[str, float | None]]:
        """Label the five frozen C3E pathologies in the C3E encoding."""
        classes = self.predict_classes(reports, progress=progress)
        rows = []
        for row in classes:
            rows.append(
                {name: CHEXBERT_CLASS_TO_C3E[int(row[idx])] for name, idx in C3E_TARGETS.items()}
            )
        return rows


def validate_against_reference(
    labeler: CheXbertLabeler, repo_src: str | Path
) -> dict[str, Any]:
    """Run the port over the upstream sample reports and compare to its labels.

    The upstream repository ships `sample_reports.csv` with `labeled_reports.csv`
    holding reference labels for the same reports. Agreement on those cells is
    the fidelity gate: the port must reproduce them before it labels anything
    belonging to this project.
    """
    import pandas as pd

    src = Path(repo_src)
    reports_df = pd.read_csv(src / "sample_reports.csv")
    reference = pd.read_csv(src / "labeled_reports.csv")

    reports = reports_df["Report Impression"].astype(str).tolist()
    predicted = labeler.predict_classes(reports)

    total = 0
    agree = 0
    disagreements: list[dict[str, Any]] = []
    for i in range(len(reports)):
        for j, condition in enumerate(CONDITIONS):
            if condition not in reference.columns:
                continue
            expected_raw = reference.iloc[i][condition]
            expected = None if pd.isna(expected_raw) else float(expected_raw)
            got = CHEXBERT_CLASS_TO_C3E[int(predicted[i][j])]
            total += 1
            if expected == got or (expected is None and got is None):
                agree += 1
            else:
                disagreements.append(
                    {"report_index": i, "condition": condition, "expected": expected, "got": got}
                )

    return {
        "reports_checked": len(reports),
        "cells_compared": total,
        "cells_agreeing": agree,
        "agreement_fraction": round(agree / total, 6) if total else 0.0,
        "exact_match": not disagreements,
        "disagreements": disagreements,
        "note": (
            "reference cells come from the upstream repository's own labeled_reports.csv; "
            "these are public sample reports, not project data"
        ),
    }
