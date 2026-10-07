"""Uncertainty from the finite calibration sample (exploratory; Revision R1).

Stage 10 intervals resample evaluation patients only. They condition on the
fitted models *and* on the thresholds and cutoffs selected from one realised
calibration tier (9,233 studies, 3,000 patients). This module quantifies the
second source: calibration patients are resampled with replacement, the frozen
selection *rule* (balanced-accuracy thresholds on supervised cells; abstention
cutoff at the 1 - coverage quantile of min |2p - 1|) is re-applied to each
resample, and the point estimates are recomputed on the fixed evaluation data.

This does not revise the frozen thresholds. It measures how much the reported
estimates would move had a different calibration sample been drawn. Training
variability is a third source, addressed only by the seed replicate.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..calibration.policy import abstention_threshold_for_coverage, balanced_accuracy_threshold
from ..calibration.policy import study_confidence
from .comparators import load_cal
from .engine import Site, labels_from_raw
from .estimators import decisions, risks_from_sums, term_matrix
from .fastboot import PatientIndex

SEED = 20260718


def _risk(p, lab, msk, thr, cut, est):
    acc = study_confidence(p, "minimum") >= cut
    T = term_matrix(decisions(p, thr), lab, msk)
    return float(risks_from_sums((T * acc[:, None]).sum(0))[est])


def run(root, src: Site, ext: Site, models=("M1", "M2", "M3", "M4"), replicates: int = 200,
        coverage: float = 0.8, estimators=("evaluable_study", "original")) -> list[dict[str, Any]]:
    ls, ms = labels_from_raw(src.raw)
    le, me = labels_from_raw(ext.raw)
    rows = []
    for m in models:
        cal = load_cal(root, m)
        pidx = PatientIndex(cal["patients"])
        rng = np.random.default_rng(SEED)
        ps, pe = src.probs[(m, "C0")], ext.probs[(m, "C0")]
        draws = {e: [] for e in estimators}
        thr_draws, cut_draws = [], []
        for _ in range(replicates):
            w = np.bincount(rng.integers(0, pidx.n, pidx.n), minlength=pidx.n)[pidx.inverse]
            rows_b = np.repeat(np.arange(len(w)), w.astype(int))
            p, y, k = cal["probabilities"][rows_b], cal["labels"][rows_b], cal["mask"][rows_b]
            thr = np.array([balanced_accuracy_threshold(p[:, j], y[:, j], k[:, j])[0] for j in range(5)])
            cut = abstention_threshold_for_coverage(study_confidence(p, "minimum"), coverage)
            thr_draws.append(thr)
            cut_draws.append(cut)
            for e in estimators:
                draws[e].append(_risk(pe, le, me, thr, cut, e) - _risk(ps, ls, ms, thr, cut, e))
        for e in estimators:
            d = np.asarray(draws[e])
            rows.append({"model": m, "estimator": e, "replicates": replicates,
                         "h1_mean": float(d.mean()), "h1_sd_calibration": float(d.std(ddof=1)),
                         "h1_q025": float(np.quantile(d, 0.025)), "h1_q975": float(np.quantile(d, 0.975)),
                         "cutoff_sd": float(np.std(cut_draws, ddof=1)),
                         "threshold_sd_by_pathology": np.std(np.asarray(thr_draws), axis=0, ddof=1).round(4).tolist()})
    return rows
