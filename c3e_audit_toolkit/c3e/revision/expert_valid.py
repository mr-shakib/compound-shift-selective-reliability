"""External-site report labels against radiologist labels (post hoc; Phase 0).

CheXpert's validation set (200 studies) was labelled from the images by a
consensus of three board-certified radiologists, and its images are part of
CheXpert Plus; 132 of its studies are in the external intervention cohort.
With the radiologist labels in hand (the CheXpert v1.0 ``valid.csv``, placed by
the corresponding author at ``EXPERT_VALID``; restricted, never committed),
this module measures, for the external site only:

* what each CheXbert report-label category (positive, negative, uncertain,
  unmentioned) corresponds to on the image, per pathology; in particular the
  share of *unmentioned* cells that radiologists call present, which decides
  whether "unmentioned = negative" is closer to the truth there;
* the selective error of each model at the frozen policy against the
  radiologist labels, beside the same quantity under the report-label
  handlings used in the paper, on the same studies.

It cannot compare sites: no comparable expert labels exist for the source.
Nothing is fitted. Output is aggregate only. If the file is absent the
analysis reports ``pending``.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from ..calibration.policy import TARGETS
from .engine import frozen_policy, labels_from_raw, load_site
from .estimators import decisions
from .fastboot import percentile_interval

EXPERT_VALID = "data/chexpert/valid.csv"
KEY = re.compile(r"(valid/patient\d+/study\d+)/")
SEED = 20260718


def load_expert(path: Path) -> pd.DataFrame:
    """Radiologist labels per study (any image positive -> positive)."""
    d = pd.read_csv(path)
    d["study_key"] = d["Path"].astype(str).str.extract(KEY, expand=False)
    if d.study_key.isna().any():
        raise ValueError("valid.csv: a Path does not match valid/patient#/study#/")
    lab = d.groupby("study_key")[list(TARGETS)].max()
    if not lab.isin([0, 1]).all().all():
        raise ValueError("valid.csv: radiologist labels must be 0 or 1")
    return lab.astype(int)


def _category(raw: np.ndarray) -> np.ndarray:
    return np.select([raw == 1, raw == 0, raw == -1], ["positive", "negative", "uncertain"], "unmentioned")


def _study_error(pred: np.ndarray, lab: np.ndarray, msk: np.ndarray) -> np.ndarray:
    n = msk.sum(1)
    w = ((pred != lab) & (msk > 0)).sum(1)
    return np.where(n > 0, w / np.maximum(n, 1), np.nan)


def analyse(root: Path, models=("M1", "M2", "M3", "M4"), replicates: int = 2000) -> dict[str, Any]:
    root = Path(root)
    path = root / EXPERT_VALID
    if not path.exists():
        return {"expert_valid_status": [{"status": "pending", "reason": f"{EXPERT_VALID} not present"}]}
    expert = load_expert(path)
    ext = load_site(root, "external", models=models, conditions=("C0",))
    keys = ext.cohort["study_key"].astype(str).to_numpy()
    idx = np.flatnonzero(np.isin(keys, expert.index.to_numpy()))
    E = expert.loc[keys[idx], list(TARGETS)].to_numpy()
    raw = ext.raw[idx]

    agree = []
    cat = _category(raw)
    for j, t in enumerate(TARGETS):
        for c in ("positive", "negative", "uncertain", "unmentioned"):
            sel = cat[:, j] == c
            agree.append({"pathology": t, "report_label": c, "studies": int(sel.sum()),
                          "radiologist_positive": int(E[sel, j].sum()),
                          "share_radiologist_positive": float(E[sel, j].mean()) if sel.any() else float("nan")})

    pol = frozen_policy(root)
    variants = {"radiologist": (E, np.ones_like(E, dtype=float))}
    for v in ("primary", "unmentioned_negative", "uncertain_positive"):
        variants[f"report_{v}"] = labels_from_raw(raw, v)
    rng = np.random.default_rng(SEED)
    boots = [rng.integers(0, len(idx), len(idx)) for _ in range(replicates)]
    risk = []
    for m in models:
        p = ext.probs[(m, "C0")][idx]
        pred = decisions(p, pol.thresholds[m])
        acc = pol.accepted(m, p)
        for name, (lab, msk) in variants.items():
            err = _study_error(pred, lab, msk)
            ok = acc & np.isfinite(err)
            draws = np.array([np.nanmean(np.where(ok[b], err[b], np.nan)) for b in boots])
            lo, hi = percentile_interval(draws)
            risk.append({"model": m, "labels": name, "studies": int(len(idx)), "accepted": int(acc.sum()),
                         "evaluable_accepted": int(ok.sum()), "selective_error": float(err[ok].mean()),
                         "ci_low": lo, "ci_high": hi})
    return {"expert_valid_status": [{"status": "done", "studies_matched": int(len(idx)),
                                     "studies_in_file": int(len(expert))}],
            "expert_valid_label_agreement": agree, "expert_valid_selective_error": risk}
