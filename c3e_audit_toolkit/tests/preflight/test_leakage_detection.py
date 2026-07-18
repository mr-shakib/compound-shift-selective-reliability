import pytest

from c3e.preflight.contracts import ContractError
from c3e.preflight.leakage_checks import validate_context_payload, validate_model_input_columns


@pytest.mark.parametrize("column", ["findings", "impression", "full_report", "report"])
def test_forbidden_model_input_columns_rejected(column):
    with pytest.raises(ContractError, match="forbidden model-input"):
        validate_model_input_columns(["context_text", column])


def test_forbidden_section_marker_in_context_rejected(synthetic_images):
    invalid = synthetic_images.copy()
    invalid.at[invalid.index[0], "context_text"] = "FINDINGS: fictional forbidden payload"
    with pytest.raises(ContractError, match="section marker"):
        validate_context_payload(invalid)


def test_clean_fictional_context_passes(synthetic_images):
    validate_context_payload(synthetic_images)
