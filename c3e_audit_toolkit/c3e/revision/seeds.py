"""Training-seed replicates (post hoc; added 2026-10-14).

The original analysis and Revision R1 had two training runs (seeds 20260718
and 20260719), and the second moved the corrected transfer gaps by about
-0.04, more than their bootstrap intervals. Three further seeds
(``NEW_SEEDS``) are trained by ``scripts/run_seed_replicates.sh`` with the
frozen v0.4.2 settings on the model-train tier only, and scored on the
calibration tier, the source evaluation tier and the external site.

For each replicate seed, thresholds and cutoffs are re-selected on the
calibration tier by the frozen Stage 7 rule (as for the seed-20260719
replicate), and the full contrast family is computed exactly as for the
primary models. Nothing is fitted on external data. A seed whose caches are
incomplete is reported as pending, never estimated.

``summary`` pools the per-seed estimates of all available seeds (the primary
run, the 20260719 replicate and the new ones) into a between-seed spread,
which the evaluation bootstrap does not capture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..calibration.policy import TARGETS
from .engine import Policy, Site, labels_from_raw, load_site
from .followup import _aligned, _select
from .hypotheses import CONDS, run_family
from .inference import rev_cache_path
from .selective import auroc

NEW_SEEDS = (20260720, 20260721, 20260722)
MODELS = ("M1", "M2", "M3", "M4")
# The revision caches cover the cohort of the seed-20260719 pass: one external
# image was lost after the primary run, so that cohort has one study fewer.
COHORT_SEED = 20260719
C2_SEED = 20260718
ESTIMATORS = ("original", "evaluable_study", "cell_micro")
TIERS = (("source", "prespecified_eval"), ("external", "external"))


def needed(root: Path, seed: int, models=MODELS) -> list[Path]:
    paths = [rev_cache_path(root, site="source", tier="threshold_calibration", model=m, cond="C0",
                            train_seed=seed, c2_seed=None) for m in models]
    for site_name, tier in TIERS:
        for m in models:
            for c in CONDS:
                paths.append(rev_cache_path(root, site=site_name, tier=tier, model=m, cond=c,
                                            train_seed=seed, c2_seed=C2_SEED if c == "C2" else None))
    return paths


def replicate_policy(root: Path, seed: int, models=MODELS) -> tuple[Policy, dict[str, Any]]:
    """Thresholds and the 80% cutoff re-selected on the calibration tier by the frozen rule."""
    th, cu, sel = {}, {}, {}
    for m in models:
        with np.load(rev_cache_path(root, site="source", tier="threshold_calibration", model=m,
                                    cond="C0", train_seed=seed, c2_seed=None)) as z:
            th[m], cu[m] = _select({k: z[k] for k in z.files})
        sel[m] = {"thresholds": dict(zip(TARGETS, np.round(th[m], 6).tolist())),
                  "cutoff_0.80": round(float(cu[m]), 6)}
    return Policy(name=f"replicate_{seed}", thresholds=th, cutoffs=cu), sel


def replicate_sites(root: Path, seed: int, models=MODELS) -> tuple[Site, Site]:
    out = {}
    for site_name, tier in TIERS:
        s = load_site(root, site_name, seed=COHORT_SEED, models=())
        for m in models:
            for c in CONDS:
                s.probs[(m, c)] = _aligned(s, rev_cache_path(
                    root, site=site_name, tier=tier, model=m, cond=c, train_seed=seed,
                    c2_seed=C2_SEED if c == "C2" else None))
        out[site_name] = s
    return out["source"], out["external"]


def macro_auroc(site: Site, model: str, cond: str = "C0") -> dict[str, float]:
    lab, msk = labels_from_raw(site.raw)
    p = site.probs[(model, cond)]
    per = {}
    for j, name in enumerate(TARGETS):
        obs = msk[:, j] > 0
        per[name] = auroc(p[obs, j], lab[obs, j] > 0)
    per["macro"] = float(np.mean([per[t] for t in TARGETS]))
    return per


def replicates(root: Path, seeds=NEW_SEEDS, models=MODELS, multimodal=("M3", "M4"),
               n_boot: int = 2000) -> dict[str, Any]:
    root = Path(root)
    contrasts, coverage, status, disc, selection = [], [], [], [], {}
    for seed in seeds:
        missing = [p for p in needed(root, seed, models) if not p.exists()]
        if missing:
            status.append({"train_seed": seed, "status": "pending", "missing_caches": len(missing)})
            continue
        pol, sel = replicate_policy(root, seed, models)
        src, ext = replicate_sites(root, seed, models)
        fam = run_family(src, ext, pol, models=models, multimodal=multimodal,
                         estimators=ESTIMATORS, replicates=n_boot)
        contrasts += [{"train_seed": seed, **r} for r in fam["contrasts"]]
        coverage += [{"train_seed": seed, **r} for r in fam["coverage_gap"]]
        for m in models:
            a, b = macro_auroc(src, m), macro_auroc(ext, m)
            disc.append({"train_seed": seed, "model": m, "auroc_macro_source": a["macro"],
                         "auroc_macro_external": b["macro"],
                         "difference": b["macro"] - a["macro"]})
        selection[str(seed)] = sel
        status.append({"train_seed": seed, "status": "done", "missing_caches": 0})
    return {"seed_status": status, "seed_contrasts": contrasts, "seed_coverage_gap": coverage,
            "seed_discrimination": disc, "seed_selection": selection}


def second_seed_discrimination(root: Path) -> list[dict[str, Any]]:
    """Macro AUROC for the seed-20260719 replicate: M1 and M4 from the Stage 8/9b
    caches, M2 and M3 from the revision caches (as in followup.m2m3_replicate)."""
    rows = []
    for m in MODELS:
        vals = {}
        for site_name, tier in TIERS:
            if m in ("M1", "M4"):
                s = load_site(root, site_name, seed=COHORT_SEED, models=(m,), conditions=("C0",))
            else:
                s = load_site(root, site_name, seed=COHORT_SEED, models=(), conditions=("C0",))
                path = rev_cache_path(root, site=site_name, tier=tier, model=m, cond="C0",
                                      train_seed=COHORT_SEED, c2_seed=None)
                if not path.exists():
                    return []
                s.probs[(m, "C0")] = _aligned(s, path)
            vals[site_name] = macro_auroc(s, m)["macro"]
        rows.append({"train_seed": COHORT_SEED, "model": m, "auroc_macro_source": vals["source"],
                     "auroc_macro_external": vals["external"],
                     "difference": vals["external"] - vals["source"]})
    return rows


KEYS = ("hypothesis", "model", "site", "contrast", "estimator")


def summary(primary: pd.DataFrame, second: pd.DataFrame, new: pd.DataFrame) -> list[dict[str, Any]]:
    """Per-seed estimates of H1 (all models) and H4, and their between-seed spread.

    ``primary``: hypotheses.csv rows of the primary analysis and primary labels;
    ``second``: the seed-20260719 family; ``new``: rows from ``replicates``.
    """
    frames = [primary.assign(train_seed=20260718), second.assign(train_seed=20260719)]
    if len(new):
        frames.append(new)
    allr = pd.concat(frames, ignore_index=True)
    allr = allr[allr.hypothesis.isin(["H1", "H4"]) & allr.estimator.isin(["evaluable_study", "original"])]
    allr = allr.assign(site=allr.site.fillna(""))
    rows = []
    for key, g in allr.groupby(list(KEYS), sort=True):
        g = g.drop_duplicates("train_seed").sort_values("train_seed")
        base = dict(zip(KEYS, key))
        for _, r in g.iterrows():
            rows.append({**base, "train_seed": int(r.train_seed), "point_estimate": float(r.point_estimate),
                         "ci_low": float(r.ci_low), "ci_high": float(r.ci_high), "verdict": r.verdict})
        x = g.point_estimate.to_numpy(float)
        rows.append({**base, "train_seed": "all", "n_seeds": len(x), "mean": float(x.mean()),
                     "sd_between_seeds": float(x.std(ddof=1)) if len(x) > 1 else float("nan"),
                     "min": float(x.min()), "max": float(x.max()),
                     "n_ci_above_zero": int((g.ci_low > 0).sum()), "n_ci_below_zero": int((g.ci_high < 0).sum())})
    return rows
