"""Guards on which frozen thresholds a downstream stage consumes.

These exist because a real defect shipped. Stages 8 and 9b hardcoded the primary
Stage 7 path and ignored the seed, so the replicate run applied the *primary*
model's abstention cutoff (M4: 0.119743) to the *replicate* model's predictions,
whose own calibrated cutoff was 0.083848. Stage 10 resolved the path correctly,
so the three stages disagreed about which policy was being evaluated.

The predictions themselves were never wrong -- only the cutoff applied to them
-- which is precisely why the mismatch survived a reading of the output. Stage
9b reported an external coverage drift of -0.108 for M4 and Stage 10 reported
-0.026 for the same model and cohort. Nothing crashed.

Every stage now asks the module that writes these files. The tests below assert
that no stage reintroduces an opinion of its own.

All fixtures are synthetic and contain no patient data.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from c3e.calibration.runner import stage7_path
from c3e.training.runner import SEED

ROOT = Path("/nonexistent/project")


def test_primary_resolves_to_the_primary_artifact():
    p = stage7_path(ROOT, "impression", None)
    assert p == ROOT / "results/c3e_mimic/stage7_thresholds/stage7_thresholds.json"


def test_naming_the_primary_seed_explicitly_is_still_the_primary():
    # checkpoint_name treats seed == SEED as the primary; this must agree, or a
    # run passing the primary seed would look for an artifact never written.
    assert stage7_path(ROOT, "impression", SEED) == stage7_path(ROOT, "impression", None)


def test_replicate_resolves_to_its_own_artifact():
    p = stage7_path(ROOT, "impression", 20260719)
    assert p == (ROOT / "results/c3e_mimic/stage7_thresholds_seed20260719"
                 / "stage7_thresholds.json")


def test_replicate_never_resolves_to_the_primary():
    """The defect in one assertion."""
    assert stage7_path(ROOT, "impression", 20260719) != stage7_path(ROOT, "impression", None)


def test_findings_endpoint_resolves_to_the_sensitivity_artifact():
    p = stage7_path(ROOT, "findings", None)
    assert p == ROOT / "results/c3e_mimic/stage7_thresholds_findings/stage7_thresholds.json"


def test_replicate_on_the_findings_endpoint_is_refused():
    # No such Stage 7 was ever produced. Falling back to any existing artifact
    # would silently score one endpoint's predictions with another's cutoffs.
    with pytest.raises(RuntimeError, match="no Stage 7 exists for seed"):
        stage7_path(ROOT, "findings", 20260719)


@pytest.mark.parametrize("module", [
    "c3e.evaluation.runner",
    "c3e.external.evaluate",
    "c3e.analysis.runner",
])
def test_no_consumer_builds_the_stage7_path_itself(module):
    src = inspect.getsource(__import__(module, fromlist=["_"]))
    run_src = "".join(
        block for block in re.split(r"\ndef ", src)
        if block.startswith(("run(", "analyse(")))
    offenders = [line.strip() for line in run_src.splitlines()
                 if "stage7_path =" in line and "resolve_stage7" not in line]
    assert not offenders, (
        f"{module} constructs the Stage 7 path itself: {offenders}. "
        "Call resolve_stage7(root, label_source, seed) so a replicate cannot "
        "consume the primary's thresholds.")
