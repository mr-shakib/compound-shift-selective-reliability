"""Patient-clustered bootstrap that replays the Stage 10 draws exactly.

Stage 10 resampled patients by concatenating each drawn patient's rows. A
statistic that is a ratio of sums is unchanged if, instead, each patient's
summed contribution is multiplied by the number of times that patient was
drawn, so the same random integers give the same replicate statistic without
materialising rows. Sums are taken over patient-aggregated columns and many
replicates are multiplied at once.

The draw order matches ``c3e.analysis.bootstrap`` exactly:

* ``joint``: one generator seeded 20260718; in each replicate draw source
  patients then external patients (``independent_bootstrap``). Every
  cross-site Stage 10 contrast restarted the generator at the same seed, so
  one joint pass reproduces all of them.
* ``single``: a fresh generator per site, drawing that site's patients only
  (``paired_bootstrap``), as within-site contrasts (H4) did.

Patients are indexed in ``np.unique`` order, as ``_patient_index`` did.
"""

from __future__ import annotations

import numpy as np

from ..analysis.bootstrap import BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED


class PatientIndex:
    def __init__(self, patients: np.ndarray):
        self.uniq, self.inverse = np.unique(np.asarray(patients), return_inverse=True)
        self.n = len(self.uniq)
        self._order = np.argsort(self.inverse, kind="stable")
        self._starts = np.searchsorted(self.inverse[self._order], np.arange(self.n))

    def aggregate(self, M: np.ndarray) -> np.ndarray:
        """Sum study-level rows within patient: (n_studies, C) -> (n_patients, C)."""
        M = np.asarray(M, dtype=float)
        if M.ndim == 1:
            M = M[:, None]
        return np.add.reduceat(M[self._order], self._starts, axis=0)


def _counts(rng: np.random.Generator, n: int) -> np.ndarray:
    return np.bincount(rng.integers(0, n, size=n), minlength=n).astype(float)


def joint_sums(src: PatientIndex, P_src: np.ndarray, ext: PatientIndex, P_ext: np.ndarray, *,
               replicates: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED,
               batch: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Replicate sums at both sites, drawn source-then-external per replicate."""
    rng = np.random.default_rng(seed)
    out_s = np.empty((replicates, P_src.shape[1]))
    out_e = np.empty((replicates, P_ext.shape[1]))
    for b0 in range(0, replicates, batch):
        k = min(batch, replicates - b0)
        Cs = np.empty((k, src.n))
        Ce = np.empty((k, ext.n))
        for i in range(k):
            Cs[i] = _counts(rng, src.n)
            Ce[i] = _counts(rng, ext.n)
        out_s[b0:b0 + k] = Cs @ P_src
        out_e[b0:b0 + k] = Ce @ P_ext
    return out_s, out_e


def single_sums(idx: PatientIndex, P: np.ndarray, *, replicates: int = BOOTSTRAP_REPLICATES,
                seed: int = BOOTSTRAP_SEED, batch: int = 100) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.empty((replicates, P.shape[1]))
    for b0 in range(0, replicates, batch):
        k = min(batch, replicates - b0)
        C = np.empty((k, idx.n))
        for i in range(k):
            C[i] = _counts(rng, idx.n)
        out[b0:b0 + k] = C @ P
    return out


def percentile_interval(draws: np.ndarray, level: float = 0.95) -> tuple[float, float]:
    draws = np.asarray(draws, dtype=float)
    finite = draws[np.isfinite(draws)]
    if len(finite) != len(draws):
        raise ValueError(f"{len(draws) - len(finite)} non-finite replicate(s); the SAP "
                         "forbids reporting an interval from fewer than the frozen count")
    a = (1.0 - level) / 2.0
    return float(np.quantile(draws, a)), float(np.quantile(draws, 1.0 - a))


def bootstrap_p_two_sided(draws: np.ndarray, null: float = 0.0) -> float:
    """Interval-inversion p-value with the 1/(B+1) floor made explicit."""
    draws = np.asarray(draws, dtype=float)
    b = len(draws)
    below = float(np.sum(draws <= null))
    above = float(np.sum(draws >= null))
    return float(min(1.0, 2.0 * (min(below, above) + 1.0) / (b + 1.0)))
