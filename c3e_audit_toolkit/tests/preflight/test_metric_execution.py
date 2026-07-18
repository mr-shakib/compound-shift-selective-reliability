import numpy as np
import pandas as pd
import pytest

from c3e.preflight.metrics import (
    any_label_error,
    augrc_placeholder,
    aurc,
    compound_shift_interaction,
    controlled_context_penalty,
    coverage,
    coverage_transport_gap,
    failure_detection_auroc,
    five_label_hamming_loss,
    pathology_auprc,
    pathology_auroc,
    pathology_binary_error,
    pathology_brier_score,
    risk_transport_gap,
    selective_risk,
)
from c3e.preflight.runner import run_preflight


def test_standard_and_selective_metrics_execute(protocol_root):
    labels = ["Cardiomegaly", "Edema", "Pleural Effusion", "Atelectasis", "Consolidation"]
    truth = pd.DataFrame([[1, 0, 1, 0, 1], [0, 1, 0, 1, 0]], columns=labels)
    pred = pd.DataFrame([[1, 0, 0, 0, 1], [0, 0, 0, 1, 0]], columns=labels)
    probability = pd.Series([0.8, 0.2, 0.7, 0.3])
    binary_truth = pd.Series([1, 0, 1, 0])
    binary_pred = pd.Series([1, 0, 1, 1])
    losses = np.array([0.0, 0.4, 0.2, 0.8])
    confidence = np.array([0.9, 0.7, 0.4, 0.1])
    failures = np.array([0, 1, 0, 1])
    assert five_label_hamming_loss(truth, pred) == pytest.approx(0.2)
    assert any_label_error(truth, pred) == 1.0
    assert pathology_binary_error(binary_truth, binary_pred) == 0.25
    assert coverage(confidence, 0.4) == 0.75
    assert selective_risk(losses, confidence, 0.4) == pytest.approx(0.2)
    assert aurc(losses, confidence) >= 0
    assert failure_detection_auroc(failures, confidence) >= 0
    assert pathology_auroc(binary_truth, probability) == 1.0
    assert pathology_auprc(binary_truth, probability) == 1.0
    assert pathology_brier_score(binary_truth, probability) >= 0
    assert risk_transport_gap(0.3, 0.2) == pytest.approx(0.1)
    assert coverage_transport_gap(0.7, 0.8) == pytest.approx(-0.1)
    assert controlled_context_penalty(0.25, 0.2) == pytest.approx(0.05)
    assert compound_shift_interaction(0.4, 0.2, 0.25, 0.2) == pytest.approx(0.15)
    report = run_preflight(protocol_root)
    assert report["status"] == "PASS"
    assert len(report["metrics_successfully_executed"]) >= 15


def test_augrc_is_explicit_unimplemented_placeholder():
    with pytest.raises(NotImplementedError, match="verified implementation"):
        augrc_placeholder()
