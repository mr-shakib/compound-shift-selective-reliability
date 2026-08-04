"""C3-E6 Stage 6: dataset joining preprocessed images, labels, and context text.

The decision unit is the study; the model inference unit is the image. A study
carries one label vector and one context string, and may have several frontal
images. Training samples are images so that every acquired image contributes
gradient; study-level aggregation happens at evaluation, not here.

Only the model-train tier is exposed. The threshold-calibration and
prespecified-eval tiers are reserved for later stages and this module refuses to
load them, so an accidental read cannot contaminate the confirmatory path.

Context text is pre-diagnostic only — indication and history, per
`text_policy.permitted_sections_source`. Findings, impression, wet reads and
full reports are forbidden as model input and never reach this class.
"""

from __future__ import annotations

from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from ..mimic_intake.stage3b_reports import HEADER_RE, SECTION_MAP

TARGETS = ["Cardiomegaly", "Edema", "Consolidation", "Atelectasis", "Pleural Effusion"]

# Frozen by protocol v0.4.0 text_policy.permitted_sections_source.
PERMITTED_SECTIONS = ("indication", "history")
FORBIDDEN_TIERS = ("threshold_calibration", "prespecified_eval",
                   "official_validate", "official_test")

# ImageNet statistics, required because the image backbone is ImageNet-initialised.
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class TierAccessError(RuntimeError):
    """Raised when a reserved evaluation tier is requested during training."""


def extract_permitted_context(text: str) -> str:
    """Header-driven extraction of the permitted pre-diagnostic sections.

    SECTION_MAP values are (canonical_name, class) pairs, so the name has to be
    unpacked before comparison. Comparing the pair directly against a name
    silently matches nothing and yields empty context for every report.
    """
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return ""
    parts: list[str] = []
    for i, m in enumerate(matches):
        mapped = SECTION_MAP.get(m.group(1).strip().upper())
        if mapped is None:
            continue
        canonical = mapped[0] if isinstance(mapped, tuple) else mapped
        if canonical not in PERMITTED_SECTIONS:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        parts.append(text[m.end():end].strip())
    return " ".join(p for p in parts if p).strip()


def load_context(data_root: Path, wanted_paths: set[str]) -> dict[str, str]:
    """Read permitted context for the given report paths from the report archive."""
    out: dict[str, str] = {}
    with zipfile.ZipFile(data_root / "reports/mimic-cxr-reports.zip") as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename not in wanted_paths:
                continue
            text = zf.read(info).decode("utf-8", errors="replace")
            out[info.filename] = extract_permitted_context(text)
    return out


def build_index(project_root: Path, tier: str = "model_train") -> pd.DataFrame:
    """Build the image-level training index for one tier.

    Returns one row per frontal image with its study's label vector and context.
    """
    if tier in FORBIDDEN_TIERS:
        raise TierAccessError(
            f"tier '{tier}' is reserved for a later stage and must not be read "
            "during training. Internal validation is carved from model_train."
        )

    root = Path(project_root).resolve()
    data_root = root / "data/mimic"

    labels = pd.read_csv(data_root / "labels/mimic_impression_labels.csv")
    labels = labels[labels["tier"] == tier].copy()
    if labels.empty:
        raise ValueError(f"no studies in tier '{tier}'")

    # Map study -> its frontal image paths, from the acquisition manifest.
    manifest = (data_root / "download_manifests/ALL_frontal_jpg_paths.txt").read_text().split()
    rows = []
    for p in manifest:
        parts = p.split("/")
        if len(parts) < 4:
            continue
        rows.append({"study_id": int(parts[3][1:]), "image_path": p})
    images = pd.DataFrame(rows)

    idx = labels.merge(images, on="study_id", how="inner")

    # Report path follows the same pXX/pXXXXXXXX/sYYYYYYYY layout.
    idx["report_path"] = idx["image_path"].map(
        lambda p: "/".join(p.split("/")[:4]) + ".txt")

    context = load_context(data_root, set(idx["report_path"]))
    idx["context"] = idx["report_path"].map(lambda p: context.get(p, ""))
    return idx.reset_index(drop=True)


def split_internal_validation(index: pd.DataFrame, *, fraction: float = 0.05,
                              seed: int = 20260718) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carve a patient-disjoint internal validation set out of model_train.

    Early stopping needs a held-out set, and the protocol forbids using the
    calibration or evaluation tiers for it. Splitting is on patient so no
    patient's images appear on both sides.
    """
    patients = np.sort(index["subject_id"].unique())
    rng = np.random.default_rng(seed)
    n_val = max(1, int(round(len(patients) * fraction)))
    val_patients = set(rng.choice(patients, size=n_val, replace=False).tolist())
    is_val = index["subject_id"].isin(val_patients)
    return index[~is_val].reset_index(drop=True), index[is_val].reset_index(drop=True)


class C3EStudyImageDataset(Dataset):
    """One frontal image, its study's five labels, and its pre-diagnostic context.

    Uncertain (-1) and unmentioned (NaN) labels are masked out of the loss rather
    than mapped to a class. The protocol treats them as absent supervision, and
    collapsing them into negatives would silently change label prevalence.
    """

    def __init__(self, index: pd.DataFrame, image_root: Path, tokenizer=None,
                 max_length: int = 128, train: bool = False):
        self.index = index.reset_index(drop=True)
        self.image_root = Path(image_root)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.train = train
        self._mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
        self._std = torch.tensor(IMAGENET_STD).view(3, 1, 1)

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, i: int) -> dict[str, torch.Tensor]:
        from PIL import Image

        row = self.index.iloc[i]
        with Image.open(self.image_root / row["image_path"]) as im:
            arr = np.asarray(im.convert("L"), dtype=np.float32) / 255.0
        img = torch.from_numpy(arr).unsqueeze(0).repeat(3, 1, 1)
        img = (img - self._mean) / self._std

        raw = row[TARGETS].to_numpy(dtype=np.float32)
        # 1 positive, 0 negative, -1 uncertain, NaN unmentioned.
        mask = np.isin(raw, [0.0, 1.0]).astype(np.float32)
        target = np.where(mask > 0, raw, 0.0).astype(np.float32)

        item = {
            "image": img,
            "target": torch.from_numpy(target),
            "mask": torch.from_numpy(mask),
        }
        if self.tokenizer is not None:
            enc = self.tokenizer(
                row["context"] or "", truncation=True, max_length=self.max_length,
                padding="max_length", return_tensors="pt")
            item["input_ids"] = enc["input_ids"].squeeze(0)
            item["attention_mask"] = enc["attention_mask"].squeeze(0)
        return item
