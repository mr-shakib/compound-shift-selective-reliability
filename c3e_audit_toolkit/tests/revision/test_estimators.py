"""Selective-risk estimators and the label-less-study defect. Synthetic data."""

from __future__ import annotations

import numpy as np
import pytest

from c3e.calibration.policy import hamming_error
from c3e.revision.engine import labels_from_raw
from c3e.revision.estimators import PolicyEval, risks_from_sums, summarise, term_matrix

NAN = np.nan


def _case():
    # Three studies: one labelled and wrong on 1 of 2 cells, one labelled and
    # right on its only cell, one with no labelled cell at all.
    pred = np.array([[1, 0, 0, 0, 0], [1, 1, 1, 1, 1], [1, 1, 1, 1, 1]], float)
    labels = np.array([[1, 1, 0, 0, 0], [1, 0, 0, 0, 0], [0, 0, 0, 0, 0]], float)
    mask = np.array([[1, 1, 0, 0, 0], [1, 0, 0, 0, 0], [0, 0, 0, 0, 0]], float)
    return pred, labels, mask


def test_original_estimator_counts_label_less_study_as_correct():
    pred, labels, mask = _case()
    e = hamming_error(pred, labels, mask)
    assert e.tolist() == [0.5, 0.0, 0.0]          # third study: zero error, no labels
    r = risks_from_sums(term_matrix(pred, labels, mask).sum(0))
    assert r["original"] == pytest.approx(0.5 / 3)  # matches Stage 10's mean
    assert r["evaluable_study"] == pytest.approx(0.5 / 2)
    assert r["cell_micro"] == pytest.approx(1 / 3)


def test_identity_original_equals_evaluable_times_evaluable_fraction():
    rng = np.random.default_rng(0)
    pred = rng.integers(0, 2, (500, 5)).astype(float)
    labels = rng.integers(0, 2, (500, 5)).astype(float)
    mask = (rng.random((500, 5)) < 0.15).astype(float)
    acc = rng.random(500) < 0.8
    s = summarise(PolicyEval(term_matrix(pred, labels, mask), acc))
    assert s["risk_original"] == pytest.approx(s["risk_evaluable_study"] * s["evaluable_fraction_accepted"])
    # Stage 7/8/9b computed the original as a plain mean over accepted studies.
    assert s["risk_original"] == pytest.approx(hamming_error(pred, labels, mask)[acc].mean())


def test_cross_site_gap_can_be_produced_by_label_availability_alone():
    """Two sites with identical error among labelled studies but different
    label availability: the original estimator reports a transfer gap, the
    corrected one does not."""
    rng = np.random.default_rng(1)
    def site(p_labelled):
        n = 20000
        mask = np.zeros((n, 5))
        lab = rng.random(n) < p_labelled
        mask[lab, 0] = 1
        labels = np.zeros((n, 5))
        pred = np.zeros((n, 5))
        pred[lab, 0] = (rng.random(lab.sum()) < 0.2)       # 20% error where labelled
        return risks_from_sums(term_matrix(pred, labels, mask).sum(0))
    src, ext = site(0.53), site(0.81)
    assert ext["original"] - src["original"] > 0.04
    assert abs(ext["evaluable_study"] - src["evaluable_study"]) < 0.01


def test_coverage_over_all_and_over_evaluable_studies_differ():
    pred, labels, mask = _case()
    s = summarise(PolicyEval(term_matrix(pred, labels, mask), np.array([True, False, True])))
    assert s["coverage_all"] == pytest.approx(2 / 3)
    assert s["coverage_evaluable"] == pytest.approx(1 / 2)


def test_pathology_macro_averages_per_pathology_rates():
    pred = np.array([[1, 0, 0, 0, 0], [0, 0, 0, 0, 0]], float)
    labels = np.array([[0, 0, 0, 0, 0], [0, 1, 0, 0, 0]], float)
    mask = np.array([[1, 0, 0, 0, 0], [1, 1, 0, 0, 0]], float)
    r = risks_from_sums(term_matrix(pred, labels, mask).sum(0))
    assert r["pathology_0"] == pytest.approx(0.5)
    assert r["pathology_1"] == pytest.approx(1.0)
    assert np.isnan(r["pathology_2"])
    assert r["pathology_macro"] == pytest.approx(0.75)


def test_label_variants_map_only_what_they_name():
    raw = np.array([[1, 0, -1, NAN, 1]], float)
    for variant, exp_mask, exp_lab in [
        ("primary", [1, 1, 0, 0, 1], [1, 0, 0, 0, 1]),
        ("unmentioned_negative", [1, 1, 0, 1, 1], [1, 0, 0, 0, 1]),
        ("uncertain_positive", [1, 1, 1, 0, 1], [1, 0, 1, 0, 1]),
        ("uncertain_negative", [1, 1, 1, 0, 1], [1, 0, 0, 0, 1]),
    ]:
        lab, msk = labels_from_raw(raw, variant)
        assert msk[0].tolist() == exp_mask and lab[0].tolist() == exp_lab, variant
    with pytest.raises(ValueError):
        labels_from_raw(raw, "everything_negative")


def test_empty_acceptance_yields_nan_not_zero():
    pred, labels, mask = _case()
    s = summarise(PolicyEval(term_matrix(pred, labels, mask), np.zeros(3, bool)))
    assert np.isnan(s["risk_evaluable_study"]) and np.isnan(s["risk_original"])
