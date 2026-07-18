import pytest

from c3e.preflight.contracts import (
    ContractError,
    EXTERNAL_SITE_ID,
    SOURCE_COVERAGES,
    SOURCE_SITE_ID,
)
from c3e.preflight.split_checks import assert_selection_allowed
from c3e.preflight.threshold_policy import fit_source_threshold_policy


def test_source_calibration_thresholds_and_coverages_frozen(study_rows):
    calibration = study_rows[
        study_rows["site_id"].eq(SOURCE_SITE_ID)
        & study_rows["split_id"].eq("calibration")
        & study_rows["intervention"].eq("C0")
    ]
    policy = fit_source_threshold_policy(calibration)
    assert set(policy.classification_thresholds) == {
        "Cardiomegaly", "Edema", "Pleural Effusion", "Atelectasis", "Consolidation"
    }
    assert tuple(policy.abstention_thresholds) == SOURCE_COVERAGES
    assert policy.fit_site_id == SOURCE_SITE_ID


def test_target_site_threshold_fitting_rejected(study_rows):
    external = study_rows[
        study_rows["site_id"].eq(EXTERNAL_SITE_ID) & study_rows["intervention"].eq("C0")
    ]
    with pytest.raises(ContractError, match="source-calibration-only"):
        fit_source_threshold_policy(external)


@pytest.mark.parametrize("action", ["temperature_selection", "architecture_selection", "context_rule_revision"])
def test_other_target_site_selection_rejected(action):
    with pytest.raises(ContractError, match="target-site"):
        assert_selection_allowed(site_id=EXTERNAL_SITE_ID, action=action)
