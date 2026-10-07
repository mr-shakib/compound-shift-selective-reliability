"""Diagnostics of the frozen selective policy (post hoc; Revision R1).

* Risk-coverage curves at each site, with the frozen operating point marked.
* AURC (registered MET008, secondary) and AUGRC (registered MET007,
  "primary_threshold_free"; never reported in the original analysis), each
  over evaluable studies, with external-minus-source contrasts and
  patient-clustered intervals from the joint draw.
* Failure-detection AUROC (registered MET009): does the confidence score rank
  studies with any error below studies with none? And, per pathology, does
  the per-cell score rank the correctness of the *thresholded decision*?
  The frozen per-cell score |2p - 1| is centred at 0.5, while decisions are
  made at pathology-specific thresholds t_j; the threshold-centred margin
  |logit p - logit t_j| is reported alongside as the decision-aware analogue.
* Per-pathology operating characteristics (TP, FP, TN, FN, sensitivity,
  specificity) among accepted studies and over the full cohort.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..calibration.policy import TARGETS, study_confidence
from .engine import Policy, Site, labels_from_raw
from .estimators import decisions
from .fastboot import PatientIndex, percentile_interval

EPS = 1e-6


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def threshold_margin(probs: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """Per-cell decision-aware margin |logit p - logit t|; larger is more confident."""
    return np.abs(logit(probs) - logit(np.asarray(thresholds)[None, :]))


def auroc(score: np.ndarray, positive: np.ndarray) -> float:
    """Mann-Whitney AUROC with average ranks for ties; P(score_pos > score_neg)."""
    from scipy.stats import rankdata
    s = np.asarray(score, dtype=float)
    y = np.asarray(positive, dtype=bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    ranks = rankdata(s)
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def rc_curve(conf: np.ndarray, err: np.ndarray, weights: np.ndarray | None = None,
             grid: np.ndarray | None = None, order: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Risk-coverage over evaluable studies (err finite), most confident first.

    AURC is the coverage-weighted mean of selective risk along the ranked
    curve; AUGRC (Traub et al., 2024) integrates the generalised risk
    (accepted errors / all evaluable studies). Pass ``order`` (indices of the
    evaluable studies sorted by descending confidence) to avoid re-sorting.
    """
    if order is None:
        ok = np.flatnonzero(np.isfinite(err))
        order = ok[np.argsort(-conf[ok], kind="mergesort")]
    e = err[order]
    w = np.ones(len(order)) if weights is None else weights[order]
    cw, ce = np.cumsum(w), np.cumsum(w * e)
    tot = cw[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        risk = np.where(cw > 0, ce / np.where(cw > 0, cw, 1), 0.0)
    aurc = float(np.sum(w * risk) / tot)
    augrc = float(np.sum(w * (ce / tot)) / tot)
    out = {"aurc": aurc, "augrc": augrc}
    if grid is not None:
        cov = cw / tot
        idx = np.clip(np.searchsorted(cov, grid, side="left"), 0, len(cov) - 1)
        out["coverage"], out["risk"] = grid, risk[idx]
    return out


def ranked(conf: np.ndarray, err: np.ndarray) -> np.ndarray:
    ok = np.flatnonzero(np.isfinite(err))
    return ok[np.argsort(-conf[ok], kind="mergesort")]


def study_error(pred: np.ndarray, labels: np.ndarray, mask: np.ndarray) -> np.ndarray:
    obs = mask > 0
    n = obs.sum(1)
    w = ((pred != labels) & obs).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, w / np.where(n > 0, n, 1), np.nan)


def threshold_free(src: Site, ext: Site, policy: Policy, models=("M1", "M2", "M3", "M4"),
                   cond: str = "C0", replicates: int = 2000, seed: int = 20260718,
                   score: str = "frozen") -> list[dict[str, Any]]:
    """AURC and AUGRC at each site and their external-minus-source contrast."""
    rows = []
    ls, ms = labels_from_raw(src.raw)
    le, me = labels_from_raw(ext.raw)
    prep = {}
    for m in models:
        for tag, site, lab, msk in (("source", src, ls, ms), ("external", ext, le, me)):
            p = site.probs[(m, cond)]
            pred = decisions(p, policy.thresholds[m])
            conf = (study_confidence(p, "minimum") if score == "frozen"
                    else threshold_margin(p, policy.thresholds[m]).min(1))
            err = study_error(pred, lab, msk)
            prep[(m, tag)] = (conf, err, ranked(conf, err))
    # Joint draw identical to Stage 10's independent bootstrap.
    rng = np.random.default_rng(seed)
    ps, pe = PatientIndex(src.cohort["patient"].to_numpy().astype(str)), \
        PatientIndex(ext.cohort["patient"].to_numpy().astype(str))
    draws = {k: np.empty(replicates) for m in models for k in
             [(m, "aurc"), (m, "augrc")]}
    for b in range(replicates):
        ws = np.bincount(rng.integers(0, ps.n, ps.n), minlength=ps.n)[ps.inverse].astype(float)
        we = np.bincount(rng.integers(0, pe.n, pe.n), minlength=pe.n)[pe.inverse].astype(float)
        for m in models:
            cs, es, os_ = prep[(m, "source")]
            ce_, ee, oe = prep[(m, "external")]
            a = rc_curve(cs, es, weights=ws, order=os_)
            e = rc_curve(ce_, ee, weights=we, order=oe)
            draws[(m, "aurc")][b] = e["aurc"] - a["aurc"]
            draws[(m, "augrc")][b] = e["augrc"] - a["augrc"]
    for m in models:
        a = rc_curve(*prep[(m, "source")][:2])
        e = rc_curve(*prep[(m, "external")][:2])
        for k in ("aurc", "augrc"):
            lo, hi = percentile_interval(draws[(m, k)])
            rows.append({"model": m, "condition": cond, "metric": k, "score": score,
                         "source": a[k], "external": e[k], "difference": e[k] - a[k],
                         "ci_low": lo, "ci_high": hi, "population": "evaluable studies"})
    return rows


