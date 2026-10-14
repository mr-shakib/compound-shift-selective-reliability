"""Between-seed summary of the training-seed replicates."""

from __future__ import annotations

import numpy as np
import pandas as pd

from c3e.revision.seeds import summary


def _rows(seed=None, h1=0.0, h4=0.01):
    base = {"contrast": "x", "ci_low": -0.01, "ci_high": 0.01, "verdict": "inconclusive"}
    out = [{**base, "hypothesis": "H1", "model": "M4", "site": np.nan, "estimator": "evaluable_study",
            "point_estimate": h1},
           {**base, "hypothesis": "H4", "model": "M3", "site": "external", "estimator": "evaluable_study",
            "point_estimate": h4, "ci_low": h4 - 0.005, "ci_high": h4 + 0.005},
           {**base, "hypothesis": "H2", "model": "M4", "site": np.nan, "estimator": "evaluable_study",
            "point_estimate": 9.0}]
    df = pd.DataFrame(out)
    return df if seed is None else df.assign(train_seed=seed)


def test_summary_pools_all_seeds_and_skips_other_hypotheses():
    new = pd.concat([_rows(20260720, h1=0.03), _rows(20260721, h1=-0.03)], ignore_index=True)
    rows = pd.DataFrame(summary(_rows(h1=0.01), _rows(h1=-0.01), new))
    assert set(rows.hypothesis) == {"H1", "H4"}
    agg = rows[(rows.train_seed.astype(str) == "all") & (rows.hypothesis == "H1")].iloc[0]
    assert agg.n_seeds == 4
    assert np.isclose(agg["mean"], 0.0)
    assert np.isclose(agg.sd_between_seeds, np.std([0.01, -0.01, 0.03, -0.03], ddof=1))
    assert (agg["min"], agg["max"]) == (-0.03, 0.03)


def test_summary_counts_intervals_above_zero():
    rows = pd.DataFrame(summary(_rows(h4=0.02), _rows(h4=-0.02), pd.DataFrame()))
    agg = rows[(rows.train_seed.astype(str) == "all") & (rows.hypothesis == "H4")].iloc[0]
    assert (agg.n_ci_above_zero, agg.n_ci_below_zero, agg.n_seeds) == (1, 1, 2)
