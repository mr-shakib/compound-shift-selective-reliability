import pandas as pd
import pytest

from c3e.preflight.contracts import ContractError, validate_data_contract


def test_duplicate_image_ids_rejected(synthetic_images):
    invalid = pd.concat([synthetic_images, synthetic_images.iloc[[0]]], ignore_index=True)
    with pytest.raises(ContractError, match="duplicate image IDs"):
        validate_data_contract(invalid)


def test_study_assigned_to_multiple_patients_rejected(synthetic_images):
    extra = synthetic_images.iloc[0].copy()
    extra["image_id"] = "SYN-INVALID-NEW-IMAGE"
    extra["patient_id"] = "SYN-INVALID-OTHER-PERSON"
    invalid = pd.concat([synthetic_images, pd.DataFrame([extra])], ignore_index=True)
    with pytest.raises(ContractError, match="multiple patients"):
        validate_data_contract(invalid)


def test_image_assigned_to_multiple_studies_rejected(synthetic_images):
    extra = synthetic_images.iloc[0].copy()
    extra["study_id"] = "SYN-INVALID-OTHER-STUDY"
    invalid = pd.concat([synthetic_images, pd.DataFrame([extra])], ignore_index=True)
    with pytest.raises(ContractError, match="duplicate image IDs"):
        validate_data_contract(invalid)
