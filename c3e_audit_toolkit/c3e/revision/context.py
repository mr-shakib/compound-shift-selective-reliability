"""Prediction change versus selection change under context interventions.

A context intervention changes a model's probabilities, hence both its
decisions on every study and which studies its frozen cutoff accepts. The
selective-risk difference R_c(A_c) - R_0(A_0) is the effect on the deployed
policy and mixes the two. Writing R_x(A) for the risk of condition-x
predictions over acceptance set A:

  order 1:  [R_c(A_0) - R_0(A_0)]   prediction change on the fixed C0 set
          + [R_c(A_c) - R_c(A_0)]   selection change
  order 2:  [R_0(A_c) - R_0(A_0)]   selection change
          + [R_c(A_c) - R_0(A_c)]   prediction change on the fixed C-c set

Both orders are reported because the split is not unique when the factors
interact. The full-cohort contrast (no abstention) is reported as the
selection-free reference. Fixed-set quantities are diagnostics: no deployed
policy evaluates intervention-c predictions on the C0 acceptance set.

All within-site and paired: one single-site draw per site, as H4 used.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .engine import ItemSet, Policy, Site, item_risk, item_terms, labels_from_raw
from .fastboot import percentile_interval, single_sums


def decompose(site: Site, policy: Policy, models=("M2", "M3", "M4"), conds=("C1", "C2"),
              estimators=("evaluable_study", "original", "cell_micro"),
              replicates: int = 2000) -> list[dict[str, Any]]:
    lab, msk = labels_from_raw(site.raw)
    items = ItemSet(site)
    acc = {}
    for m in models:
        for c in ("C0",) + tuple(conds):
            acc[(m, c)] = policy.accepted(m, site.probs[(m, c)])
    allrows = np.ones(site.n, dtype=bool)
    for m in models:
        for x in ("C0",) + tuple(conds):
            for a in ("C0",) + tuple(conds) + ("ALL",):
                A = allrows if a == "ALL" else acc[(m, a)]
                items.add(f"{m}|{x}|{a}", item_terms(site.probs[(m, x)], lab, msk,
                                                      policy.thresholds[m], A))
    W = single_sums(site.pidx, items.matrix(), replicates=replicates)
    pt = items.point_sums()
    rows = []
    for est in estimators:
        for m in models:
            for c in conds:
                def R(S, x, a):
                    return item_risk(S, items, f"{m}|{x}|{a}", est)
                terms = {
                    "policy_effect": lambda S: R(S, c, c) - R(S, "C0", "C0"),
                    "order1_prediction_on_C0_set": lambda S: R(S, c, "C0") - R(S, "C0", "C0"),
                    "order1_selection": lambda S: R(S, c, c) - R(S, c, "C0"),
                    "order2_selection": lambda S: R(S, "C0", c) - R(S, "C0", "C0"),
                    "order2_prediction_on_intervention_set": lambda S: R(S, c, c) - R(S, "C0", c),
                    "full_cohort_prediction_effect": lambda S: R(S, c, "ALL") - R(S, "C0", "ALL"),
                }
                n_overlap = int((acc[(m, c)] & acc[(m, "C0")]).sum())
                for name, f in terms.items():
                    lo, hi = percentile_interval(f(W))
                    rows.append({"site": site.name, "model": m, "condition": c,
                                 "estimator": est, "term": name, "estimate": float(f(pt)),
                                 "ci_low": lo, "ci_high": hi,
                                 "accepted_C0": int(acc[(m, "C0")].sum()),
                                 "accepted_intervention": int(acc[(m, c)].sum()),
                                 "accepted_both": n_overlap,
                                 "jaccard_acceptance": n_overlap / int((acc[(m, c)] | acc[(m, "C0")]).sum())})
    return rows
