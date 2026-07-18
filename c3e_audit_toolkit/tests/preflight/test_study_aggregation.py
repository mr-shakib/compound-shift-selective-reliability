import numpy as np
import pytest

from c3e.preflight.contracts import ContractError, MULTIMODAL_PROBABILITY_COLUMNS, PATHOLOGIES
from c3e.preflight.study_aggregation import aggregate_images_to_studies


def test_one_probability_vector_per_study_and_equal_downstream_weight(study_rows):
    assert not study_rows.duplicated(["study_id", "intervention"]).any()
    assert set(study_rows["eligible_image_count"]) == {1, 2}
    assert "patient_id" in study_rows


def test_multi_image_probability_is_arithmetic_mean(intervention_images, study_rows):
    sample = intervention_images[
        intervention_images["view"].eq("frontal") & intervention_images["intervention"].eq("C0")
    ].groupby("study_id").filter(lambda group: len(group) == 2).iloc[0]
    source = intervention_images[
        intervention_images["study_id"].eq(sample["study_id"])
        & intervention_images["intervention"].eq("C0")
        & intervention_images["view"].eq("frontal")
    ]
    result = study_rows[
        study_rows["study_id"].eq(sample["study_id"])
        & study_rows["intervention"].eq("C0")
    ].iloc[0]
    column = MULTIMODAL_PROBABILITY_COLUMNS[0]
    assert np.isclose(result[column], source[column].mean())


def test_inconsistent_study_labels_rejected(intervention_images):
    invalid = intervention_images.copy()
    group = invalid[invalid["intervention"].eq("C0")].groupby("study_id").filter(lambda g: len(g) > 1)
    invalid.at[group.index[0], PATHOLOGIES[0]] = 1 - int(invalid.at[group.index[0], PATHOLOGIES[0]])
    with pytest.raises(ContractError, match="labels are inconsistent"):
        aggregate_images_to_studies(invalid)


def test_unsupported_view_rejected(intervention_images):
    invalid = intervention_images.copy()
    invalid.at[invalid.index[0], "view"] = "oblique"
    with pytest.raises(ContractError, match="unsupported views"):
        aggregate_images_to_studies(invalid)
