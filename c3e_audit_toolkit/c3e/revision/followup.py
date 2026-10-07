"""Analyses of the GPU follow-up outputs (exploratory; Revision R1).

* Additional C2 donor permutations (seeds other than the frozen 20260718):
  within-site H4 (C2 - C1) and the C2 penalty (C2 - C0) recomputed with the
  alternative C2 realisation, everything else unchanged.
* M2 and M3 under training seed 20260719: thresholds and cutoffs re-selected
  on the calibration tier by the frozen rule (exactly as Stage 7 did for the
  M1/M4 replicate), then the full contrast family with the replicate M1, M2,
  M3 and M4.

Each analysis runs only if its inputs exist; otherwise it is reported as
pending, never estimated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..calibration.policy import (TARGETS, abstention_threshold_for_coverage,
                                  balanced_accuracy_threshold, study_confidence)
from .engine import ItemSet, Policy, Site, frozen_policy, item_risk, item_terms, labels_from_raw, load_site
from .fastboot import percentile_interval, single_sums
from .hypotheses import run_family
from .inference import REV_CACHE, rev_cache_path
from .verdict import verdict

C2_SEEDS = (20260719, 20260720)
REP = 20260719


def _aligned(site: Site, path: Path) -> np.ndarray:
    z = np.load(path)
    key = "study_id" if site.name == "source" else "study_key"
    order = site.cohort[key].astype(str).to_numpy()
    pos = {k: i for i, k in enumerate(z["studies"].astype(str))}
    if len(pos) != len(order) or any(k not in pos for k in order):
        raise RuntimeError(f"{path.name}: study keys do not match the cohort")
    idx = np.array([pos[k] for k in order])
    if not np.array_equal(z["patients"].astype(str)[idx], site.cohort["patient"].astype(str).to_numpy()):
        raise RuntimeError(f"{path.name}: patients misaligned")
    return z["probabilities"][idx].astype(float)


def c2_permutations(root: Path, replicates: int = 2000) -> list[dict[str, Any]]:
    root = Path(root)
    pol = frozen_policy(root)
    rows = []
    for site_name in ("source", "external"):
        site = load_site(root, site_name)
        lab, msk = labels_from_raw(site.raw)
        tier = "prespecified_eval" if site_name == "source" else "external"
        for seed in (20260718,) + (C2_SEEDS if site_name == "source" else C2_SEEDS[:1]):
            # Each model is analysed as soon as its cache exists; a model whose
            # cache is missing is reported as pending, never estimated.
            probs, models = {}, []
            for m in ("M2", "M3", "M4"):
                if seed == 20260718:
                    probs[m] = site.probs[(m, "C2")]
                    models.append(m)
                    continue
                p = rev_cache_path(root, site=site_name, tier=tier, model=m, cond="C2", train_seed=None,
                                   c2_seed=seed)
                if not p.exists():
                    rows.append({"site": site_name, "c2_seed": seed, "status": "pending", "model": m})
                    continue
                # The external revision cohort lacks one image lost after the
                # primary run; compare on the common studies only.
                with np.load(p) as zz:
                    partial = site_name == "external" and len(zz["studies"]) != site.n
                probs[m] = _aligned_common(site, p) if partial else _aligned(site, p)
                models.append(m)
            if not models:
                continue
            items = ItemSet(site)
            keep = np.ones(site.n, bool)
            for m in models:
                if np.isnan(probs[m]).any():
                    keep &= ~np.isnan(probs[m]).any(1)
            for m in models:
                for c, p in (("C0", site.probs[(m, "C0")]), ("C1", site.probs[(m, "C1")]), ("C2", np.nan_to_num(probs[m]))):
                    t = item_terms(p, lab, msk, pol.thresholds[m], pol.accepted(m, p))
                    items.add(f"{m}|{c}", t * keep[:, None])
            W = single_sums(site.pidx, items.matrix(), replicates=replicates)
            pt = items.point_sums()
            for est in ("evaluable_study", "original"):
                for m in models:
                    for name, a, b in (("H4 (C2 - C1)", "C2", "C1"), ("C2 penalty (C2 - C0)", "C2", "C0")):
                        d = item_risk(W, items, f"{m}|{a}", est) - item_risk(W, items, f"{m}|{b}", est)
                        p_ = item_risk(pt, items, f"{m}|{a}", est) - item_risk(pt, items, f"{m}|{b}", est)
                        lo, hi = percentile_interval(d)
                        v = verdict(p_, lo, hi, direction="greater_or_equal", materiality=None)
                        rows.append({"site": site_name, "c2_seed": seed, "status": "done", "estimator": est,
                                     "model": m, "contrast": name, "point_estimate": float(p_),
                                     "ci_low": lo, "ci_high": hi, "verdict": v["verdict"],
                                     "studies": int(keep.sum())})
    return rows


def _aligned_common(site: Site, path: Path) -> np.ndarray:
    z = np.load(path)
    studies, probs = z["studies"].astype(str), z["probabilities"]   # decompress once
    key = "study_id" if site.name == "source" else "study_key"
    order = site.cohort[key].astype(str).to_numpy()
    pos = {k: i for i, k in enumerate(studies)}
    idx = np.array([pos.get(k, -1) for k in order])
    out = np.full((site.n, 5), np.nan)
    out[idx >= 0] = probs[idx[idx >= 0]]
    return out


def _select(cal: dict[str, np.ndarray], coverage: float = 0.8) -> tuple[np.ndarray, float]:
    p, y, m = cal["probabilities"], cal["labels"], cal["mask"]
    thr = np.array([balanced_accuracy_threshold(p[:, j], y[:, j], m[:, j])[0] for j in range(5)])
    return thr, abstention_threshold_for_coverage(study_confidence(p, "minimum"), coverage)


def m2m3_replicate(root: Path, replicates: int = 2000) -> dict[str, Any]:
    root = Path(root)
    need = [rev_cache_path(root, site="source", tier="threshold_calibration", model=m, cond="C0",
                           train_seed=REP, c2_seed=None) for m in ("M2", "M3")]
    for site_name, tier in (("source", "prespecified_eval"), ("external", "external")):
        for m in ("M2", "M3"):
            for c in ("C0", "C1", "C2"):
                need.append(rev_cache_path(root, site=site_name, tier=tier, model=m, cond=c, train_seed=REP,
                                           c2_seed=20260718 if c == "C2" else None))
    missing = [p.name for p in need if not p.exists()]
    if missing:
        return {"status": "pending", "missing": missing}
    base = frozen_policy(root, "impression", REP)
    th, cu = dict(base.thresholds), dict(base.cutoffs)
    sel = {}
    for m in ("M2", "M3"):
        z = np.load(rev_cache_path(root, site="source", tier="threshold_calibration", model=m, cond="C0",
                                   train_seed=REP, c2_seed=None))
        th[m], cu[m] = _select({k: z[k] for k in z.files})
        sel[m] = {"thresholds": dict(zip(TARGETS, np.round(th[m], 6).tolist())), "cutoff_0.80": round(cu[m], 6)}
    pol = Policy(name="replicate_20260719_all_models", thresholds=th, cutoffs=cu)
    sites = {}
    for site_name, tier in (("source", "prespecified_eval"), ("external", "external")):
        s = load_site(root, site_name, seed=REP, models=("M1", "M4"))
        for m in ("M2", "M3"):
            for c in ("C0", "C1", "C2"):
                s.probs[(m, c)] = _aligned(s, rev_cache_path(root, site=site_name, tier=tier, model=m, cond=c,
                                                             train_seed=REP, c2_seed=20260718 if c == "C2" else None))
        sites[site_name] = s
    fam = run_family(sites["source"], sites["external"], pol, replicates=replicates,
                     estimators=("original", "evaluable_study", "cell_micro"))
    return {"status": "done", "selection": sel, "contrasts": fam["contrasts"], "levels": fam["levels"],
            "coverage_gap": fam["coverage_gap"]}
