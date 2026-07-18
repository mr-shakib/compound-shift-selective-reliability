from pathlib import Path

import pytest

from c3e.preflight.context_interventions import create_context_interventions
from c3e.preflight.study_aggregation import aggregate_images_to_studies
from c3e.preflight.synthetic_data import generate_synthetic_records


@pytest.fixture(scope="session")
def protocol_root() -> Path:
    return Path(__file__).resolve().parents[3] / "protocols" / "C3E6_stage2"


@pytest.fixture()
def synthetic_images():
    return generate_synthetic_records()


@pytest.fixture()
def intervention_images(synthetic_images):
    return create_context_interventions(synthetic_images)


@pytest.fixture()
def study_rows(intervention_images):
    return aggregate_images_to_studies(intervention_images)
