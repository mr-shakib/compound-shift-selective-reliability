import pytest

from c3e.preflight.contracts import ContractError, SOURCE_SITE_ID
from c3e.preflight.split_checks import validate_split_isolation


def test_all_required_partitions_and_split_isolation_pass(synthetic_images):
    validate_split_isolation(synthetic_images)


def test_patient_overlap_across_source_splits_rejected(synthetic_images):
    invalid = synthetic_images.copy()
    train_patient = invalid[
        invalid["site_id"].eq(SOURCE_SITE_ID) & invalid["split_id"].eq("train")
    ]["patient_id"].iloc[0]
    mask = invalid["site_id"].eq(SOURCE_SITE_ID) & invalid["split_id"].eq("calibration")
    calibration_patient = invalid.loc[mask, "patient_id"].iloc[0]
    invalid.loc[mask & invalid["patient_id"].eq(calibration_patient), "patient_id"] = train_patient
    with pytest.raises(ContractError, match="overlap"):
        validate_split_isolation(invalid)