def curves(site: Site, policy: Policy, models=("M1", "M2", "M3", "M4"), conds=("C0",),
           grid=np.linspace(0.05, 1.0, 96)) -> list[dict[str, Any]]:
    lab, msk = labels_from_raw(site.raw)
    rows = []
    for m in models:
        for c in conds:
            p = site.probs[(m, c)]
            pred = decisions(p, policy.thresholds[m])
            err = study_error(pred, lab, msk)
            for score in ("frozen", "threshold_margin"):
                conf = (study_confidence(p, "minimum") if score == "frozen"
                        else threshold_margin(p, policy.thresholds[m]).min(1))
                rc = rc_curve(conf, err, grid=grid)
                for cv, rk in zip(rc["coverage"], rc["risk"]):
                    rows.append({"site": site.name, "model": m, "condition": c, "score": score,
                                 "coverage_evaluable": float(cv), "risk_evaluable_study": float(rk)})
    return rows


def failure_detection(site: Site, policy: Policy, models=("M1", "M2", "M3", "M4"),
                      cond: str = "C0") -> list[dict[str, Any]]:
    lab, msk = labels_from_raw(site.raw)
    rows = []
    for m in models:
        p = site.probs[(m, cond)]
        t = policy.thresholds[m]
        pred = decisions(p, t)
        err = study_error(pred, lab, msk)
        ok = np.isfinite(err)
        for score, conf in (("frozen_min_abs_2p_minus_1", study_confidence(p, "minimum")),
                            ("min_threshold_margin", threshold_margin(p, t).min(1))):
            rows.append({"site": site.name, "model": m, "condition": cond, "level": "study",
                         "pathology": "all", "score": score,
                         "auroc_correct_vs_any_error": auroc(conf[ok], err[ok] == 0),
                         "n": int(ok.sum()), "error_prevalence": float((err[ok] > 0).mean())})
        per_frozen = np.abs(2 * p - 1)
        per_margin = threshold_margin(p, t)
        for j, name in enumerate(TARGETS):
            obs = msk[:, j] > 0
            correct = (pred[obs, j] == lab[obs, j])
            for score, sc in (("abs_2p_minus_1", per_frozen[obs, j]),
                              ("threshold_margin", per_margin[obs, j])):
                rows.append({"site": site.name, "model": m, "condition": cond, "level": "cell",
                             "pathology": name, "score": score,
                             "auroc_correct_vs_any_error": auroc(sc, correct),
                             "n": int(obs.sum()), "error_prevalence": float(1 - correct.mean())
                             if obs.any() else float("nan")})
    return rows


def operating_characteristics(site: Site, policy: Policy, models=("M1", "M2", "M3", "M4"),
                              cond: str = "C0", variant: str = "primary") -> list[dict[str, Any]]:
    lab, msk = labels_from_raw(site.raw, variant)
    rows = []
    for m in models:
        p = site.probs[(m, cond)]
        pred = decisions(p, policy.thresholds[m])
        acc = policy.accepted(m, p)
        for scope, rsel in (("accepted", acc), ("full_cohort", np.ones(len(p), bool))):
            for j, name in enumerate(TARGETS):
                o = (msk[:, j] > 0) & rsel
                y, yh = lab[o, j], pred[o, j]
                tp, fp = int(((y == 1) & (yh == 1)).sum()), int(((y == 0) & (yh == 1)).sum())
                tn, fn = int(((y == 0) & (yh == 0)).sum()), int(((y == 1) & (yh == 0)).sum())
                rows.append({"site": site.name, "model": m, "condition": cond, "scope": scope,
                             "label_variant": variant,
                             "pathology": name, "threshold": float(policy.thresholds[m][j]),
                             "tp": tp, "fp": fp, "tn": tn, "fn": fn,
                             "sensitivity": tp / (tp + fn) if tp + fn else float("nan"),
                             "specificity": tn / (tn + fp) if tn + fp else float("nan"),
                             "error_rate_labelled": (fp + fn) / max(tp + fp + tn + fn, 1),
                             "decided_positive_rate_in_scope":
                                 float(pred[rsel, j].mean()) if rsel.any() else float("nan")})
    return rows
