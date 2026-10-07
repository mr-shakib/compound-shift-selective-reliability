"""What the primary endpoint measures: label composition at both sites.

Reports, per site x label source x pathology, the counts of positive,
negative, uncertain and unmentioned cells over the evaluation cohort and over
the studies each model accepts at the frozen 80% cutoff; the fraction of
studies with no labelled cell at all; and, on cells labelled under both report
scopes, how often the impression and findings labels agree.

Aggregates only. Counts are of cells and studies, never of identifiers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..calibration.policy import TARGETS
from .engine import Site, frozen_policy, load_site


def _counts(raw: np.ndarray, rows: np.ndarray | None = None) -> list[dict[str, Any]]:
    r = raw if rows is None else raw[rows]
    out = []
    for j, t in enumerate(TARGETS):
        v = r[:, j]
        pos, neg = int((v == 1).sum()), int((v == 0).sum())
        unc, unm = int((v == -1).sum()), int(np.isnan(v).sum())
        n = len(v)
        out.append({"pathology": t, "studies": n, "positive": pos, "negative": neg,
                    "uncertain": unc, "unmentioned": unm,
                    "labelled_fraction": (pos + neg) / n if n else float("nan"),
                    "positive_rate_among_labelled": pos / (pos + neg) if pos + neg else float("nan"),
                    "positive_rate_unmentioned_as_negative": pos / (n - unc) if n - unc else float("nan")})
    return out


def _study_summary(raw: np.ndarray, rows: np.ndarray | None = None) -> dict[str, Any]:
    r = raw if rows is None else raw[rows]
    lab = np.isin(r, [0.0, 1.0])
    n = len(r)
    return {"studies": n,
            "studies_with_no_labelled_cell": int((~lab.any(1)).sum()),
            "fraction_no_labelled_cell": float((~lab.any(1)).mean()) if n else float("nan"),
            "labelled_cell_density": float(lab.mean()) if n else float("nan"),
            "positive_rate_among_labelled": float((r[lab] == 1).mean()) if lab.any() else float("nan"),
            "studies_with_any_uncertain": int((r == -1).any(1).sum()),
            "mean_labelled_cells_per_evaluable_study": float(lab.sum(1)[lab.any(1)].mean())
            if lab.any() else float("nan")}


def audit(root: Path) -> dict[str, Any]:
    root = Path(root)
    out: dict[str, Any] = {"by_pathology": [], "by_study": [], "agreement": []}
    pol = frozen_policy(root, "impression")
    sites = {(s, ls): load_site(root, s, label_source=ls)
             for s in ("source", "external") for ls in ("impression", "findings")}
    for (s, ls), site in sites.items():
        scopes = [("all_eligible", None)]
        if ls == "impression":
            for m in ("M1", "M2", "M3", "M4"):
                scopes.append((f"accepted_{m}_C0",
                               pol.accepted(m, site.probs[(m, "C0")])))
        for scope, rows in scopes:
            for row in _counts(site.raw, rows):
                out["by_pathology"].append({"site": s, "label_source": ls, "scope": scope, **row})
            out["by_study"].append({"site": s, "label_source": ls, "scope": scope,
                                    **_study_summary(site.raw, rows)})

    # Agreement on cells labelled under both scopes, within the primary cohort.
    for s in ("source", "external"):
        imp = sites[(s, "impression")]
        fin = sites[(s, "findings")]
        key = "study_id" if s == "source" else "study_key"
        f_raw = fin.cohort.set_index(key)[TARGETS].reindex(imp.cohort[key]).to_numpy(dtype=float)
        studies_with_findings = int(np.isin(f_raw, [0.0, 1.0, -1.0]).any(1).sum())
        for j, t in enumerate(TARGETS):
            a, b = imp.raw[:, j], f_raw[:, j]
            both = np.isin(a, [0, 1]) & np.isin(b, [0, 1])
            n = int(both.sum())
            out["agreement"].append({
                "site": s, "pathology": t, "cells_labelled_both": n,
                "agreement": float((a[both] == b[both]).mean()) if n else float("nan"),
                "imp_pos_find_neg": int(((a == 1) & (b == 0)).sum()),
                "imp_neg_find_pos": int(((a == 0) & (b == 1)).sum()),
                "labelled_impression_only": int((np.isin(a, [0, 1]) & ~np.isin(b, [0, 1])).sum()),
                "labelled_findings_only": int((~np.isin(a, [0, 1]) & np.isin(b, [0, 1])).sum()),
                "studies_in_cohort": int(len(a)),
                "studies_with_any_findings_label_value": studies_with_findings})
    return out
