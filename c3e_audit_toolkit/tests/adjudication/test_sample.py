"""Stratified allocation for the expert adjudication sample."""

from __future__ import annotations

import numpy as np
import pandas as pd

from c3e.adjudication.sample import allocate, draw, group_of, proportional, strata


def test_strata_codes_and_groups():
    s = strata(np.array([1, 0, 1]), np.array([1, 1, 0]), np.array([0, 1, 1]))
    assert s.tolist() == ["L1A1P0", "L0A1P1", "L1A0P1"]
    assert [group_of(x) for x in s] == ["accepted_labelled", "accepted_label_less", "deferred"]


def test_proportional_is_exact_and_respects_caps():
    a = proportional(100, {"x": 5, "y": 1000, "z": 1000})
    assert sum(a.values()) == 100
    assert a["x"] <= 5
    assert abs(a["y"] - a["z"]) <= 1
    assert proportional(50, {"x": 10, "y": 20}) == {"x": 10, "y": 20}


def test_allocate_matches_protocol_shares():
    sizes = {"L1A1P1": 4000, "L1A1P0": 2000, "L0A1P1": 1000, "L0A1P0": 3000,
             "L1A0P1": 1500, "L1A0P0": 500, "L0A0P1": 800, "L0A0P0": 200}
    a = allocate(sizes, per_site=600)
    assert sum(a.values()) == 600
    by = {}
    for s, n in a.items():
        by[group_of(s)] = by.get(group_of(s), 0) + n
    assert by == {"accepted_labelled": 300, "accepted_label_less": 150, "deferred": 150}
    assert a["L1A1P1"] == 200 and a["L1A1P0"] == 100


def test_draw_records_inclusion_probability():
    fr = pd.DataFrame({"study": [f"s{i}" for i in range(40)], "stratum": ["L1A1P1"] * 30 + ["L0A0P0"] * 10})
    out = draw(fr, {"L1A1P1": 3, "L0A0P0": 5}, np.random.default_rng(0))
    assert len(out) == 8 and out.study.is_unique
    assert np.allclose(out[out.stratum == "L1A1P1"].inclusion_prob, 0.1)
    assert np.allclose(out[out.stratum == "L0A0P0"].inclusion_prob, 0.5)
