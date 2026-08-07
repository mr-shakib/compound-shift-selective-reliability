"""Guards on the frozen inference machinery. All fixtures are synthetic."""

from __future__ import annotations

import numpy as np
import pytest

from c3e.analysis.bootstrap import (BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED,
                                    MATERIALITY, bootstrap_pvalue,
                                    coverage_drift, decide, holm_adjust,
                                    independent_bootstrap, paired_bootstrap,
                                    percentile_ci, selective_error)


def _mean(d):
    return float(d["x"].mean())


def test_patient_clustering_widens_the_interval():
    """Resampling studies instead of patients would understate uncertainty.

    Each patient here contributes ten perfectly correlated studies, so the
    effective sample size is the patient count, not the row count.
    """
    rng = np.random.default_rng(0)
    per_patient = rng.normal(0, 1, 60)
    patients = np.repeat(np.arange(60), 10)
    x = np.repeat(per_patient, 10)

    clustered = paired_bootstrap(patients, {"x": x}, _mean, replicates=400, seed=1)
    naive = paired_bootstrap(np.arange(len(x)), {"x": x}, _mean, replicates=400, seed=1)
    lo_c, hi_c = percentile_ci(clustered)
    lo_n, hi_n = percentile_ci(naive)
    assert (hi_c - lo_c) > 2 * (hi_n - lo_n)


def test_paired_bootstrap_preserves_pairing():
    """A constant per-study difference must have near-zero interval width."""
    patients = np.repeat(np.arange(80), 3)
    base = np.random.default_rng(2).normal(0, 5, len(patients))
    vals = {"c0": base, "c1": base + 0.1}
    draws = paired_bootstrap(patients, vals, lambda d: float((d["c1"] - d["c0"]).mean()),
                             replicates=300)
    lo, hi = percentile_ci(draws)
    assert lo == pytest.approx(0.1, abs=1e-6)
    assert hi == pytest.approx(0.1, abs=1e-6)


def test_bootstrap_is_deterministic_under_the_frozen_seed():
    patients = np.repeat(np.arange(40), 2)
    x = np.random.default_rng(3).normal(0, 1, len(patients))
    a = paired_bootstrap(patients, {"x": x}, _mean, replicates=200, seed=BOOTSTRAP_SEED)
    b = paired_bootstrap(patients, {"x": x}, _mean, replicates=200, seed=BOOTSTRAP_SEED)
    assert np.array_equal(a, b)


def test_frozen_constants_match_the_protocol():
    assert BOOTSTRAP_REPLICATES == 2000
    assert BOOTSTRAP_SEED == 20260718
    assert MATERIALITY == 0.02


def test_independent_bootstrap_runs_over_two_sites():
    pa, pb = np.repeat(np.arange(30), 2), np.repeat(np.arange(50), 2)
    va = {"x": np.zeros(60)}
    vb = {"x": np.ones(100)}
    draws = independent_bootstrap(pa, va, pb, vb,
                                  lambda a, b: float(b["x"].mean() - a["x"].mean()),
                                  replicates=100)
    assert np.allclose(draws, 1.0)


def test_decision_requires_both_conditions():
    """CI excluding zero is not sufficient; the estimate must reach materiality."""
    tiny = decide(0.005, 0.001, 0.009)
    assert tiny["ci_excludes_zero"] and not tiny["reaches_materiality"]
    assert not tiny["confirmed"]

    big = decide(0.05, 0.01, 0.09)
    assert big["confirmed"]

    straddles = decide(0.05, -0.01, 0.11)
    assert straddles["reaches_materiality"] and not straddles["ci_excludes_zero"]
    assert not straddles["confirmed"]


def test_decision_at_exactly_materiality_is_confirmed_but_marginal():
    """The 50% power ceiling lives here: at a true effect equal to materiality,
    half of repetitions land below and fail."""
    assert decide(MATERIALITY, 0.001, 0.04)["confirmed"]
    assert not decide(MATERIALITY - 1e-9, 0.001, 0.04)["confirmed"]


def test_holm_is_monotone_and_bounded():
    adj = holm_adjust({"a": 0.001, "b": 0.02, "c": 0.04, "d": 0.5})
    assert all(0.0 <= v <= 1.0 for v in adj.values())
    assert adj["a"] <= adj["b"] <= adj["c"] <= adj["d"]
    assert adj["a"] == pytest.approx(0.004)


def test_holm_never_lowers_a_pvalue():
    raw = {"a": 0.01, "b": 0.02, "c": 0.03}
    adj = holm_adjust(raw)
    assert all(adj[k] >= raw[k] for k in raw)


def test_selective_error_handles_an_empty_acceptance_set():
    assert np.isnan(selective_error(np.array([1.0, 0.0]), np.array([0.1, 0.2]), 0.9))


def test_bootstrap_pvalue_is_small_for_a_clear_effect():
    assert bootstrap_pvalue(np.full(500, 0.3)) < 0.01
    assert bootstrap_pvalue(np.random.default_rng(0).normal(0, 1, 2000)) > 0.5


def test_coverage_drift_flags_the_stage8_observations():
    """Both drifts seen at the source site clear the 0.05 criterion."""
    assert coverage_drift(1.0, 0.8)["material"] is True     # M2 under C1
    assert coverage_drift(0.728, 0.8)["material"] is True   # M3 under C2
    assert coverage_drift(0.805, 0.8)["material"] is False  # M4 under C1


def test_interval_below_zero_is_reported_as_excluding_zero():
    """A reversed effect must not be reported as an absent one.

    An interval lying entirely below zero does exclude zero. Reporting
    otherwise, because the hypothesis predicted the other sign, would state
    something false about the interval and would turn a reversal into a null.
    """
    d = decide(-0.035, -0.041, -0.029, direction="greater_than_zero")
    assert d["ci_excludes_zero"] is True
    assert d["ci_supports_direction"] is False
    assert d["confirmed"] is False
    assert d["reversed_at_materiality"] is True


def test_small_reversal_is_not_flagged_as_material():
    d = decide(-0.005, -0.008, -0.002, direction="greater_than_zero")
    assert d["ci_excludes_zero"] is True
    assert d["reversed_at_materiality"] is False


def test_straddling_zero_is_neither_confirmed_nor_reversed():
    d = decide(0.03, -0.01, 0.07, direction="greater_than_zero")
    assert d["ci_excludes_zero"] is False
    assert d["confirmed"] is False
    assert d["reversed_at_materiality"] is False


def test_label_sources_are_the_two_the_protocol_fixes():
    """S1 is a label-source sensitivity, not an open parameter."""
    from c3e.training.dataset import LABEL_FILES

    assert set(LABEL_FILES) == {"impression", "findings"}
    assert "impression" in LABEL_FILES["impression"]
    assert "findings" in LABEL_FILES["findings"]


def test_unknown_label_source_is_refused(tmp_path):
    from c3e.training.dataset import build_index
    import pytest as _pytest

    with _pytest.raises(ValueError, match="unknown label source"):
        build_index(tmp_path, tier="model_train", label_source="report")
