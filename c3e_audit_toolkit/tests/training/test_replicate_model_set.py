"""Guards on which models a replicate seed is allowed to score.

These exist because a real defect shipped. Only M1 and M4 were retrained under
the replicate seed, but Stages 7, 8 and 9b each loaded all four checkpoints
unconditionally, so every one of them died on a missing ``m2_best_seed*.pt``
after doing its full cohort setup. Stage 10 knew the correct model set but
still digested M2's checkpoint to build M3's identity, so it would have failed
at the same place had the earlier stages survived.

The quieter half of the defect is the one worth testing. Had an M2 replicate
file existed under any name, the stages would have run happily and produced an
M3 built from a replicate M1 and a primary M2 — two seeds inside one model,
reported as a seed replicate. The model set therefore has to be decided in one
place that every stage asks, rather than written out four times.

All fixtures below are synthetic and contain no patient data.
"""

from __future__ import annotations

import inspect
import re

import pytest

from c3e.training.runner import (SEED, checkpoint_name, scored_models,
                                 weighted_models)


def test_primary_scores_all_four_models():
    assert scored_models(None) == ("M1", "M2", "M3", "M4")
    assert scored_models(SEED) == ("M1", "M2", "M3", "M4")


def test_replicate_scores_only_the_models_that_were_retrained():
    assert scored_models(20260719) == ("M1", "M4")


def test_replicate_excludes_m3_because_it_would_mix_seeds():
    # M3 is the probability average of M1 and M2. With no M2 replicate it could
    # only be built from a replicate M1 and the primary M2.
    assert "M3" not in scored_models(20260719)
    assert "M2" not in scored_models(20260719)


def test_weighted_models_drops_m3_which_has_no_checkpoint():
    assert weighted_models(None) == ("M1", "M2", "M4")
    assert weighted_models(20260719) == ("M1", "M4")
    for seed in (None, 20260719):
        assert set(weighted_models(seed)) <= set(scored_models(seed))


def test_every_weighted_model_has_a_distinct_checkpoint_name():
    names = [checkpoint_name(m, 20260719) for m in weighted_models(20260719)]
    assert names == ["m1_best_seed20260719.pt", "m4_best_seed20260719.pt"]
    assert len(set(names)) == len(names)
    # The primary must not be reachable under a replicate seed, or a missing
    # replicate would silently fall back to primary weights.
    assert not set(names) & {checkpoint_name(m) for m in weighted_models(None)}


@pytest.mark.parametrize("module", [
    "c3e.calibration.runner",
    "c3e.evaluation.runner",
    "c3e.external.evaluate",
    "c3e.analysis.runner",
])
def test_no_stage_hardcodes_the_four_model_tuple(module):
    """Each stage must ask scored_models rather than list the models itself.

    A stage that disagreed with the analysis about which models exist would
    either crash on a missing checkpoint or cache a mixed-seed pass.
    """
    src = inspect.getsource(__import__(module, fromlist=["_"]))
    hardcoded = [line.strip() for line in src.splitlines()
                 if re.search(r'"M1",\s*"M2",\s*"M3",\s*"M4"', line)]
    assert not hardcoded, (
        f"{module} lists the model set itself: {hardcoded}. "
        "Call scored_models(seed) so a replicate cannot load a checkpoint "
        "that was never retrained.")
    assert "scored_models" in src, f"{module} never consults scored_models"
