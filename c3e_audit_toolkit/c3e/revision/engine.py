"""Shared machinery: aligned sites, label variants, frozen policies, items.

An *item* is one (site, model, condition, label set, policy) combination,
represented by its per-study term matrix restricted to accepted studies and
over all studies (30 columns). Patient-aggregated items are concatenated so a
single bootstrap pass yields the replicate sums of every item at once; every
estimator and contrast is then arithmetic on those sums.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from ..calibration.policy import TARGETS, study_confidence
from .align import ALIGN_DIR, load_cache
from .estimators import N_COLS, decisions, risks_from_sums, term_matrix
from .fastboot import PatientIndex

LABEL_VARIANTS = ("primary", "unmentioned_negative", "uncertain_positive", "uncertain_negative")

STAGE7 = {
    ("impression", None): "results/c3e_mimic/stage7_thresholds/stage7_thresholds.json",
    ("findings", None): "results/c3e_mimic/stage7_thresholds_findings/stage7_thresholds.json",
    ("impression", 20260719): "results/c3e_mimic/stage7_thresholds_seed20260719/stage7_thresholds.json",
}


def labels_from_raw(raw: np.ndarray, variant: str = "primary") -> tuple[np.ndarray, np.ndarray]:
    """Map raw CheXbert values (1, 0, -1, NaN) to (labels, mask) under a variant.

    primary               1/0 kept; -1 and NaN unsupervised (the frozen rule)
    unmentioned_negative  NaN -> 0; -1 unsupervised   (sensitivity, not primary)
    uncertain_positive    -1 -> 1;  NaN unsupervised  (SAP-registered sensitivity)
    uncertain_negative    -1 -> 0;  NaN unsupervised  (SAP-registered sensitivity)
    """
    r = np.asarray(raw, dtype=float).copy()
    if variant == "unmentioned_negative":
        r = np.where(np.isnan(r), 0.0, r)
    elif variant == "uncertain_positive":
        r = np.where(r == -1.0, 1.0, r)
    elif variant == "uncertain_negative":
        r = np.where(r == -1.0, 0.0, r)
    elif variant != "primary":
        raise ValueError(f"unknown label variant {variant!r}")
    mask = np.isin(r, [0.0, 1.0]).astype(float)
    return np.where(mask > 0, r, 0.0), mask


@dataclass
class Policy:
    name: str
    thresholds: dict[str, np.ndarray]
    cutoffs: dict[str, float]
    confidence: Callable[[str, np.ndarray], np.ndarray] = field(
        default=lambda mid, p: study_confidence(p, "minimum"))

    def accepted(self, mid: str, probs: np.ndarray) -> np.ndarray:
        return self.confidence(mid, probs) >= self.cutoffs[mid]


def frozen_policy(root: Path, label_source: str = "impression", seed: int | None = None,
                  coverage: float = 0.8) -> Policy:
    s7 = json.loads((Path(root) / STAGE7[(label_source, seed)]).read_text())
    th, cu = {}, {}
    for mid, m in s7["models"].items():
        th[mid] = np.array([m["classification_thresholds"][t] for t in TARGETS])
        cu[mid] = m["abstention_thresholds"][f"{coverage:.2f}"]["abstention_threshold"]
    return Policy(name=f"frozen_{label_source}_{seed or 'primary'}_{coverage:.2f}",
                  thresholds=th, cutoffs=cu)


@dataclass
class Site:
    name: str
    cohort: pd.DataFrame
    raw: np.ndarray
    probs: dict[tuple[str, str], np.ndarray]
    pidx: PatientIndex

    @property
    def n(self) -> int:
        return len(self.cohort)


def load_site(root: Path, site: str, *, label_source: str = "impression", threshold: int = 3,
              seed: int | None = None, models=("M1", "M2", "M3", "M4"),
              conditions=("C0", "C1", "C2")) -> Site:
    root = Path(root)
    suffix = ("" if threshold == 3 else f"__T{threshold}") + (f"__seed{seed}" if seed else "")
    tag = f"{site}__{label_source}__T{threshold}" + (f"__seed{seed}" if seed else "")
    cohort = pd.read_parquet(root / ALIGN_DIR / f"{tag}.parquet")
    probs = {}
    for m in models:
        for c in conditions:
            z = load_cache(root, site, m, c, label_source, suffix)
            if not np.array_equal(z["patients"].astype(str), cohort["patient"].to_numpy().astype(str)):
                raise RuntimeError(f"{site}/{m}/{c}/{label_source}{suffix}: cache rows misaligned")
            probs[(m, c)] = z["probabilities"].astype(float)
    return Site(site, cohort, cohort[TARGETS].to_numpy(dtype=float), probs,
                PatientIndex(cohort["patient"].to_numpy().astype(str)))


def item_terms(probs: np.ndarray, labels: np.ndarray, mask: np.ndarray,
               thresholds: np.ndarray, accepted: np.ndarray) -> np.ndarray:
    T = term_matrix(decisions(probs, thresholds), labels, mask)
    return np.hstack([T * accepted[:, None], T])


class ItemSet:
    """Named items on one site; concatenated and patient-aggregated on demand."""

    def __init__(self, site: Site):
        self.site = site
        self.names: list[str] = []
        self.blocks: list[np.ndarray] = []

    def add(self, name: str, terms30: np.ndarray) -> None:
        if name in self.names:
            raise KeyError(f"duplicate item {name}")
        self.names.append(name)
        self.blocks.append(terms30)

    def matrix(self) -> np.ndarray:
        return self.site.pidx.aggregate(np.hstack(self.blocks))

    def point_sums(self) -> np.ndarray:
        return np.hstack(self.blocks).sum(axis=0)

    def slice_of(self, name: str) -> slice:
        k = self.names.index(name)
        return slice(k * 2 * N_COLS, (k + 1) * 2 * N_COLS)


def item_risk(sums: np.ndarray, items: ItemSet, name: str, estimator: str) -> np.ndarray:
    block = sums[..., items.slice_of(name)]
    return risks_from_sums(block[..., :N_COLS])[estimator]


def item_coverage(sums: np.ndarray, items: ItemSet, name: str) -> np.ndarray:
    block = sums[..., items.slice_of(name)]
    return block[..., 0] / block[..., N_COLS]


def item_terms_from_pred(pred: np.ndarray, labels: np.ndarray, mask: np.ndarray,
                         accepted: np.ndarray) -> np.ndarray:
    """As ``item_terms`` but for decisions not produced by per-pathology thresholds."""
    T = term_matrix(pred, labels, mask)
    return np.hstack([T * accepted[:, None], T])
