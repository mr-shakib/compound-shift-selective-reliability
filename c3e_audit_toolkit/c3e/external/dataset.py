"""C3-E9b: the external-site cohort and dataset.

Context at this site arrives as columns — `section_clinical_history` and
`section_history` — rather than as sections parsed out of a report body. That is
a different mechanism from the source site but the same intent, and it is what
`text_policy.permitted_sections_external` specifies. The informativeness rule
that classifies N1, N2 and N3 is the source-site rule applied unchanged;
refitting it here would be external-site tuning.

The one image that is corrupt in the published dataset is excluded, and the
exclusion is counted rather than hidden.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from ..evaluation.interventions import natural_state
from ..training.dataset import IMAGENET_MEAN, IMAGENET_STD, TARGETS

PARQUET = "data/chexpert_plus/df_chexpert_plus_240401.parquet"
LABELS = "data/chexpert_plus/labels/impression_fixed.json"
SENSITIVITY_LABELS = "data/chexpert_plus/labels/findings_fixed.json"
IMAGE_DIR = "data/chexpert_plus/images_224"

#: Frozen by text_policy.permitted_sections_external.
PERMITTED_COLUMNS = ("section_clinical_history", "section_history")


def build_external_index(project_root: Path, *,
                         label_source: str = "impression") -> pd.DataFrame:
    """One row per usable frontal image, with labels, context, and patient.

    Studies are identified by the directory portion of the image path, since the
    published table carries no study identifier of its own.
    """
    root = Path(project_root).resolve()
    meta = pd.read_parquet(root / PARQUET, columns=[
        "path_to_image", "deid_patient_id", "frontal_lateral", "split",
        *PERMITTED_COLUMNS])
    frontal = meta[meta["frontal_lateral"].str.lower() == "frontal"].copy()

    label_path = root / (LABELS if label_source == "impression" else SENSITIVITY_LABELS)
    labels = pd.read_json(label_path, lines=True)
    keep = ["path_to_image", *TARGETS]
    labels = labels[[c for c in keep if c in labels.columns]]

    idx = frontal.merge(labels, on="path_to_image", how="inner")
    if len(idx) != len(frontal):
        raise RuntimeError(
            f"label join changed row count: {len(frontal)} -> {len(idx)}; the "
            "frozen one-to-one join on path_to_image is a protocol assumption")

    # Permitted context is the concatenation of the two permitted columns.
    parts = [idx[c].fillna("").astype(str) for c in PERMITTED_COLUMNS]
    idx["context"] = (parts[0] + " " + parts[1]).str.strip()

    idx["study_key"] = idx["path_to_image"].str.rsplit("/", n=1).str[0]
    idx["natural_state"] = idx["context"].map(natural_state)

    # Drop images that are unusable in the published dataset. Counted by the
    # caller; silently dropping them would misstate the cohort.
    image_root = root / IMAGE_DIR
    idx["_present"] = [(image_root / p).exists() for p in idx["path_to_image"]]
    return idx.reset_index(drop=True)


class CheXpertPlusDataset(Dataset):
    """One frontal image, its five labels, and its permitted context.

    Normalisation, channel replication, and label masking match the source-site
    dataset exactly. Anything that differed here would confound the site effect
    the study exists to estimate.
    """

    def __init__(self, index: pd.DataFrame, image_root: Path, tokenizer=None,
                 max_length: int = 128):
        self.index = index.reset_index(drop=True)
        self.image_root = Path(image_root)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self._mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
        self._std = torch.tensor(IMAGENET_STD).view(3, 1, 1)

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, i: int) -> dict[str, torch.Tensor]:
        from PIL import Image

        row = self.index.iloc[i]
        with Image.open(self.image_root / row["path_to_image"]) as im:
            arr = np.asarray(im.convert("L"), dtype=np.float32) / 255.0
        img = torch.from_numpy(arr).unsqueeze(0).repeat(3, 1, 1)
        img = (img - self._mean) / self._std

        raw = row[TARGETS].to_numpy(dtype=np.float32)
        mask = np.isin(raw, [0.0, 1.0]).astype(np.float32)
        target = np.where(mask > 0, raw, 0.0).astype(np.float32)

        item = {"image": img,
                "target": torch.from_numpy(target),
                "mask": torch.from_numpy(mask)}
        if self.tokenizer is not None:
            enc = self.tokenizer(row["context"] or "", truncation=True,
                                 max_length=self.max_length, padding="max_length",
                                 return_tensors="pt")
            item["input_ids"] = enc["input_ids"].squeeze(0)
            item["attention_mask"] = enc["attention_mask"].squeeze(0)
        return item
