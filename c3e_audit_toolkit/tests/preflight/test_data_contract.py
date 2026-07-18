import pytest

from c3e.preflight.contracts import (
    ContractError,
    PATHOLOGIES,
    PRIMARY_LABEL_SOURCE,
    REQUIRED_COLUMNS,
    SENSITIVITY_LABEL_SOURCE,
    validate_data_contract,
)
from c3e.preflight.synthetic_data import generate_synthetic_records


def test_valid_synthetic_contract_contains_locked_columns(synthetic_images):
    validate_data_contract(synthetic_images)
    assert set(REQUIRED_COLUMNS).issubset(synthetic_images.columns)
    assert tuple(pathology for pathology in PATHOLOGIES) == PATHOLOGIES


def test_both_approved_label_sources_validate():
    for source in (PRIMARY_LABEL_SOURCE, SENSITIVITY_LABEL_SOURCE):
        validate_data_contract(generate_synthetic_records(label_source=source))


@pytest.mark.parametrize("column", ["patient_id", "study_id", "image_id"])
def test_missing_required_identifier_column_rejected(synthetic_images, column):
    with pytest.raises(ContractError, match="missing required columns"):
        validate_data_contract(synthetic_images.drop(columns=[column]))


def test_missing_pathology_rejected(synthetic_images):
    with pytest.raises(ContractError, match="missing required columns"):
        validate_data_contract(synthetic_images.drop(columns=[PATHOLOGIES[0]]))


def test_invalid_pathology_value_rejected(synthetic_images):
    invalid = synthetic_images.copy()
    invalid.at[invalid.index[0], PATHOLOGIES[0]] = -1
    with pytest.raises(ContractError, match="invalid pathology values"):
        validate_data_contract(invalid)
