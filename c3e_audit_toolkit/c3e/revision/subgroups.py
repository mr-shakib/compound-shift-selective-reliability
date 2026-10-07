"""Stratified analyses (exploratory; Revision R1).

* View (AP-only vs PA-only studies; mixed-view studies excluded) at both
  sites. The SAP (2026-07-18) lists AP/PA as a mandatory sensitivity; it was
  not run before the external results were seen, so it is reported here as
  post hoc. View is not randomised and differs in case mix (portable AP
  films are typical of inpatients), so differences are not causal.
* External-site demographics (sex, age band, race, insurance) with the
  registry's subgroup metrics MET016 (max - min coverage across groups) and
  MET017 (worst-group selective risk). No source-site demographics are
  available in the acquired MIMIC-CXR-JPG metadata (they live in MIMIC-IV,
  which was not acquired), so no cross-site subgroup contrast is attempted.

Domain estimation: every stratum statistic uses the same patient-clustered
draw as the unstratified analysis, with out-of-stratum studies weighted zero.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .engine import ItemSet, Policy, Site, item_coverage, item_risk, item_terms, labels_from_raw
from .fastboot import joint_sums, percentile_interval, single_sums


def view_strata(site: Site) -> dict[str, np.ndarray]:
    v = site.cohort["views"].astype(str)
    return {"AP_only": (v == "AP").to_numpy(), "PA_only": (v == "PA").to_numpy()}


def age_band(a: pd.Series) -> pd.Series:
    b = pd.cut(pd.to_numeric(a, errors="coerce"), [-1, 39, 64, 79, 200],
               labels=["<40", "40-64", "65-79", ">=80"])
    return b.astype(object).where(b.notna(), "Unknown").astype(str)


def demographic_strata(site: Site) -> dict[str, dict[str, np.ndarray]]:
    c = site.cohort
    out: dict[str, dict[str, np.ndarray]] = {}
    for col in ("sex", "race", "insurance_type"):
        vals = c[col].fillna("Unknown").astype(str)
        out[col] = {k: (vals == k).to_numpy() for k in sorted(vals.unique())}
    ab = age_band(c["age"])
    out["age_band"] = {k: (ab == k).to_numpy() for k in sorted(ab.unique())}
    return out


def _stratum_items(site: Site, policy: Policy, models, strata: dict[str, np.ndarray],
                   cond: str = "C0") -> ItemSet:
    lab, msk = labels_from_raw(site.raw)
    items = ItemSet(site)
    for m in models:
        p = site.probs[(m, cond)]
        base = item_terms(p, lab, msk, policy.thresholds[m], policy.accepted(m, p))
        for k, sel in strata.items():
            items.add(f"{m}|{k}", base * sel[:, None])
    return items


def view_analysis(src: Site, ext: Site, policy: Policy, models=("M1", "M2", "M3", "M4"),
                  estimator: str = "evaluable_study", replicates: int = 2000) -> list[dict[str, Any]]:
    Ss, Se = view_strata(src), view_strata(ext)
    Is, Ie = _stratum_items(src, policy, models, Ss), _stratum_items(ext, policy, models, Se)
    Bs, Be = joint_sums(src.pidx, Is.matrix(), ext.pidx, Ie.matrix(), replicates=replicates)
    ps, pe = Is.point_sums(), Ie.point_sums()
    rows = []
    for m in models:
        for k in Ss:
            n = f"{m}|{k}"
            d = item_risk(Be, Ie, n, estimator) - item_risk(Bs, Is, n, estimator)
            lo, hi = percentile_interval(d)
            rows.append({"stratum": k, "model": m, "estimator": estimator,
                         "studies_source": int(Ss[k].sum()), "studies_external": int(Se[k].sum()),
                         "coverage_source": float(item_coverage(ps, Is, n)),
                         "coverage_external": float(item_coverage(pe, Ie, n)),
                         "risk_source": float(item_risk(ps, Is, n, estimator)),
                         "risk_external": float(item_risk(pe, Ie, n, estimator)),
                         "transfer_gap": float(item_risk(pe, Ie, n, estimator) - item_risk(ps, Is, n, estimator)),
                         "ci_low": lo, "ci_high": hi})
    return rows


def demographic_analysis(ext: Site, policy: Policy, models=("M1", "M2", "M3", "M4"),
                         estimator: str = "evaluable_study", replicates: int = 2000,
                         min_studies: int = 500) -> dict[str, list[dict[str, Any]]]:
    groups = demographic_strata(ext)
    rows, disparity = [], []
    for var, strata in groups.items():
        strata = {k: v for k, v in strata.items() if v.sum() >= min_studies}
        items = _stratum_items(ext, policy, models, strata)
        W = single_sums(ext.pidx, items.matrix(), replicates=replicates)
        pt = items.point_sums()
        for m in models:
            covs, risks = {}, {}
            for k in strata:
                n = f"{m}|{k}"
                cv, rk = item_coverage(W, items, n), item_risk(W, items, n, estimator)
                covs[k], risks[k] = cv, rk
                clo, chi = percentile_interval(cv)
                rlo, rhi = percentile_interval(rk)
                rows.append({"variable": var, "group": k, "model": m, "estimator": estimator,
                             "studies": int(strata[k].sum()),
                             "coverage": float(item_coverage(pt, items, n)),
                             "coverage_ci_low": clo, "coverage_ci_high": chi,
                             "selective_risk": float(item_risk(pt, items, n, estimator)),
                             "risk_ci_low": rlo, "risk_ci_high": rhi})
            cov_mat = np.column_stack([covs[k] for k in strata])
            risk_mat = np.column_stack([risks[k] for k in strata])
            ptc = np.array([item_coverage(pt, items, f"{m}|{k}") for k in strata])
            ptr = np.array([item_risk(pt, items, f"{m}|{k}", estimator) for k in strata])
            d_lo, d_hi = percentile_interval(cov_mat.max(1) - cov_mat.min(1))
            w_lo, w_hi = percentile_interval(risk_mat.max(1))
            disparity.append({"variable": var, "model": m, "groups": list(strata),
                              "MET016_coverage_disparity": float(ptc.max() - ptc.min()),
                              "MET016_ci_low": d_lo, "MET016_ci_high": d_hi,
                              "MET017_worst_group_risk": float(ptr.max()),
                              "MET017_worst_group": list(strata)[int(np.argmax(ptr))],
                              "MET017_ci_low": w_lo, "MET017_ci_high": w_hi,
                              "note": "max-of-groups statistics are upward-biased in small groups; "
                                      f"groups with fewer than {min_studies} studies omitted"})
    return {"rows": rows, "disparity": disparity}
