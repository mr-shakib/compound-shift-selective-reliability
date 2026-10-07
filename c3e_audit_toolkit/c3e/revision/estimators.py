"""Selective-risk estimators, made explicit.

Notation. Study i has five pathology cells j. y_ij is the label, m_ij = 1 when
the cell carries a positive or negative label (uncertain and unmentioned cells
have m_ij = 0), yhat_ij = 1[p_ij >= t_j] is the thresholded decision, and
a_i = 1[g_i >= tau] is acceptance by the frozen abstention cutoff. Let
n_i = sum_j m_ij, w_i = sum_j m_ij 1[yhat_ij != y_ij], and e_i = w_i / n_i when
n_i > 0.

``original`` (what Stage 7/8/9b/10 computed):
    R_orig = sum_i a_i * w_i / max(n_i, 1)  /  sum_i a_i
  A study with no labelled cell (n_i = 0) contributes error 0 to the numerator
  and 1 to the denominator, i.e. it is counted as correct. The code's docstring
  states the intent was the opposite ("unsupervised cells are excluded rather
  than counted correct"), so this is a verified implementation defect for any
  study whose five cells are all unsupervised.

``evaluable_study`` (minimal correction; the registered MET001 mean(L_i | g_i >= tau)
taken over studies where L_i is defined):
    R_eval = sum_i a_i 1[n_i > 0] e_i  /  sum_i a_i 1[n_i > 0]
  Identity: R_orig = R_eval * P(n_i > 0 | accepted).

``cell_micro``: pooled over labelled cells of accepted studies
    R_cell = sum_i a_i w_i / sum_i a_i n_i

``pathology_macro``: unweighted mean over the five pathologies of the
    per-pathology selective error over labelled cells of accepted studies.

Coverage is reported over all eligible studies (the deployed quantity: the
policy accepts or refers every study, labelled or not) and over evaluable
studies only.

Every estimator is a ratio of weighted sums, so one bootstrap pass can carry
all of them: a replicate is a vector of non-negative integer patient
multiplicities expanded to studies.
"""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np

ESTIMATORS = ("original", "evaluable_study", "cell_micro", "pathology_macro")
N_TARGETS = 5

# Column layout of the per-study term matrix.
COL_ONE, COL_EVAL, COL_EORIG, COL_NWRONG, COL_NOBS = 0, 1, 2, 3, 4
COL_WRONG_J = slice(5, 5 + N_TARGETS)
COL_OBS_J = slice(5 + N_TARGETS, 5 + 2 * N_TARGETS)
N_COLS = 5 + 2 * N_TARGETS


def decisions(prob: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    return (prob >= np.asarray(thresholds)[None, :]).astype(float)


def term_matrix(pred: np.ndarray, labels: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Per-study columns from which every estimator is a ratio of sums."""
    obs = (mask > 0)
    wrong = (pred != labels) & obs
    n_obs = obs.sum(axis=1).astype(float)
    n_wrong = wrong.sum(axis=1).astype(float)
    T = np.empty((len(pred), N_COLS), dtype=float)
    T[:, COL_ONE] = 1.0
    T[:, COL_EVAL] = (n_obs > 0).astype(float)
    T[:, COL_EORIG] = n_wrong / np.maximum(n_obs, 1.0)
    T[:, COL_NWRONG] = n_wrong
    T[:, COL_NOBS] = n_obs
    T[:, COL_WRONG_J] = wrong.astype(float)
    T[:, COL_OBS_J] = obs.astype(float)
    return T


def _ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)


def risks_from_sums(acc_sums: np.ndarray) -> dict[str, np.ndarray]:
    """Estimators from sums of the term matrix over accepted studies.

    ``acc_sums`` has the term columns on its last axis and any leading shape
    (for example replicates).
    """
    s = np.asarray(acc_sums, dtype=float)
    out = {
        "original": _ratio(s[..., COL_EORIG], s[..., COL_ONE]),
        "evaluable_study": _ratio(s[..., COL_EORIG], s[..., COL_EVAL]),
        "cell_micro": _ratio(s[..., COL_NWRONG], s[..., COL_NOBS]),
    }
    per_j = _ratio(s[..., COL_WRONG_J], s[..., COL_OBS_J])
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out["pathology_macro"] = np.nanmean(per_j, axis=-1) if per_j.size else per_j
    for j in range(N_TARGETS):
        out[f"pathology_{j}"] = per_j[..., j]
    return out


@dataclass
class PolicyEval:
    """One model x condition x site under one label set and one policy."""
    terms: np.ndarray        # (n, N_COLS)
    accepted: np.ndarray     # (n,) bool

    def sums(self, weights: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        """(sums over accepted, sums over all) of the term columns."""
        w = np.ones(len(self.terms)) if weights is None else weights
        wa = w * self.accepted
        return wa @ self.terms, w @ self.terms


def summarise(pe: PolicyEval) -> dict[str, float]:
    acc, allv = pe.sums()
    r = risks_from_sums(acc)
    full = risks_from_sums(allv)
    n = allv[COL_ONE]
    n_eval = allv[COL_EVAL]
    out = {
        "studies": int(n), "evaluable_studies": int(n_eval),
        "accepted_studies": int(acc[COL_ONE]),
        "accepted_evaluable_studies": int(acc[COL_EVAL]),
        "coverage_all": float(acc[COL_ONE] / n) if n else float("nan"),
        "coverage_evaluable": float(acc[COL_EVAL] / n_eval) if n_eval else float("nan"),
        "labelled_cells_accepted": int(acc[COL_NOBS]),
        "labelled_cells_all": int(allv[COL_NOBS]),
        "evaluable_fraction_accepted": float(acc[COL_EVAL] / acc[COL_ONE]) if acc[COL_ONE] else float("nan"),
        "evaluable_fraction_all": float(n_eval / n) if n else float("nan"),
    }
    for k in ESTIMATORS:
        out[f"risk_{k}"] = float(r[k])
        out[f"full_coverage_{k}"] = float(full[k])
    for j in range(N_TARGETS):
        out[f"risk_pathology_{j}"] = float(r[f"pathology_{j}"])
    return out
