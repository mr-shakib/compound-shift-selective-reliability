"""The fast bootstrap must replay the Stage 10 draws exactly. Synthetic data."""

from __future__ import annotations

import numpy as np
import pytest

from c3e.analysis.bootstrap import independent_bootstrap, paired_bootstrap, selective_error
from c3e.revision.estimators import risks_from_sums, term_matrix
from c3e.revision.fastboot import (PatientIndex, bootstrap_p_two_sided, joint_sums,
                                   percentile_interval, single_sums)
from c3e.calibration.policy import hamming_error


def _site(rng, n_pat, labelled):
    pats = np.repeat(np.arange(n_pat), rng.integers(1, 4, n_pat)).astype(str)
    n = len(pats)
    pred = rng.integers(0, 2, (n, 5)).astype(float)
    labels = rng.integers(0, 2, (n, 5)).astype(float)
    mask = (rng.random((n, 5)) < labelled).astype(float)
    conf = rng.random(n)
    return pats, pred, labels, mask, conf


def test_joint_pass_reproduces_independent_bootstrap():
    rng = np.random.default_rng(3)
    ps, *a = _site(rng, 70, 0.2)
    pe, *b = _site(rng, 90, 0.3)
    cut = 0.2
    ea, eb = hamming_error(*a[:3]), hamming_error(*b[:3])
    ref = independent_bootstrap(ps, {"e": ea, "c": a[3]}, pe, {"e": eb, "c": b[3]},
                                lambda x, y: selective_error(y["e"], y["c"], cut)
                                - selective_error(x["e"], x["c"], cut), replicates=150, seed=11)
    Ts = term_matrix(*a[:3]) * (a[3] >= cut)[:, None]
    Te = term_matrix(*b[:3]) * (b[3] >= cut)[:, None]
    i_s, i_e = PatientIndex(ps), PatientIndex(pe)
    Ss, Se = joint_sums(i_s, i_s.aggregate(Ts), i_e, i_e.aggregate(Te), replicates=150, seed=11, batch=7)
    mine = risks_from_sums(Se)["original"] - risks_from_sums(Ss)["original"]
    np.testing.assert_allclose(mine, ref, rtol=0, atol=1e-12)


def test_single_pass_reproduces_paired_bootstrap():
    rng = np.random.default_rng(4)
    ps, pred, labels, mask, conf = _site(rng, 80, 0.25)
    e = hamming_error(pred, labels, mask)
    ref = paired_bootstrap(ps, {"e": e, "c": conf},
                           lambda v: selective_error(v["e"], v["c"], 0.3), replicates=120, seed=5)
    idx = PatientIndex(ps)
    S = single_sums(idx, idx.aggregate(term_matrix(pred, labels, mask) * (conf >= 0.3)[:, None]),
                    replicates=120, seed=5, batch=13)
    np.testing.assert_allclose(risks_from_sums(S)["original"], ref, rtol=0, atol=1e-12)


def test_percentile_interval_refuses_non_finite_replicates():
    with pytest.raises(ValueError):
        percentile_interval(np.array([0.1, np.nan, 0.2]))


def test_bootstrap_p_has_an_explicit_floor():
    p = bootstrap_p_two_sided(np.full(2000, 0.5))
    assert p == pytest.approx(2 / 2001)
    assert bootstrap_p_two_sided(np.array([-1.0, 1.0])) == pytest.approx(1.0)
