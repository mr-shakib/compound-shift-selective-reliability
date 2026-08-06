"""C3-E6 Stage 10: patient-clustered bootstrap and the confirmatory decision rule.

Everything here is fixed by the statistical analysis plan: 2,000 replicates,
seed 20260718, resampling patients rather than studies, and 95% percentile
intervals.

Patients are the resampling unit because a patient contributes several studies
whose errors are correlated. Resampling studies would treat those as independent
and understate the interval, which is the difference between a defensible
confidence statement and an overconfident one.

Within-site context contrasts are paired: C0, C1 and C2 are the same patients
under three interventions, so each replicate draws a patient set once and reads
all three conditions for it. Breaking the pairing would discard the very
variance reduction the crossed design was built to obtain.

Cross-institution contrasts are unpaired, since the two sites hold different
patients, and are drawn independently within each site.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20260718
CI_LEVEL = 0.95
MATERIALITY = 0.02
COVERAGE_DRIFT_MATERIALITY = 0.05


def percentile_ci(draws: np.ndarray, level: float = CI_LEVEL) -> tuple[float, float]:
    alpha = (1.0 - level) / 2.0
    return (float(np.quantile(draws, alpha)), float(np.quantile(draws, 1.0 - alpha)))


def _patient_index(patients: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    """Unique patients and the row positions belonging to each."""
    uniq, inverse = np.unique(patients, return_inverse=True)
    order = np.argsort(inverse, kind="stable")
    boundaries = np.searchsorted(inverse[order], np.arange(len(uniq) + 1))
    return uniq, [order[boundaries[i]:boundaries[i + 1]] for i in range(len(uniq))]


def paired_bootstrap(patients: np.ndarray, values: dict[str, np.ndarray],
                     statistic, *, replicates: int = BOOTSTRAP_REPLICATES,
                     seed: int = BOOTSTRAP_SEED) -> np.ndarray:
    """Patient-clustered bootstrap over several aligned condition arrays.

    `values` maps a condition name to a per-study array, all sharing the row
    order of `patients`. Each replicate draws patients once and evaluates
    `statistic` on that same draw across every condition, which is what keeps
    the comparison paired.
    """
    lengths = {len(v) for v in values.values()} | {len(patients)}
    if len(lengths) != 1:
        raise ValueError("patients and all condition arrays must share length")

    _, groups = _patient_index(patients)
    rng = np.random.default_rng(seed)
    n = len(groups)
    out = np.empty(replicates, dtype=float)
    for b in range(replicates):
        picked = rng.integers(0, n, size=n)
        rows = np.concatenate([groups[i] for i in picked])
        out[b] = statistic({k: v[rows] for k, v in values.items()})
    return out


def independent_bootstrap(patients_a: np.ndarray, values_a: dict[str, np.ndarray],
                          patients_b: np.ndarray, values_b: dict[str, np.ndarray],
                          statistic, *, replicates: int = BOOTSTRAP_REPLICATES,
                          seed: int = BOOTSTRAP_SEED) -> np.ndarray:
    """Unpaired bootstrap for a contrast between two sites.

    The sites hold different patients, so each is resampled independently rather
    than pretending a correspondence that does not exist.
    """
    _, groups_a = _patient_index(patients_a)
    _, groups_b = _patient_index(patients_b)
    rng = np.random.default_rng(seed)
    out = np.empty(replicates, dtype=float)
    for b in range(replicates):
        ra = np.concatenate([groups_a[i] for i in rng.integers(0, len(groups_a), len(groups_a))])
        rb = np.concatenate([groups_b[i] for i in rng.integers(0, len(groups_b), len(groups_b))])
        out[b] = statistic({k: v[ra] for k, v in values_a.items()},
                           {k: v[rb] for k, v in values_b.items()})
    return out


def selective_error(errors: np.ndarray, confidence: np.ndarray,
                    cutoff: float) -> float:
    """Mean error over accepted studies; NaN when a replicate accepts nothing."""
    accepted = confidence >= cutoff
    return float(errors[accepted].mean()) if accepted.any() else float("nan")


def decide(point: float, lo: float, hi: float, *,
           materiality: float = MATERIALITY,
           direction: str = "greater_than_zero") -> dict[str, object]:
    """Apply the frozen decision rule.

    A hypothesis is confirmed when the interval excludes zero **and** the point
    estimate itself reaches materiality.

    Note the consequence, established in Stage 3D: because the rule requires the
    point estimate to clear the threshold, a true effect exactly equal to
    materiality is confirmed in only half of repetitions, so power is capped at
    50% there regardless of sample size. Materiality is the smallest effect
    worth acting on, not the effect the study is powered against.
    """
    excludes_zero = (lo > 0.0) or (hi < 0.0)
    if direction == "greater_than_zero":
        material = point >= materiality
        excludes_zero = lo > 0.0
    elif direction == "greater_than_or_equal_zero":
        material = point >= 0.0
    else:
        material = abs(point) >= materiality
    return {
        "point_estimate": round(point, 6),
        "ci_low": round(lo, 6), "ci_high": round(hi, 6),
        "ci_excludes_zero": bool(excludes_zero),
        "reaches_materiality": bool(material),
        "materiality_threshold": materiality,
        "confirmed": bool(excludes_zero and material),
        "direction": direction,
    }


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm step-down correction for the per-pathology secondary family.

    The aggregate primary estimand does not pass through here: it is a single
    prespecified comparison and pays no multiplicity penalty.
    """
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, float] = {}
    running = 0.0
    for i, (key, p) in enumerate(items):
        adjusted = min(1.0, (m - i) * p)
        running = max(running, adjusted)
        out[key] = round(running, 6)
    return out


def bootstrap_pvalue(draws: np.ndarray, null: float = 0.0) -> float:
    """Two-sided bootstrap p-value by interval inversion.

    Reported for the secondary family only, so Holm has something to adjust.
    """
    finite = draws[np.isfinite(draws)]
    if len(finite) == 0:
        return float("nan")
    below = float((finite <= null).mean())
    return float(min(1.0, 2.0 * min(below, 1.0 - below)))


def coverage_drift(realised: float, target: float) -> dict[str, object]:
    """Coverage departure from target, against the frozen materiality.

    A frozen cutoff is supposed to hold the operating burden constant across
    sites and conditions. When it does not, the comparison is no longer at equal
    coverage, and the drift is itself a finding rather than a nuisance.
    """
    drift = realised - target
    return {
        "target_coverage": target,
        "realised_coverage": round(realised, 6),
        "drift": round(drift, 6),
        "material": bool(abs(drift) >= COVERAGE_DRIFT_MATERIALITY),
        "threshold": COVERAGE_DRIFT_MATERIALITY,
    }
