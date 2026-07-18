import pytest

from c3e.preflight.context_interventions import validate_interventions
from c3e.preflight.contracts import ContractError, EXTERNAL_SITE_ID, validate_data_contract
from c3e.preflight.split_checks import assert_selection_allowed


@pytest.mark.parametrize(
    "column,replacement,message",
    [
        ("context_donor_patient_id", "same_patient", "different patient"),
        ("context_donor_site_id", "SYN-OTHER-SITE", "crossed site"),
        ("context_donor_split_id", "SYN-OTHER-SPLIT", "crossed split"),
    ],
)
def test_invalid_c2_pairings_rejected(intervention_images, column, replacement, message):
    invalid = intervention_images.copy()
    mask = invalid["intervention"].eq("C2")
    if replacement == "same_patient":
        invalid.loc[mask, column] = invalid.loc[mask, "patient_id"]
    else:
        invalid.loc[mask, column] = replacement
    with pytest.raises(ContractError, match=message):
        validate_interventions(invalid)


@pytest.mark.parametrize(
    "action",
    ["classification_threshold_selection", "temperature_selection", "architecture_selection", "context_rule_revision"],
)
def test_external_selection_actions_rejected(action):
    with pytest.raises(ContractError):
        assert_selection_allowed(site_id=EXTERNAL_SITE_ID, action=action)


def test_unsupported_and_forbidden_label_sources_rejected(synthetic_images):
    for source in ("unknown.json", "report_fixed.json"):
        invalid = synthetic_images.copy()
        invalid["label_source"] = source
        with pytest.raises(ContractError):
            validate_data_contract(invalid)


def test_inconsistent_context_state_rejected(synthetic_images):
    invalid = synthetic_images.copy()
    index = invalid[invalid["context_state"].eq("absent")].index[0]
    invalid.at[index, "context_text"] = "fictional text contradicts absence"
    with pytest.raises(ContractError, match="absent context_state"):
        validate_data_contract(invalid)
