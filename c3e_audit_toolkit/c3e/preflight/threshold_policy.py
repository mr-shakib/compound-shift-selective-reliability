"""Frozen source-calibration-only classification and abstention policy."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

from .contracts import (
    ContractError,
    MULTIMODAL_PROBABILITY_COLUMNS,
    PATHOLOGIES,
    SOURCE_COVERAGES,
)
from .split_checks import require_source_calibration


@dataclass(frozen=True)
class FrozenThresholdPolicy:
    classification_items: tuple[tuple[str, float], ...]
    abstention_items: tuple[tuple[float, float], ...]
    fit_site_id: str
    fit_split_id: str
    criterion: str = "balanced_accuracy"
    confidence_definition: str = "minimum_abs_2p_minus_1"

    @property
    def classification_thresholds(self) -> dict[str, float]:
        return dict(self.classification_items)

    @property
    def abstention_thresholds(self) -> dict[float, float]:
        return dict(self.abstention_items)

    def as_dict(self) -> dict:
        return {
            "classification_thresholds": self.classification_thresholds,
            "abstention_thresholds": {
                f"{coverage:.2f}": threshold
                for coverage, threshold in self.abstention_items
            },
            "fit_site_id": self.fit_site_id,
            "fit_split_id": self.fit_split_id,
            "criterion": self.criterion,
            "confidence_definition": self.confidence_definition,
            "frozen": True,
        }


def _balanced_accuracy_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    if set(np.unique(y_true)) != {0, 1}:
        raise ContractError("balanced-accuracy threshold selection requires both classes")
    unique = np.unique(probabilities.astype(float))
    candidates = np.unique(np.concatenate(([0.0], unique, [np.nextafter(1.0, 2.0)])))
    scored: list[tuple[float, float]] = []
    for threshold in candidates:
        predictions = (probabilities >= threshold).astype(int)
        score = float(balanced_accuracy_score(y_true, predictions))
        scored.append((score, float(threshold)))
    best_score = max(score for score, _ in scored)
    tied = [threshold for score, threshold in scored if np.isclose(score, best_score)]
    return min(tied, key=lambda threshold: (abs(threshold - 0.5), threshold))


def minimum_margin_confidence(
    df: pd.DataFrame,
    *,
    probability_columns: tuple[str, ...] = MULTIMODAL_PROBABILITY_COLUMNS,
) -> np.ndarray:
    values = df[list(probability_columns)].to_numpy(dtype=float)
    if values.ndim != 2 or values.shape[1] != len(PATHOLOGIES):
        raise ContractError("study confidence requires exactly five pathology probabilities")
    return np.min(np.abs(2.0 * values - 1.0), axis=1)


def _threshold_for_coverage(confidence: np.ndarray, coverage: float) -> float:
    if not 0.0 < coverage <= 1.0 or len(confidence) == 0:
        raise ContractError("coverage threshold requires non-empty confidence and coverage in (0,1]")
    retained = max(1, math.ceil(coverage * len(confidence)))
    descending = np.sort(confidence.astype(float))[::-1]
    return float(descending[retained - 1])


def fit_source_threshold_policy(
    calibration_studies: pd.DataFrame,
    *,
    probability_columns: tuple[str, ...] = MULTIMODAL_PROBABILITY_COLUMNS,
) -> FrozenThresholdPolicy:
    require_source_calibration(calibration_studies, action="threshold fitting")
    thresholds: list[tuple[str, float]] = []
    for pathology, probability_column in zip(PATHOLOGIES, probability_columns):
        threshold = _balanced_accuracy_threshold(
            calibration_studies[pathology].to_numpy(dtype=int),
            calibration_studies[probability_column].to_numpy(dtype=float),
        )
        thresholds.append((pathology, threshold))
    confidence = minimum_margin_confidence(
        calibration_studies, probability_columns=probability_columns
    )
    abstention = tuple(
        (coverage, _threshold_for_coverage(confidence, coverage))
        for coverage in SOURCE_COVERAGES
    )
    return FrozenThresholdPolicy(
        classification_items=tuple(thresholds),
        abstention_items=abstention,
        fit_site_id=str(calibration_studies["site_id"].iloc[0]),
        fit_split_id=str(calibration_studies["split_id"].iloc[0]),
    )


def apply_classification_thresholds(
    df: pd.DataFrame,
    policy: FrozenThresholdPolicy,
    *,
    probability_columns: tuple[str, ...] = MULTIMODAL_PROBABILITY_COLUMNS,
) -> pd.DataFrame:
    thresholds = policy.classification_thresholds
    predictions = pd.DataFrame(index=df.index)
    for pathology, probability_column in zip(PATHOLOGIES, probability_columns):
        predictions[pathology] = (
            df[probability_column].astype(float) >= thresholds[pathology]
        ).astype(int)
    return predictions
