"""Alternative selective policies (exploratory comparators; Revision R1).

The registry (experiment_registry.yaml ``uncertainty_baselines.required``)
names three baselines: raw_probability_margin (the frozen policy),
temperature_scaled_probability_margin and split_conformal_singleton_acceptance.
Only the first was implemented before the external results were seen. The
other two, and a decision-aware expected-loss score, are added here as
post hoc exploratory comparators. Everything is fitted on the source
threshold-calibration tier only (Stage 7's tier, read under
purpose="calibration") and transferred unchanged; nothing is fitted on the
source evaluation tier or on external data. The frozen primary policy is
unchanged and remains the primary analysis.

Policies (all at 80% coverage on the calibration tier):

  frozen        min_j |2 p_j - 1|, frozen cutoff; frozen thresholds t_j.
  temp_margin   per-pathology temperature T_j fitted by NLL on supervised
                calibration cells; score min_j |2 sigma(z_j / T_j) - 1|;
                frozen thresholds. (A single global temperature would leave
                the ranking, and hence the policy, unchanged.)
  expected_loss per-pathology Platt map q_j = sigma(a_j z_j + b_j) fitted on
                supervised calibration cells; with the frozen decision
                d_j = 1[p_j >= t_j], P(error_j) = q_j if d_j = 0 else 1 - q_j;
                score = -(1/5) sum_j P(error_j). Decision-aware: it ranks the
                expected Hamming loss of the decisions actually made. Its
                validity rests on the calibration map transporting, which is
                exactly what an external site may break.
  conformal     split conformal per pathology on supervised calibration cells,
                nonconformity 1 - phat(y); accept a study when all five
                prediction sets are singletons; the decision is the singleton
                label (a 0.5-centred decision, not t_j). One miscoverage level
                alpha is chosen so calibration acceptance is closest to 80%.
                Marginal coverage guarantees assume exchangeability, which
                institutional transfer does not provide.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize

from ..calibration.policy import TARGETS, abstention_threshold_for_coverage, study_confidence
from .engine import (ItemSet, Policy, Site, item_coverage, item_risk, item_terms_from_pred,
                     labels_from_raw)
from .estimators import decisions
from .fastboot import joint_sums, percentile_interval
from .inference import rev_cache_path
from .selective import auroc, logit, rc_curve, study_error

COVERAGE = 0.8


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _nll(y, logits):
    return float(np.mean(np.logaddexp(0.0, logits) - y * logits))


def fit_temperature(z: np.ndarray, y: np.ndarray) -> float:
    r = minimize(lambda lt: _nll(y, z / np.exp(lt[0])), x0=[0.0], method="Nelder-Mead")
    return float(np.exp(r.x[0]))


def fit_platt(z: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    r = minimize(lambda ab: _nll(y, ab[0] * z + ab[1]), x0=[1.0, 0.0], method="Nelder-Mead",
                 options={"xatol": 1e-6, "fatol": 1e-9, "maxiter": 4000})
    return float(r.x[0]), float(r.x[1])


def conformal_q(p: np.ndarray, y: np.ndarray, alpha: float) -> float:
    s = np.where(y == 1, 1 - p, p)
    n = len(s)
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return float(np.sort(s)[min(k, n) - 1]) if k <= n else 1.0


def conformal_sets(p: np.ndarray, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per cell: (singleton?, singleton label)."""
    has1 = (1 - p) <= q[None, :]
    has0 = p <= q[None, :]
    single = has1 ^ has0
    return single, has1.astype(float)


