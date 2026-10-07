"""One machine-readable verdict function for every hypothesis contrast.

Registered rules (protocols/C3E6_stage2/config/hypothesis_registry.yaml and
experiment_registry.yaml ``failure_criteria``), recovered verbatim:

  H1  confirmatory, direction > 0, materiality 0.02
      (failure_criteria.selective_transport_failure)
  H2  confirmatory, direction > 0, materiality 0.02, contexts C0 vs C1 only
      (failure_criteria.compound_shift_failure)
  H3  confirmatory, direction > 0, **no materiality registered**
  H4  **secondary**, direction >= 0, **no materiality registered**

The H4 direction-only rule was implemented in commit b6052a7 (2026-08-06),
before any external result existed, so it is the authentic H4 rule. The
manuscript's statement that every hypothesis needs a 0.02 point estimate was a
reporting error, not a code error.

Labels are deliberately finer than "confirmed / not confirmed". A point
estimate reaching materiality with an interval excluding zero does **not**
show that the true effect exceeds materiality; that needs the interval itself
to clear it, reported separately as ``interval_excludes_materiality``.
Likewise, an interval that includes zero is not evidence of no effect; only an
interval lying inside (-materiality, +materiality) is reported as
``within_materiality_bounds``.
"""

from __future__ import annotations

import math
from typing import Any

#: Registered rules. ``materiality=None`` means the registry names none.
REGISTERED_RULES: dict[str, dict[str, Any]] = {
    "H1": {"status": "confirmatory", "direction": "greater", "materiality": 0.02,
           "registry_note": "failure_criteria.selective_transport_failure"},
    "H2": {"status": "confirmatory", "direction": "greater", "materiality": 0.02,
           "registry_note": "failure_criteria.compound_shift_failure; contexts C0 and C1 only"},
    "H3": {"status": "confirmatory", "direction": "greater", "materiality": None,
           "registry_note": ("no materiality registered; estimand registered as MET006 "
                             "Omega contrast, which is identically H2 because M1 is "
                             "context-invariant")},
    "H4": {"status": "secondary", "direction": "greater_or_equal", "materiality": None,
           "registry_note": "secondary; direction >= 0; no materiality registered"},
}

#: The materiality the original Stage 10 code applied to H3 by default.
STAGE10_H3_MATERIALITY = 0.02

VERDICTS = (
    "confirmed",                        # interval on hypothesised side, and materiality met if registered
    "same_direction_not_material",      # interval on hypothesised side, point below materiality
    "inconclusive",                     # interval includes zero
    "opposite_direction_not_material",  # interval on opposite side, |point| below materiality
    "opposite_direction_material",      # interval on opposite side, |point| at/above materiality
)


class VerdictInputError(ValueError):
    """Raised for a non-finite or internally inconsistent estimate."""


def _finite(name: str, x: float) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError) as exc:
        raise VerdictInputError(f"{name} is not a number: {x!r}") from exc
    if not math.isfinite(v):
        raise VerdictInputError(f"{name} is not finite: {x!r}")
    return v


def verdict(point: float, lo: float, hi: float, *,
            direction: str = "greater",
            materiality: float | None = 0.02) -> dict[str, Any]:
    """Classify one contrast.

    ``direction`` is ``"greater"`` (hypothesis predicts a positive contrast) or
    ``"greater_or_equal"`` (predicts a non-negative one; tested, as
    implemented before results, by requiring the interval to lie above zero).
    ``"less"`` is accepted for completeness and mirrors ``"greater"``.

    Boundary conventions, all pinned by tests:
      * an interval endpoint exactly at zero does **not** exclude zero;
      * a point estimate exactly at materiality **does** reach it;
      * an interval endpoint exactly at materiality **does** clear it.
    """
    p, l, h = _finite("point", point), _finite("ci_low", lo), _finite("ci_high", hi)
    if l > h:
        raise VerdictInputError(f"ci_low {l} exceeds ci_high {h}")
    if direction not in ("greater", "greater_or_equal", "less"):
        raise VerdictInputError(f"unknown direction {direction!r}")
    if materiality is not None:
        materiality = _finite("materiality", materiality)
        if materiality < 0:
            raise VerdictInputError("materiality must be non-negative")

    sign = -1.0 if direction == "less" else 1.0
    # Orient so the hypothesised direction is always "above".
    sp, sl, sh = sign * p, min(sign * l, sign * h), max(sign * l, sign * h)

    if sl > 0.0:
        side = "hypothesised"
    elif sh < 0.0:
        side = "opposite"
    else:
        side = "spans_zero"

    reaches = None if materiality is None else bool(sp >= materiality)
    magnitude_material = None if materiality is None else bool(abs(sp) >= materiality)

    if side == "hypothesised":
        if materiality is None or reaches:
            label = "confirmed"
        else:
            label = "same_direction_not_material"
    elif side == "spans_zero":
        label = "inconclusive"
    else:
        label = ("opposite_direction_material"
                 if (materiality is not None and magnitude_material)
                 else "opposite_direction_not_material")

    return {
        "point_estimate": p, "ci_low": l, "ci_high": h,
        "direction": direction, "materiality": materiality,
        "ci_excludes_zero": bool(l > 0.0 or h < 0.0),
        "ci_side": side,
        "reaches_materiality": reaches,
        "interval_excludes_materiality": (None if materiality is None
                                          else bool(sl >= materiality)),
        "within_materiality_bounds": (None if materiality is None
                                      else bool(l > -materiality and h < materiality)),
        "point_outside_interval": bool(p < l or p > h),
        "confirmed": label == "confirmed",
        "verdict": label,
    }


def registered_verdict(hypothesis: str, point: float, lo: float, hi: float,
                       *, materiality_override: float | None | str = "registered"
                       ) -> dict[str, Any]:
    """Apply the rule registered for ``hypothesis`` (H1-H4)."""
    if hypothesis not in REGISTERED_RULES:
        raise VerdictInputError(f"unregistered hypothesis {hypothesis!r}")
    rule = REGISTERED_RULES[hypothesis]
    mat = rule["materiality"] if materiality_override == "registered" else materiality_override
    out = verdict(point, lo, hi, direction=rule["direction"], materiality=mat)
    out.update({"hypothesis": hypothesis, "status": rule["status"],
                "rule_materiality_source": ("registered" if materiality_override == "registered"
                                            else "override")})
    return out


def short_label(v: dict[str, Any]) -> str:
    """Human-readable verdict for tables."""
    return {
        "confirmed": "confirmed",
        "same_direction_not_material": "same direction, below materiality",
        "inconclusive": "inconclusive (CI includes 0)",
        "opposite_direction_not_material": "opposite direction, below materiality",
        "opposite_direction_material": "opposite direction, material magnitude",
    }[v["verdict"]]
