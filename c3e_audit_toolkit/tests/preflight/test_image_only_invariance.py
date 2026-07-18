import numpy as np

from c3e.preflight.contracts import IMAGE_PROBABILITY_COLUMNS


def test_image_only_probabilities_exactly_invariant(intervention_images):
    groups = {
        name: frame.sort_values("image_id")
        for name, frame in intervention_images.groupby("intervention")
    }
    for column in IMAGE_PROBABILITY_COLUMNS:
        assert np.array_equal(groups["C0"][column].to_numpy(), groups["C1"][column].to_numpy())
        assert np.array_equal(groups["C0"][column].to_numpy(), groups["C2"][column].to_numpy())