class Fitted:
    def __init__(self, model: str, frozen: Policy, cal: dict[str, np.ndarray]):
        self.model = model
        p, y, m = cal["probabilities"], cal["labels"], cal["mask"]
        self.t = frozen.thresholds[model]
        self.frozen_cut = frozen.cutoffs[model]
        z = logit(p)
        self.T = np.array([fit_temperature(z[m[:, j] > 0, j], y[m[:, j] > 0, j]) for j in range(5)])
        self.platt = [fit_platt(z[m[:, j] > 0, j], y[m[:, j] > 0, j]) for j in range(5)]
        self.cut_temp = abstention_threshold_for_coverage(self.score_temp(p), COVERAGE)
        self.cut_el = abstention_threshold_for_coverage(self.score_el(p), COVERAGE)
        # Conformal: one alpha for all five pathologies, calibration acceptance ~80%.
        best = None
        for a in np.round(np.arange(0.005, 0.5001, 0.0025), 4):
            q = np.array([conformal_q(p[m[:, j] > 0, j], y[m[:, j] > 0, j], a) for j in range(5)])
            acc = conformal_sets(p, q)[0].all(1).mean()
            if best is None or abs(acc - COVERAGE) < abs(best[2] - COVERAGE):
                best = (a, q, acc)
        self.alpha, self.q, self.cal_acc_conformal = best

    def score_temp(self, p):
        return np.abs(2 * _sigmoid(logit(p) / self.T[None, :]) - 1).min(1)

    def calibrated(self, p):
        z = logit(p)
        return np.column_stack([_sigmoid(a * z[:, j] + b) for j, (a, b) in enumerate(self.platt)])

    def score_el(self, p):
        q = self.calibrated(p)
        d = decisions(p, self.t)
        perr = np.where(d == 1, 1 - q, q)
        return -perr.mean(1)

    def policies(self, p) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """name -> (decisions, accepted, ranking score)."""
        d = decisions(p, self.t)
        single, lab1 = conformal_sets(p, self.q)
        conf_score = (np.abs(p - 0.5) - np.abs(self.q[None, :] - 0.5)).min(1)
        return {
            "frozen": (d, study_confidence(p, "minimum") >= self.frozen_cut,
                       study_confidence(p, "minimum")),
            "temp_margin": (d, self.score_temp(p) >= self.cut_temp, self.score_temp(p)),
            "expected_loss": (d, self.score_el(p) >= self.cut_el, self.score_el(p)),
            "conformal": (lab1, single.all(1), conf_score),
            "conformal_accept_frozen_decisions": (d, single.all(1), conf_score),
        }

    def describe(self) -> dict[str, Any]:
        return {"model": self.model, "temperature": dict(zip(TARGETS, self.T.round(4).tolist())),
                "platt_a_b": {t: [round(a, 4), round(b, 4)] for t, (a, b) in zip(TARGETS, self.platt)},
                "cutoff_temp_margin": self.cut_temp, "cutoff_expected_loss": self.cut_el,
                "conformal_alpha": float(self.alpha),
                "conformal_q": dict(zip(TARGETS, np.round(self.q, 4).tolist())),
                "conformal_calibration_acceptance": float(self.cal_acc_conformal)}


def load_cal(root: Path, model: str, train_seed: int | None = None) -> dict[str, np.ndarray]:
    z = np.load(rev_cache_path(root, site="source", tier="threshold_calibration", model=model,
                               cond="C0", train_seed=train_seed, c2_seed=None))
    return {k: z[k] for k in z.files}


def evaluate(root: Path, src: Site, ext: Site, frozen: Policy, models=("M1", "M2", "M3", "M4"),
             replicates: int = 2000) -> dict[str, Any]:
    ls, ms = labels_from_raw(src.raw)
    le, me = labels_from_raw(ext.raw)
    fits = {m: Fitted(m, frozen, load_cal(root, m)) for m in models}
    Is, Ie = ItemSet(src), ItemSet(ext)
    extra = []
    names = []
    for m in models:
        for c in ("C0", "C1", "C2"):
            Ps, Pe = fits[m].policies(src.probs[(m, c)]), fits[m].policies(ext.probs[(m, c)])
            for pol in Ps:
                n = f"{m}|{c}|{pol}"
                names.append((m, c, pol))
                Is.add(n, item_terms_from_pred(Ps[pol][0], ls, ms, Ps[pol][1]))
                Ie.add(n, item_terms_from_pred(Pe[pol][0], le, me, Pe[pol][1]))
                if c == "C0":
                    for tag, P, lab, msk in (("source", Ps, ls, ms), ("external", Pe, le, me)):
                        err = study_error(P[pol][0], lab, msk)
                        ok = np.isfinite(err)
                        rc = rc_curve(P[pol][2], err)
                        extra.append({"model": m, "policy": pol, "site": tag,
                                      "failure_auroc": auroc(P[pol][2][ok], err[ok] == 0),
                                      "aurc_evaluable": rc["aurc"], "augrc_evaluable": rc["augrc"]})
    Bs, Be = joint_sums(src.pidx, Is.matrix(), ext.pidx, Ie.matrix(), replicates=replicates)
    ps, pe = Is.point_sums(), Ie.point_sums()
    rows = []
    for (m, c, pol) in names:
        n = f"{m}|{c}|{pol}"
        row = {"model": m, "condition": c, "policy": pol,
               "coverage_source": float(item_coverage(ps, Is, n)),
               "coverage_external": float(item_coverage(pe, Ie, n))}
        for est in ("evaluable_study", "cell_micro", "original"):
            rs, re_ = item_risk(ps, Is, n, est), item_risk(pe, Ie, n, est)
            lo, hi = percentile_interval(item_risk(Be, Ie, n, est) - item_risk(Bs, Is, n, est))
            row.update({f"risk_source_{est}": float(rs), f"risk_external_{est}": float(re_),
                        f"gap_{est}": float(re_ - rs), f"gap_{est}_ci_low": lo,
                        f"gap_{est}_ci_high": hi})
        rows.append(row)
    return {"rows": rows, "ranking": extra, "fits": [f.describe() for f in fits.values()]}
