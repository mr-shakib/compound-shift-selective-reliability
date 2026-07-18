import pytest

from c3e.preflight.context_interventions import create_context_interventions, validate_interventions
from c3e.preflight.contracts import BOOTSTRAP_SEED, ContractError


def test_c0_c1_c2_semantics_and_donor_constraints(intervention_images):
    validate_interventions(intervention_images)
    groups = {k: v for k, v in intervention_images.groupby("intervention")}
    assert groups["C1"]["context_text"].eq("[NO_CONTEXT]").all()
    assert set(groups["C0"]["study_id"]) == set(groups["C1"]["study_id"]) == set(groups["C2"]["study_id"])
    assert groups["C2"]["patient_id"].ne(groups["C2"]["context_donor_patient_id"]).all()
    assert groups["C2"]["site_id"].eq(groups["C2"]["context_donor_site_id"]).all()
    assert groups["C2"]["split_id"].eq(groups["C2"]["context_donor_split_id"]).all()


def test_c2_is_deterministic(synthetic_images):
    first = create_context_interventions(synthetic_images, seed=BOOTSTRAP_SEED)
    second = create_context_interventions(synthetic_images, seed=BOOTSTRAP_SEED)
    columns = ["image_id", "intervention", "context_text", "context_donor_patient_id"]
    assert first[columns].equals(second[columns])


def test_nonfrozen_intervention_seed_rejected(synthetic_images):
    with pytest.raises(ContractError, match="frozen"):
        create_context_interventions(synthetic_images, seed=7)
