"""Weighted AUROC used for the post hoc discrimination analysis."""

from __future__ import annotations

import numpy as np

from c3e.revision.selective import _auroc_prep, auroc, weighted_auroc


def test_unit_weights_match_rank_auroc_with_ties():
    rng = np.random.default_rng(0)
    s = np.round(rng.random(500), 2)  # many ties
    y = rng.random(500) < 0.3
    assert np.isclose(weighted_auroc(_auroc_prep(s, y), np.ones(500)), auroc(s, y))


def test_integer_weights_match_repeated_cases():
    rng = np.random.default_rng(1)
    s = np.round(rng.random(200), 1)
    y = rng.random(200) < 0.4
    w = rng.integers(0, 4, 200)
    rep = np.repeat(np.arange(200), w)
    assert np.isclose(weighted_auroc(_auroc_prep(s, y), w), auroc(s[rep], y[rep]))


def test_one_class_is_undefined():
    s = np.array([0.1, 0.2, 0.3])
    assert np.isnan(weighted_auroc(_auroc_prep(s, np.zeros(3, bool)), np.ones(3)))
