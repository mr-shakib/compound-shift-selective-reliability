"""Verify that the frozen Stage 7 selections reproduce from revision caches.

Re-applies the frozen rule (balanced-accuracy per-pathology thresholds on
supervised calibration cells; abstention cutoff at the 1 - coverage quantile of
minimum |2p - 1|) to calibration-tier predictions and compares with the
committed Stage 7 artifact. A reproduction is evidence that the calibration
pipeline and the revision caches describe the same models; it selects nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..calibration.policy import (TARGETS, abstention_threshold_for_coverage,
                                  balanced_accuracy_threshold, study_confidence)
from .inference import rev_cache_path


def check(root: Path, model: str, train_seed: int | None = None,
          stage7_rel: str = "results/c3e_mimic/stage7_thresholds/stage7_thresholds.json"
          ) -> dict:
    root = Path(root)
    z = np.load(rev_cache_path(root, site="source", tier="threshold_calibration", model=model,
                               cond="C0", train_seed=train_seed, c2_seed=None))
    s7 = json.loads((root / stage7_rel).read_text())["models"][model]
    out = {"model": model, "train_seed": train_seed, "studies": int(len(z["probabilities"]))}
    diffs = []
    for j, t in enumerate(TARGETS):
        thr, _ = balanced_accuracy_threshold(z["probabilities"][:, j], z["labels"][:, j], z["mask"][:, j])
        diffs.append(abs(round(thr, 6) - s7["classification_thresholds"][t]))
    out["max_abs_threshold_diff"] = float(max(diffs))
    conf = study_confidence(z["probabilities"], "minimum")
    cd = []
    for cov in ("0.70", "0.80", "0.90"):
        cd.append(abs(round(abstention_threshold_for_coverage(conf, float(cov)), 6)
                      - s7["abstention_thresholds"][cov]["abstention_threshold"]))
    out["max_abs_cutoff_diff"] = float(max(cd))
    out["reproduces"] = bool(out["max_abs_threshold_diff"] <= 1e-6 and out["max_abs_cutoff_diff"] <= 1e-5)
    return out
