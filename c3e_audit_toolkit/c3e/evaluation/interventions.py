"""C3-E6 Stage 8: the frozen C0, C1 and C2 context interventions.

C0 is identity, C1 replaces all permitted context with a single placeholder, and
C2 substitutes another patient's context under constraints. All three are
applied only to N1 studies — those whose context passes the frozen
informativeness rule — because removing context that was never there, or
misaligning context that was already absent, tests nothing.

The registry states five invariants for this stage. They are asserted here
rather than assumed, since a silent violation would not look like a bug: it
would look like a result.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

#: Frozen in context_interventions.yaml.
PLACEHOLDER_PATTERN = re.compile(r"_{2,}")
NO_CONTEXT_TOKEN = "[NO_CONTEXT]"
C2_SEED = 20260718
LENGTH_BINS = (0, 5, 10, 20, 40, 80, 10**9)


class InvariantViolation(RuntimeError):
    """A required invariant from the intervention registry did not hold."""


def effective_tokens(text: str) -> int:
    """Count tokens carrying information, per the frozen informativeness rule.

    De-identification placeholder runs are stripped first, so a body of
    placeholders scores zero rather than reading as informative context.
    """
    if not text:
        return 0
    cleaned = PLACEHOLDER_PATTERN.sub(" ", text)
    return sum(1 for tok in cleaned.split() if any(c.isalnum() for c in tok))


def natural_state(text: str, threshold: int = 3) -> str:
    """N1 informative, N2 low information, N3 absent."""
    n = effective_tokens(text)
    if n == 0:
        return "N3"
    return "N1" if n >= threshold else "N2"


def length_bin(text: str) -> int:
    n = effective_tokens(text)
    return int(np.digitize(n, LENGTH_BINS[1:-1]))


def apply_c1(frame: pd.DataFrame) -> pd.DataFrame:
    """Replace all permitted context with the frozen placeholder."""
    out = frame.copy()
    out["context"] = NO_CONTEXT_TOKEN
    return out


def _tiebreak_column(frame: pd.DataFrame) -> str:
    """A deterministic secondary sort key that exists at either site.

    The two sites name their path column differently. Ordering must still be
    reproducible, because the C2 rotation is defined as deterministic and a
    seed alone does not fix an ordering.
    """
    for candidate in ("image_path", "path_to_image", "study_id", "file_name"):
        if candidate in frame.columns:
            return candidate
    raise KeyError(
        "no deterministic tiebreak column found; C2 requires a reproducible "
        f"ordering and none of image_path/path_to_image/study_id is present in "
        f"{list(frame.columns)}")


def apply_c2(frame: pd.DataFrame, *, seed: int = C2_SEED) -> pd.DataFrame:
    """Deterministic permutation of context under the frozen constraints.

    Within each (split, length bin) stratum, contexts are rotated across
    patients so every recipient receives text from a different patient. The
    rotation is used rather than a random shuffle because a shuffle can leave
    fixed points, and a fixed point is silently a C0 study sitting inside C2.
    """
    out = frame.copy()
    out["_bin"] = out["context"].map(length_bin)
    tiebreak = _tiebreak_column(out)
    split_col = "split" if "split" in out.columns else None
    new_context = out["context"].to_numpy(dtype=object).copy()

    group_cols = ["_bin"] + ([split_col] if split_col else [])
    rng = np.random.default_rng(seed)

    for _, idx in out.groupby(group_cols, sort=True).groups.items():
        rows = np.asarray(idx)
        if len(rows) < 2:
            continue  # cannot satisfy different-patient; left as-is and reported
        # Order by patient so the rotation crosses patient boundaries, then
        # rotate by a stratum-specific non-zero offset.
        order = out.loc[rows].sort_values(["subject_id", tiebreak]).index.to_numpy()
        patients = out.loc[order, "subject_id"].to_numpy()
        n = len(order)
        offset = int(rng.integers(1, n)) if n > 1 else 0
        for k in range(n):
            donor = order[(k + offset) % n]
            # Walk forward until the donor is a different patient.
            step = 1
            while patients[(k + offset + step - 1) % n] == patients[k] and step <= n:
                donor = order[(k + offset + step) % n]
                step += 1
            new_context[out.index.get_loc(order[k])] = out.at[donor, "context"]

    out["context"] = new_context
    return out.drop(columns=["_bin"])


def check_invariants(c0: pd.DataFrame, c1: pd.DataFrame, c2: pd.DataFrame) -> dict[str, object]:
    """Assert the registry's required invariants and report what was checked."""
    if not (len(c0) == len(c1) == len(c2)):
        raise InvariantViolation("interventions differ in row count")

    ids0 = c0["study_id"].to_numpy()
    if not (np.array_equal(ids0, c1["study_id"].to_numpy())
            and np.array_equal(ids0, c2["study_id"].to_numpy())):
        raise InvariantViolation(
            "C0, C1 and C2 must contain identical study identifiers")

    if not (c1["context"] == NO_CONTEXT_TOKEN).all():
        raise InvariantViolation("C1 must replace every permitted context")

    same_patient = (c2["subject_id"].to_numpy() == c0["subject_id"].to_numpy()) & \
                   (c2["context"].to_numpy() == c0["context"].to_numpy())
    n_self = int(same_patient.sum())

    forbidden = re.compile(r"\b(?:findings|impression|wet read)\s*:", re.IGNORECASE)
    for name, f in (("C0", c0), ("C1", c1), ("C2", c2)):
        if f["context"].astype(str).str.contains(forbidden).any():
            raise InvariantViolation(
                f"a forbidden report section entered the {name} payload")

    return {
        "row_counts_match": True,
        "study_ids_identical_across_interventions": True,
        "c1_fully_replaced": True,
        "c2_studies_retaining_own_context": n_self,
        "c2_self_assignment_fraction": round(n_self / max(len(c2), 1), 6),
        "no_forbidden_section_in_any_payload": True,
        "c2_note": ("strata with a single member cannot satisfy the "
                    "different-patient constraint and retain their own context; "
                    "these are counted, not hidden"),
    }
