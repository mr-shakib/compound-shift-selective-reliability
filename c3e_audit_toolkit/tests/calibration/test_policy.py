"""Guards on the frozen classification and selective policies.

All fixtures are synthetic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from c3e.calibration.policy import (TARGETS, abstention_threshold_for_coverage,
                                    aggregate_images_to_studies,
                                    balanced_accuracy_threshold, hamming_error,
                                    selective_risk, study_confidence)


def test_threshold_recovers_a_clean_separation():
    prob = np.array([0.1, 0.2, 0.8, 0.9])
    label = np.array([0.0, 0.0, 1.0, 1.0])
    thr, bacc = balanced_accuracy_threshold(prob, label, np.ones(4))
    assert 0.2 < thr < 0.8
    assert bacc == pytest.approx(1.0)


def test_threshold_ignores_unsupervised_cells():
    prob = np.array([0.1, 0.9, 0.5, 0.5])
    label = np.array([0.0, 1.0, 1.0, 0.0])
    mask = np.array([1.0, 1.0, 0.0, 0.0])
    _, bacc = balanced_accuracy_threshold(prob, label, mask)
    assert bacc == pytest.approx(1.0)


def test_threshold_is_defined_when_one_class_is_absent():
    thr, bacc = balanced_accuracy_threshold(np.array([0.3, 0.4]),
                                            np.array([1.0, 1.0]), np.ones(2))
    assert thr == 0.5 and np.isnan(bacc)


def test_balanced_accuracy_beats_plain_accuracy_on_rare_positives():
    """Rare pathologies are why the criterion is balanced accuracy.

    Consolidation sits near 3% prevalence; a plain-accuracy threshold would
    drift toward predicting the majority class for every study.
    """
    rng = np.random.default_rng(0)
    n = 2000
    label = (rng.random(n) < 0.03).astype(float)
    prob = np.clip(rng.normal(0.2, 0.1, n) + label * 0.4, 0, 1)
    thr, bacc = balanced_accuracy_threshold(prob, label, np.ones(n))
    pred = prob >= thr
    assert pred.sum() > 0, "threshold must not abstain from predicting positives"
    assert bacc > 0.7


def test_confidence_is_certainty_not_positivity():
    prob = np.array([[0.99, 0.5, 0.5, 0.5, 0.5], [0.01, 0.5, 0.5, 0.5, 0.5]])
    conf = study_confidence(prob, "minimum")
    assert conf[0] == pytest.approx(conf[1]), "p=0.99 and p=0.01 are equally certain"


def test_minimum_confidence_is_the_weakest_pathology():
    prob = np.array([[0.99, 0.99, 0.55, 0.99, 0.99]])
    assert study_confidence(prob, "minimum")[0] == pytest.approx(0.1, abs=1e-6)
    assert study_confidence(prob, "mean")[0] > 0.7


def test_abstention_threshold_delivers_requested_coverage():
    conf = np.linspace(0, 1, 1000)
    for cov in (0.8, 0.9, 0.7):
        cutoff = abstention_threshold_for_coverage(conf, cov)
        assert (conf >= cutoff).mean() == pytest.approx(cov, abs=0.01)


def test_coverage_must_be_a_fraction():
    with pytest.raises(ValueError):
        abstention_threshold_for_coverage(np.linspace(0, 1, 10), 0.0)


def test_hamming_error_excludes_unsupervised_cells():
    pred = np.array([[1.0, 0.0, 1.0, 0.0, 1.0]])
    label = np.array([[1.0, 0.0, 0.0, 0.0, 0.0]])
    full = np.ones((1, 5))
    partial = np.array([[1.0, 1.0, 0.0, 1.0, 0.0]])
    assert hamming_error(pred, label, full)[0] == pytest.approx(2 / 5)
    assert hamming_error(pred, label, partial)[0] == pytest.approx(0.0)


def test_selective_risk_drops_when_low_confidence_studies_are_referred():
    errors = np.array([1.0, 1.0, 0.0, 0.0, 0.0])
    conf = np.array([0.1, 0.2, 0.8, 0.9, 0.95])
    r = selective_risk(errors, conf, 0.5)
    assert r["selective_hamming_error"] == pytest.approx(0.0)
    assert r["full_coverage_hamming_error"] == pytest.approx(0.4)
    assert r["coverage"] == pytest.approx(0.6)


def test_studies_are_aggregated_by_mean_not_counted_per_image():
    """A study with three frontal views must not count three times."""
    frame = pd.DataFrame({"subject_id": [1, 1, 1, 2],
                          "study_id": [10, 10, 10, 20]})
    for t in TARGETS:
        frame[t] = [0.0, 0.5, 1.0, 0.25]
        frame[t + "__label"] = [1.0, 1.0, 1.0, 0.0]
    out = aggregate_images_to_studies(frame)
    assert len(out) == 2
    assert out.loc[out.study_id == 10, TARGETS[0]].iloc[0] == pytest.approx(0.5)
