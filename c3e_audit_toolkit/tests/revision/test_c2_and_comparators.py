"""C2 replay, alignment refusal and comparator mechanics. Synthetic data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from c3e.evaluation.interventions import apply_c2
from c3e.revision.align import AlignmentError, verify_against_cache
from c3e.revision.c2_audit import audit, c2_with_donors
from c3e.revision.comparators import conformal_q, conformal_sets, fit_temperature
from c3e.revision.selective import auroc, rc_curve


def _frame(seed=0, n_pat=40):
    rng = np.random.default_rng(seed)
    rows = []
    words = ["cough", "fever", "chest pain", "dyspnea eval effusion", "follow up pneumonia",
             "rule out chf edema", "post op line placement check"]
    for p in range(n_pat):
        for s in range(rng.integers(1, 3)):
            ctx = " ".join(rng.choice(words, size=rng.integers(1, 4)))
            for i in range(rng.integers(1, 3)):
                rows.append({"subject_id": f"P{p:03d}", "study_id": f"S{p:03d}{s}",
                             "image_path": f"img{p:03d}{s}{i}", "context": ctx, "split": "train"})
    return pd.DataFrame(rows)


def test_replica_reproduces_apply_c2_and_never_uses_same_patient_when_possible():
    f = _frame()
    rep, donor = c2_with_donors(f)
    assert (rep["context"].to_numpy() == apply_c2(f)["context"].to_numpy()).all()
    r = audit(f, site="synthetic")
    assert r["replica_reproduces_apply_c2"]
    assert r["rows_same_patient_donor"] == 0
    # The invariant the stages reported counts identical text, whoever donated it.
    assert r["stage_invariant_count_reproduced"] == r["rows_identical_text"]


def test_c2_is_assigned_per_image_so_a_study_can_receive_several_donors():
    r = audit(_frame(seed=2, n_pat=80), site="synthetic")
    assert r["multi_image_studies"] > 0
    assert r["studies_whose_images_received_multiple_donor_studies"] > 0


def test_alignment_refuses_any_mismatch():
    cohort = pd.DataFrame({"patient": ["a", "b"], "Cardiomegaly": [1.0, np.nan], "Edema": [0.0, -1.0],
                           "Consolidation": [np.nan] * 2, "Atelectasis": [np.nan] * 2,
                           "Pleural Effusion": [np.nan] * 2})
    good = {"patients": np.array(["a", "b"]),
            "labels": np.array([[1, 0, 0, 0, 0], [0, 0, 0, 0, 0]], float),
            "mask": np.array([[1, 1, 0, 0, 0], [0, 0, 0, 0, 0]], float)}
    assert verify_against_cache(cohort, good)["labels_match"]
    for key, bad in (("patients", np.array(["b", "a"])),
                     ("mask", np.array([[1, 0, 0, 0, 0], [0, 0, 0, 0, 0]], float))):
        with pytest.raises(AlignmentError):
            verify_against_cache(cohort, {**good, key: bad})


def test_conformal_singletons_follow_the_binary_set_rule():
    p = np.array([[0.95, 0.5, 0.02, 0.6, 0.4]])
    single, lab1 = conformal_sets(p, np.array([0.3] * 5))
    # q < 0.5: singleton iff |p - 0.5| >= 0.5 - q, otherwise empty.
    assert single[0].tolist() == [True, False, True, False, False]
    assert lab1[0, 0] == 1 and lab1[0, 2] == 0
    single, _ = conformal_sets(p, np.array([0.7] * 5))
    # q >= 0.5: singleton iff |p - 0.5| > q - 0.5, otherwise both labels.
    assert single[0].tolist() == [True, False, True, False, False]


def test_conformal_quantile_is_finite_sample_corrected():
    p = np.linspace(0.01, 0.99, 99)
    y = (p > 0.5).astype(float)
    q = conformal_q(p, y, alpha=0.1)
    s = np.sort(np.where(y == 1, 1 - p, p))
    assert q == s[int(np.ceil(100 * 0.9)) - 1]


def test_temperature_fit_recovers_a_known_temperature():
    rng = np.random.default_rng(0)
    z = rng.normal(0, 3, 20000)
    y = (rng.random(20000) < 1 / (1 + np.exp(-z / 2.0))).astype(float)
    assert fit_temperature(z, y) == pytest.approx(2.0, rel=0.05)


def test_auroc_and_rc_curve_basics():
    assert auroc(np.array([0.9, 0.8, 0.1, 0.2]), np.array([1, 1, 0, 0], bool)) == 1.0
    assert auroc(np.array([0.5, 0.5]), np.array([1, 0], bool)) == 0.5
    conf = np.array([0.9, 0.8, 0.7, 0.6])
    err = np.array([0.0, 0.0, 1.0, np.nan])
    rc = rc_curve(conf, err)
    assert rc["aurc"] == pytest.approx((0 + 0 + 1 / 3) / 3)
    assert rc["augrc"] == pytest.approx((0 + 0 + 1 / 3) / 3)
