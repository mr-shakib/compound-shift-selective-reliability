"""Loading CheXpert validation radiologist labels for the Phase 0 check."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from c3e.calibration.policy import TARGETS
from c3e.revision.expert_valid import _category, _study_error, load_expert


def _csv(tmp_path, rows):
    cols = ["Path", "Sex", "Age", "Frontal/Lateral", "AP/PA", *TARGETS]
    p = tmp_path / "valid.csv"
    pd.DataFrame(rows, columns=cols).to_csv(p, index=False)
    return p


def test_study_labels_take_any_image_positive(tmp_path):
    rows = [["CheXpert-v1.0/valid/patient1/study1/view1_frontal.jpg", "F", 60, "Frontal", "AP", 1, 0, 0, 0, 0],
            ["CheXpert-v1.0/valid/patient1/study1/view2_lateral.jpg", "F", 60, "Lateral", "", 0, 0, 0, 0, 1],
            ["CheXpert-v1.0/valid/patient2/study1/view1_frontal.jpg", "M", 50, "Frontal", "PA", 0, 0, 0, 0, 0]]
    lab = load_expert(_csv(tmp_path, rows))
    assert list(lab.index) == ["valid/patient1/study1", "valid/patient2/study1"]
    assert lab.loc["valid/patient1/study1"].tolist() == [1, 0, 0, 0, 1]


def test_rejects_paths_outside_the_validation_layout(tmp_path):
    rows = [["CheXpert-v1.0/train/patient1/study1/view1_frontal.jpg", "F", 60, "Frontal", "AP", 1, 0, 0, 0, 0]]
    with pytest.raises(ValueError):
        load_expert(_csv(tmp_path, rows))


def test_report_label_categories_and_error():
    raw = np.array([[1.0, 0.0, -1.0, np.nan, 1.0]])
    assert _category(raw).tolist() == [["positive", "negative", "uncertain", "unmentioned", "positive"]]
    pred = np.array([[1, 1, 0, 0, 0]])
    lab = np.array([[1, 0, 0, 0, 1]])
    assert np.isclose(_study_error(pred, lab, np.ones((1, 5)))[0], 2 / 5)
    assert np.isnan(_study_error(pred, lab, np.zeros((1, 5)))[0])
