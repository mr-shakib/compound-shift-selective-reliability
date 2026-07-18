"""Stage 2B study-level metric execution.

Standard binary metrics use scikit-learn.  AURC is the documented discrete
mean of prefix risks after descending-confidence sorting.  AUGRC is deliberately
not approximated: the frozen registry name remains pending a verified formula.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    hamming_loss,
    roc_auc_score,
)

from .contracts import ContractError, PATHOLOGIES


def _arrays(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return (
        y_true[list(PATHOLOGIES)].to_numpy(dtype=int),
        y_pred[list(PATHOLOGIES)].to_numpy(dtype=int),
    )


def hamming_error_per_study(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> np.ndarray:
    truth, predicted = _arrays(y_true, y_pred)
    return np.mean(truth != predicted, axis=1)


def five_label_hamming_loss(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> float:
    truth, predicted = _arrays(y_true, y_pred)
    return float(hamming_loss(truth, predicted))


def any_label_error_per_study(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> np.ndarray:
    truth, predicted = _arrays(y_true, y_pred)
    return np.any(truth != predicted, axis=1).astype(int)


def any_label_error(y_true: pd.DataFrame, y_pred: pd.DataFrame) -> float:
    return float(np.mean(any_label_error_per_study(y_true, y_pred)))


def pathology_binary_error(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.mean(y_true.to_numpy(dtype=int) != y_pred.to_numpy(dtype=int)))


def coverage(confidence: np.ndarray, threshold: float) -> float:
    confidence = np.asarray(confidence, dtype=float)
    if confidence.size == 0:
        raise ContractError("coverage requires at least one study")
    return float(np.mean(confidence >= threshold))


def selective_risk(losses: np.ndarray, confidence: np.ndarray, threshold: float) -> float:
    losses = np.asarray(losses, dtype=float)
    confidence = np.asarray(confidence, dtype=float)
    if losses.shape != confidence.shape:
        raise ContractError("selective risk requires aligned loss and confidence")
    retained = confidence >= threshold
    if not retained.any():
        raise ContractError("selective threshold retained zero studies")
    return float(np.mean(losses[retained]))


def risk_transport_gap(external_risk: float, source_risk: float) -> float:
    return float(external_risk - source_risk)


def coverage_transport_gap(external_coverage: float, source_coverage: float) -> float:
    return float(external_coverage - source_coverage)


def controlled_context_penalty(intervened_risk: float, original_risk: float) -> float:
    return float(intervened_risk - original_risk)


def compound_shift_interaction(
    external_intervened_risk: float,
    external_original_risk: float,
    source_intervened_risk: float,
    source_original_risk: float,
) -> float:
    return float(
        (external_intervened_risk - external_original_risk)
        - (source_intervened_risk - source_original_risk)
    )


def aurc(losses: np.ndarray, confidence: np.ndarray) -> float:
    losses = np.asarray(losses, dtype=float)
    confidence = np.asarray(confidence, dtype=float)
    if losses.shape != confidence.shape or losses.size == 0:
        raise ContractError("AURC requires non-empty aligned arrays")
    order = np.argsort(-confidence, kind="stable")
    ordered_losses = losses[order]
    prefix_risk = np.cumsum(ordered_losses) / np.arange(1, len(ordered_losses) + 1)
    return float(np.mean(prefix_risk))


def failure_detection_auroc(failures: np.ndarray, confidence: np.ndarray) -> float:
    failures = np.asarray(failures, dtype=int)
    if set(np.unique(failures)) != {0, 1}:
        raise ContractError("failure-detection AUROC requires successes and failures")
    return float(roc_auc_score(failures, 1.0 - np.asarray(confidence, dtype=float)))


def pathology_auroc(y_true: pd.Series, probabilities: pd.Series) -> float:
    return float(roc_auc_score(y_true.to_numpy(dtype=int), probabilities.to_numpy(dtype=float)))


def pathology_auprc(y_true: pd.Series, probabilities: pd.Series) -> float:
    return float(average_precision_score(y_true.to_numpy(dtype=int), probabilities.to_numpy(dtype=float)))


def pathology_brier_score(y_true: pd.Series, probabilities: pd.Series) -> float:
    return float(brier_score_loss(y_true.to_numpy(dtype=int), probabilities.to_numpy(dtype=float)))


def augrc_placeholder(*_args, **_kwargs):
    """AUGRC is locked but intentionally unavailable pending verification."""

    raise NotImplementedError(
        "AUGRC is pending a verified implementation; Stage 2B does not invent or approximate it"
    )
