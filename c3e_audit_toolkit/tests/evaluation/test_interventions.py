"""Guards on the frozen C0/C1/C2 interventions. All fixtures are synthetic."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from c3e.evaluation.interventions import (NO_CONTEXT_TOKEN, InvariantViolation,
                                          apply_c1, apply_c2, check_invariants,
                                          effective_tokens, length_bin,
                                          natural_state)


def _frame(n=60, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "subject_id": np.repeat(np.arange(n // 2), 2),
        "study_id": np.arange(n),
        "split": ["train"] * n,
        "image_path": [f"files/p10/x/y/{i}.jpg" for i in range(n)],
        "context": [f"patient with symptom number {i} and more words here"
                    for i in range(n)],
    })


def test_placeholder_runs_do_not_count_as_information():
    """A body of de-identification placeholders is not context."""
    assert effective_tokens("___ ____ _____") == 0
    assert effective_tokens("___-year-old man with cough") == 4


def test_natural_states_follow_the_frozen_threshold():
    assert natural_state("") == "N3"
    assert natural_state("___") == "N3"
    assert natural_state("chest pain") == "N2"
    assert natural_state("acute onset chest pain today") == "N1"


def test_c1_replaces_every_context():
    out = apply_c1(_frame())
    assert (out["context"] == NO_CONTEXT_TOKEN).all()


def test_c1_preserves_study_identity():
    f = _frame()
    assert apply_c1(f)["study_id"].tolist() == f["study_id"].tolist()


def test_c2_gives_every_study_a_different_patients_context():
    f = _frame()
    c2 = apply_c2(f)
    inv = check_invariants(f, apply_c1(f), c2)
    assert inv["c2_studies_retaining_own_context"] == 0


def test_c2_is_deterministic():
    f = _frame()
    assert apply_c2(f)["context"].tolist() == apply_c2(f)["context"].tolist()


def test_c2_preserves_the_multiset_of_contexts():
    """Permutation must move context, not invent or drop it."""
    f = _frame()
    assert sorted(apply_c2(f)["context"]) == sorted(f["context"])


def test_c2_stays_within_length_bin():
    f = _frame()
    f.loc[:9, "context"] = "short"
    c2 = apply_c2(f)
    for i in range(len(f)):
        assert length_bin(c2.at[i, "context"]) == length_bin(f.at[i, "context"])


def test_invariants_reject_a_forbidden_section():
    f = _frame()
    f.loc[0, "context"] = "IMPRESSION: cardiomegaly"
    with pytest.raises(InvariantViolation, match="forbidden"):
        check_invariants(f, apply_c1(f), apply_c2(f))


def test_invariants_reject_mismatched_study_ids():
    f = _frame()
    bad = f.copy(); bad["study_id"] = bad["study_id"] + 1
    with pytest.raises(InvariantViolation, match="identical study identifiers"):
        check_invariants(f, apply_c1(f), bad)


def test_invariants_reject_incomplete_c1():
    f = _frame()
    bad = apply_c1(f); bad.loc[0, "context"] = "leftover text"
    with pytest.raises(InvariantViolation, match="C1 must replace"):
        check_invariants(f, bad, apply_c2(f))


def test_evaluation_tier_is_unreachable_from_training_and_calibration():
    """The confirmatory tier must not be readable by any stage that could
    influence a model, a threshold, or a policy."""
    from c3e.training.dataset import PURPOSE_ALLOWED_TIERS

    assert "prespecified_eval" not in PURPOSE_ALLOWED_TIERS["training"]
    assert "prespecified_eval" not in PURPOSE_ALLOWED_TIERS["calibration"]
    assert "prespecified_eval" in PURPOSE_ALLOWED_TIERS["confirmatory_evaluation"]


def test_c2_works_with_either_sites_path_column():
    """The two sites name the path column differently; C2 must stay
    deterministic at both rather than depending on one site's schema."""
    f = _frame()
    ext = f.rename(columns={"image_path": "path_to_image"})
    a = apply_c2(ext)["context"].tolist()
    b = apply_c2(ext)["context"].tolist()
    assert a == b
    assert sorted(a) == sorted(ext["context"])


def test_c2_reports_a_missing_tiebreak_rather_than_guessing():
    f = _frame().drop(columns=["image_path", "study_id"])
    with pytest.raises(KeyError, match="tiebreak"):
        apply_c2(f)
