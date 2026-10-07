"""Every Stage 10 contrast, under every estimator, with one verdict function.

Contrasts (risk R at the frozen 80% cutoff unless stated):

  H1(m)        R_ext(m,C0) - R_src(m,C0)                                (MET003)
  H2(m,C1)     [R_ext(m,C1)-R_ext(m,C0)] - [R_src(m,C1)-R_src(m,C0)]   (MET006; registered)
  H2(m,C2)     same with C2                       (computed by Stage 10; NOT registered)
  H3(m)        H1(m) - H1(M1)       (Stage 10 operationalisation; registered estimand
                                     is MET006-based and equals H2(m,C1), see verdict.py)
  H4(s,m)      R_s(m,C2) - R_s(m,C1), paired within site                (MET001; secondary)
  P(s,m,c)     R_s(m,c) - R_s(m,C0), paired within site                 (MET005)
  CovGap(m,c)  coverage_ext - coverage_src                              (MET004)

Cross-site contrasts use the joint (independent within-site) draw; within-site
contrasts use the single-site paired draw, exactly as Stage 10 did.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..calibration.policy import TARGETS
from .engine import (ItemSet, Policy, Site, item_coverage, item_risk, item_terms,
                     labels_from_raw)
from .estimators import ESTIMATORS, N_COLS
from .fastboot import (bootstrap_p_two_sided, joint_sums, percentile_interval,
                       single_sums)
from .verdict import REGISTERED_RULES, STAGE10_H3_MATERIALITY, verdict

CONDS = ("C0", "C1", "C2")


def build_items(site: Site, policy: Policy, models, *, labels=None, mask=None,
                variant: str = "primary") -> ItemSet:
    if labels is None:
        labels, mask = labels_from_raw(site.raw, variant)
    items = ItemSet(site)
    for m in models:
        for c in CONDS:
            p = site.probs[(m, c)]
            items.add(f"{m}|{c}", item_terms(p, labels, mask, policy.thresholds[m],
                                             policy.accepted(m, p)))
    return items


#: Bonferroni level for the six registered confirmatory contrasts
#: (H1, H2-C1 and H3 for M3 and M4). Not prespecified; a sensitivity only.
BONFERRONI_K = 6


def _summ(draws: np.ndarray, point: float) -> dict[str, float]:
    lo, hi = percentile_interval(draws)
    blo, bhi = percentile_interval(draws, 1.0 - 0.05 / BONFERRONI_K)
    return {"point_estimate": float(point), "ci_low": lo, "ci_high": hi,
            "ci_low_bonferroni6": blo, "ci_high_bonferroni6": bhi,
            "p_two_sided_bootstrap": bootstrap_p_two_sided(draws)}


def run_family(src: Site, ext: Site, policy: Policy, *, models=("M1", "M2", "M3", "M4"),
               multimodal=("M3", "M4"), variant: str = "primary",
               labels_src=None, mask_src=None, labels_ext=None, mask_ext=None,
               estimators=ESTIMATORS, replicates: int = 2000) -> dict[str, Any]:
    I_s = build_items(src, policy, models, labels=labels_src, mask=mask_src, variant=variant)
    I_e = build_items(ext, policy, models, labels=labels_ext, mask=mask_ext, variant=variant)
    P_s, P_e = I_s.matrix(), I_e.matrix()
    Bs, Be = joint_sums(src.pidx, P_s, ext.pidx, P_e, replicates=replicates)
    Ws = single_sums(src.pidx, P_s, replicates=replicates)
    We = single_sums(ext.pidx, P_e, replicates=replicates)
    ps, pe = I_s.point_sums(), I_e.point_sums()

    rows: list[dict[str, Any]] = []
    levels: list[dict[str, Any]] = []

    def R(sums, items, m, c, est):
        return item_risk(sums, items, f"{m}|{c}", est)

    for est in estimators:
        for site_name, items, pt, W in (("source", I_s, ps, Ws), ("external", I_e, pe, We)):
            for m in models:
                for c in CONDS:
                    lo, hi = percentile_interval(R(W, items, m, c, est))
                    levels.append({"estimator": est, "site": site_name, "model": m,
                                   "condition": c, "risk": float(R(pt, items, m, c, est)),
                                   "ci_low": lo, "ci_high": hi,
                                   "coverage_all": float(item_coverage(pt, items, f"{m}|{c}")),
                                   "coverage_evaluable": float(
                                       pt[items.slice_of(f"{m}|{c}")][1]
                                       / pt[items.slice_of(f"{m}|{c}")][N_COLS + 1])})

        def add(h, model, contrast, draws, point, site=None, registered=True, mat_override=None):
            s = _summ(draws, point)
            rule = REGISTERED_RULES[h]
            v = verdict(s["point_estimate"], s["ci_low"], s["ci_high"],
                        direction=rule["direction"],
                        materiality=rule["materiality"] if mat_override is None else mat_override)
            row = {"estimator": est, "hypothesis": h, "model": model, "site": site or "",
                   "contrast": contrast, "registered_contrast": registered,
                   "status": rule["status"] if registered else "not_registered",
                   **s, **{k: v[k] for k in ("ci_side", "reaches_materiality",
                                             "interval_excludes_materiality",
                                             "within_materiality_bounds", "verdict")},
                   "materiality_applied": v["materiality"]}
            if h == "H3":
                v2 = verdict(s["point_estimate"], s["ci_low"], s["ci_high"],
                             direction="greater", materiality=STAGE10_H3_MATERIALITY)
                row["verdict_with_stage10_materiality"] = v2["verdict"]
            rows.append(row)

        for m in models:
            d = R(Be, I_e, m, "C0", est) - R(Bs, I_s, m, "C0", est)
            p = R(pe, I_e, m, "C0", est) - R(ps, I_s, m, "C0", est)
            add("H1", m, "external C0 - source C0", d, p, registered=m in multimodal)
        for m in multimodal:
            for c in ("C1", "C2"):
                f = lambda S_s, S_e: ((R(S_e, I_e, m, c, est) - R(S_e, I_e, m, "C0", est))
                                      - (R(S_s, I_s, m, c, est) - R(S_s, I_s, m, "C0", est)))
                add("H2", m, f"interaction {c}", f(Bs, Be), f(ps, pe), registered=(c == "C1"))
        for m in multimodal:
            f = lambda S_s, S_e: ((R(S_e, I_e, m, "C0", est) - R(S_s, I_s, m, "C0", est))
                                  - (R(S_e, I_e, "M1", "C0", est) - R(S_s, I_s, "M1", "C0", est)))
            add("H3", m, f"transfer gap {m} - transfer gap M1", f(Bs, Be), f(ps, pe),
                registered=False)
        for site_name, items, pt, W in (("source", I_s, ps, Ws), ("external", I_e, pe, We)):
            for m in multimodal:
                f = lambda S: R(S, items, m, "C2", est) - R(S, items, m, "C1", est)
                add("H4", m, "C2 - C1", f(W), f(pt), site=site_name)

    # Coverage transport gap (estimator-free), joint draw.
    cov_rows = []
    for m in models:
        for c in CONDS:
            d = item_coverage(Be, I_e, f"{m}|{c}") - item_coverage(Bs, I_s, f"{m}|{c}")
            p = item_coverage(pe, I_e, f"{m}|{c}") - item_coverage(ps, I_s, f"{m}|{c}")
            lo, hi = percentile_interval(d)
            cov_rows.append({"model": m, "condition": c,
                             "coverage_source": float(item_coverage(ps, I_s, f"{m}|{c}")),
                             "coverage_external": float(item_coverage(pe, I_e, f"{m}|{c}")),
                             "coverage_gap": float(p), "ci_low": lo, "ci_high": hi})
    return {"contrasts": rows, "levels": levels, "coverage_gap": cov_rows,
            "variant": variant, "policy": policy.name,
            "n_source": src.n, "n_external": ext.n}
