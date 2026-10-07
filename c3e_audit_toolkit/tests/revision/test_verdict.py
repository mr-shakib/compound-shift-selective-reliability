"""The single verdict function. All inputs synthetic."""

from __future__ import annotations

import math

import pytest

from c3e.revision.verdict import (REGISTERED_RULES, VerdictInputError, registered_verdict,
                                  verdict)


def test_confirmed_requires_interval_above_zero_and_point_at_materiality():
    v = verdict(0.03, 0.01, 0.05, direction="greater", materiality=0.02)
    assert v["verdict"] == "confirmed" and v["confirmed"]
    # A point at materiality with an interval excluding zero does not show the
    # true effect exceeds materiality; that needs the interval to clear it.
    assert v["interval_excludes_materiality"] is False


def test_point_exactly_at_materiality_reaches_it():
    v = verdict(0.02, 0.001, 0.04, materiality=0.02)
    assert v["reaches_materiality"] is True and v["verdict"] == "confirmed"


def test_point_just_below_materiality_is_not_confirmed():
    v = verdict(math.nextafter(0.02, 0.0), 0.001, 0.04, materiality=0.02)
    assert v["verdict"] == "same_direction_not_material"


def test_interval_endpoint_at_zero_does_not_exclude_zero():
    v = verdict(0.03, 0.0, 0.06, materiality=0.02)
    assert v["ci_excludes_zero"] is False and v["verdict"] == "inconclusive"
    v = verdict(-0.03, -0.06, 0.0, materiality=0.02)
    assert v["ci_excludes_zero"] is False and v["verdict"] == "inconclusive"


def test_interval_endpoint_at_materiality_clears_it():
    v = verdict(0.03, 0.02, 0.04, materiality=0.02)
    assert v["interval_excludes_materiality"] is True


def test_interval_crossing_zero_is_inconclusive_whatever_the_point():
    for p in (-0.05, 0.0, 0.05):
        assert verdict(p, -0.06, 0.07, materiality=0.02)["verdict"] == "inconclusive"


def test_opposite_direction_split_by_magnitude():
    assert verdict(-0.035, -0.04, -0.03, materiality=0.02)["verdict"] == "opposite_direction_material"
    assert verdict(-0.006, -0.008, -0.004, materiality=0.02)["verdict"] == "opposite_direction_not_material"
    # Magnitude exactly at materiality counts as material.
    assert verdict(-0.02, -0.03, -0.01, materiality=0.02)["verdict"] == "opposite_direction_material"


def test_direction_only_rule_without_materiality():
    v = verdict(0.006, 0.0019, 0.0102, direction="greater_or_equal", materiality=None)
    assert v["verdict"] == "confirmed" and v["reaches_materiality"] is None
    v = verdict(-0.006, -0.008, -0.004, direction="greater_or_equal", materiality=None)
    assert v["verdict"] == "opposite_direction_not_material"


def test_less_direction_mirrors_greater():
    a = verdict(0.03, 0.01, 0.05, direction="greater", materiality=0.02)
    b = verdict(-0.03, -0.05, -0.01, direction="less", materiality=0.02)
    assert a["verdict"] == b["verdict"] == "confirmed"


def test_within_materiality_bounds_is_reported_separately_from_inconclusive():
    v = verdict(-0.002, -0.011, 0.006, materiality=0.02)
    assert v["verdict"] == "inconclusive" and v["within_materiality_bounds"] is True
    v = verdict(0.0, -0.03, 0.03, materiality=0.02)
    assert v["within_materiality_bounds"] is False


@pytest.mark.parametrize("args", [(float("nan"), 0, 1), (0, float("inf"), 1), (0, 0.5, 0.1),
                                  ("x", 0, 1)])
def test_invalid_inputs_raise(args):
    with pytest.raises(VerdictInputError):
        verdict(*args)


def test_unknown_direction_and_negative_materiality_raise():
    with pytest.raises(VerdictInputError):
        verdict(0, -1, 1, direction="up")
    with pytest.raises(VerdictInputError):
        verdict(0, -1, 1, materiality=-0.1)


def test_point_outside_interval_is_flagged_not_rejected():
    v = verdict(0.05, 0.01, 0.04, materiality=0.02)
    assert v["point_outside_interval"] is True


def test_registered_rules_match_the_registry():
    assert REGISTERED_RULES["H1"]["materiality"] == 0.02
    assert REGISTERED_RULES["H2"]["materiality"] == 0.02
    assert REGISTERED_RULES["H3"]["materiality"] is None
    assert REGISTERED_RULES["H4"]["status"] == "secondary"
    assert REGISTERED_RULES["H4"]["direction"] == "greater_or_equal"


def test_published_h4_source_m4_is_confirmed_under_its_registered_rule():
    # Table 8 (+0.0173) and the seed replicate (+0.0060) are "confirmed" only
    # because H4 is registered without materiality, not under a 0.02 rule.
    assert registered_verdict("H4", 0.017326, 0.012525, 0.021723)["confirmed"]
    assert registered_verdict("H4", 0.006026, 0.001921, 0.010216)["confirmed"]
    assert not registered_verdict("H4", 0.006026, 0.001921, 0.010216,
                                  materiality_override=0.02)["confirmed"]


def test_registry_file_agrees_with_rules():
    from pathlib import Path
    import yaml
    root = Path(__file__).resolve().parents[3]
    reg = yaml.safe_load((root / "protocols/C3E6_stage2/config/hypothesis_registry.yaml").read_text())
    by_id = {h["id"]: h for h in reg["hypotheses"]}
    for hid, rule in REGISTERED_RULES.items():
        assert by_id[hid].get("materiality_threshold") == rule["materiality"]
        assert by_id[hid]["status"] == rule["status"]
