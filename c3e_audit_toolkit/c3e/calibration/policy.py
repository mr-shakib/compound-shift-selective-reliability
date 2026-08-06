"""C3-E6 Stage 7: the frozen classification and selective policies.

Every rule here is fixed by the protocol registry and reproduced faithfully.
Nothing in this module is tunable, and nothing may be revised once the external
site has been inspected — that prohibition is the whole point of the transport
design, since a threshold refitted at the target site would answer a different
question than the one preregistered.

Inference happens per image; decisions happen per study. Frontal images of a
study are combined by arithmetic mean probability, per `analysis_units`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TARGETS = ["Cardiomegaly", "Edema", "Consolidation", "Atelectasis", "Pleural Effusion"]


def aggregate_images_to_studies(image_probs: pd.DataFrame) -> pd.DataFrame:
    """Arithmetic mean of per-image probabilities within each study.

    The decision unit is the study, but the model sees images, so a study with
    three frontal views must not count three times.
    """
    cols = {t: "mean" for t in TARGETS}
    cols.update({t + "__label": "first" for t in TARGETS})
    out = image_probs.groupby(["subject_id", "study_id"], as_index=False).agg(cols)
    return out


def balanced_accuracy_threshold(prob: np.ndarray, label: np.ndarray,
                                mask: np.ndarray, n_grid: int = 999
                                ) -> tuple[float, float]:
    """Per-pathology threshold maximising balanced accuracy on supervised cells.

    Balanced accuracy rather than accuracy because these pathologies are far
    from balanced — Consolidation sits near 3% — and a plain-accuracy threshold
    would drift toward predicting the majority class everywhere.

    Returns (threshold, balanced_accuracy). Returns 0.5 when a class is absent,
    since no threshold is identifiable from one class.
    """
    sel = mask > 0
    p, y = prob[sel], label[sel]
    if len(y) == 0 or len(np.unique(y)) < 2:
        return 0.5, float("nan")

    grid = np.linspace(1.0 / (n_grid + 1), n_grid / (n_grid + 1), n_grid)
    pos, neg = y == 1, y == 0
    n_pos, n_neg = pos.sum(), neg.sum()

    pred = p[None, :] >= grid[:, None]
    tpr = (pred & pos[None, :]).sum(axis=1) / n_pos
    tnr = (~pred & neg[None, :]).sum(axis=1) / n_neg
    bacc = (tpr + tnr) / 2.0
    best = int(np.argmax(bacc))
    return float(grid[best]), float(bacc[best])


def study_confidence(prob: np.ndarray, mode: str = "minimum") -> np.ndarray:
    """Study-level confidence from per-pathology probabilities.

    Per-pathology confidence is |2p - 1|: certainty about the decision, not
    about the positive class. Study confidence is the minimum across the five,
    so a study is only as trustworthy as its least certain finding. The mean is
    retained as the registry's secondary definition.
    """
    per = np.abs(2.0 * prob - 1.0)
    if mode == "minimum":
        return per.min(axis=1)
    if mode == "mean":
        return per.mean(axis=1)
    raise ValueError(f"unknown confidence mode '{mode}'")


def abstention_threshold_for_coverage(confidence: np.ndarray,
                                      coverage: float) -> float:
    """Confidence cutoff admitting the requested fraction of studies.

    Selected on the calibration tier and then transferred frozen. Coverage is
    fixed and accuracy is allowed to vary, rather than the reverse, so the
    source and external sites are compared at the same operating burden on the
    human reader.
    """
    if not 0.0 < coverage <= 1.0:
        raise ValueError(f"coverage must be in (0, 1]; got {coverage}")
    return float(np.quantile(confidence, 1.0 - coverage))


def hamming_error(pred: np.ndarray, label: np.ndarray, mask: np.ndarray
                  ) -> np.ndarray:
    """Per-study five-label Hamming error over supervised cells.

    Unsupervised cells are excluded rather than counted correct, which would
    reward the labeller's silence.
    """
    wrong = (pred != label) & (mask > 0)
    denom = np.maximum(mask.sum(axis=1), 1.0)
    return wrong.sum(axis=1) / denom


def selective_risk(errors: np.ndarray, confidence: np.ndarray,
                   cutoff: float) -> dict[str, float]:
    """Risk on accepted studies, plus realised coverage.

    Realised coverage can differ slightly from the target when confidence ties
    at the cutoff, so it is reported rather than assumed.
    """
    accepted = confidence >= cutoff
    n = len(errors)
    return {
        "coverage": float(accepted.mean()) if n else 0.0,
        "accepted_studies": int(accepted.sum()),
        "total_studies": int(n),
        "selective_hamming_error": float(errors[accepted].mean()) if accepted.any() else float("nan"),
        "full_coverage_hamming_error": float(errors.mean()) if n else float("nan"),
    }
