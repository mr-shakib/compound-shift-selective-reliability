"""Guards on the training-stage protocol boundaries.

Three things must hold no matter how the pipeline is refactored: reserved tiers
stay unreadable during training, unsupervised label cells never contribute
gradient, and M3 never acquires parameters of its own.

All fixtures are synthetic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from c3e.training.dataset import (FORBIDDEN_TIERS, TARGETS, TierAccessError,
                                  build_index, split_internal_validation)
from c3e.training.models import masked_bce_with_logits


@pytest.mark.parametrize("tier", FORBIDDEN_TIERS)
def test_reserved_tiers_refuse_to_load(tier, tmp_path):
    """Reading a reserved tier during training must fail loudly, not warn.

    The calibration tier belongs to threshold selection and the evaluation tier
    to the confirmatory analysis. Touching either during training would
    contaminate the preregistered path, and a soft warning is not a boundary.
    """
    with pytest.raises(TierAccessError):
        build_index(tmp_path, tier=tier)


def test_model_train_tier_is_not_blocked():
    assert "model_train" not in FORBIDDEN_TIERS


def test_internal_validation_split_is_patient_disjoint():
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({
        "subject_id": rng.integers(1000, 1100, size=800),
        "image_path": [f"files/p10/x/y/{i}.jpg" for i in range(800)],
        "context": ["some context"] * 800,
        **{t: rng.choice([1.0, 0.0], size=800) for t in TARGETS},
    })
    train, val = split_internal_validation(frame)
    assert len(train) + len(val) == len(frame)
    assert not set(train["subject_id"]) & set(val["subject_id"])


def test_internal_validation_split_is_deterministic():
    frame = pd.DataFrame({
        "subject_id": np.arange(500) % 120,
        "image_path": [f"files/p10/x/y/{i}.jpg" for i in range(500)],
        "context": [""] * 500,
        **{t: np.zeros(500) for t in TARGETS},
    })
    a, _ = split_internal_validation(frame)
    b, _ = split_internal_validation(frame)
    assert a["image_path"].tolist() == b["image_path"].tolist()


def test_masked_loss_ignores_unsupervised_cells():
    """Uncertain and unmentioned labels must carry no gradient.

    Mapping them to negative would change the prevalence the protocol froze. For
    Atelectasis, where the labeller emits almost no explicit negatives, that
    would invent a negative class that does not exist in the labels.
    """
    logits = torch.tensor([[5.0, -5.0, 5.0, -5.0, 5.0]])
    target = torch.tensor([[1.0, 0.0, 0.0, 1.0, 0.0]])
    all_supervised = torch.ones(1, 5)
    only_correct = torch.tensor([[1.0, 1.0, 0.0, 0.0, 0.0]])

    assert masked_bce_with_logits(logits, target, only_correct).item() < 0.01
    assert masked_bce_with_logits(logits, target, all_supervised).item() > 1.0


def test_masked_loss_is_finite_when_nothing_is_supervised():
    logits = torch.randn(4, 5)
    target = torch.zeros(4, 5)
    mask = torch.zeros(4, 5)
    assert torch.isfinite(masked_bce_with_logits(logits, target, mask))


def test_m3_has_no_trainable_parameters():
    """M3 must stay a pure average.

    If it ever gains parameters, a gain over M1 stops being attributable to the
    text signal and becomes attributable to extra capacity, which is exactly the
    confound M3 exists to rule out.
    """
    from c3e.training.models import M3LateFusion

    class _Stub(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.w = torch.nn.Linear(4, 5)

        def forward(self, *_args, **_kwargs):
            return self.w(torch.zeros(2, 4))

    m3 = M3LateFusion(_Stub(), _Stub())
    assert sum(p.numel() for p in m3.parameters() if p.requires_grad) == 0


def test_auroc_rejects_non_finite_scores():
    """A NaN score means the forward pass diverged; scoring survivors would
    report a metric over a subset chosen by numerical accident."""
    from c3e.training.runner import _macro_auroc

    scores = np.array([[0.5, 0.5], [np.nan, 0.5]])
    targets = np.array([[1.0, 0.0], [0.0, 1.0]])
    mask = np.ones((2, 2))
    with pytest.raises(ValueError, match="non-finite"):
        _macro_auroc(scores, targets, mask)
