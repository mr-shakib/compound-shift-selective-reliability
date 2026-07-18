"""End-to-end synthetic-only Stage 2B preflight runner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable

import numpy as np
import pandas as pd

from c3e.safety_scan import scan_tree

from .context_interventions import create_context_interventions, validate_interventions
from .contracts import (
    BOOTSTRAP_SEED,
    ContractError,
    EXTERNAL_SITE_ID,
    EXTERNAL_SPLIT,
    IMAGE_PROBABILITY_COLUMNS,
    MULTIMODAL_PROBABILITY_COLUMNS,
    PATHOLOGIES,
    PRIMARY_LABEL_SOURCE,
    SOURCE_SITE_ID,
    validate_data_contract,
    validate_frozen_protocol,
)
from .leakage_checks import validate_context_payload
from .metrics import (
    any_label_error,
    any_label_error_per_study,
    aurc,
    compound_shift_interaction,
    controlled_context_penalty,
    coverage,
    coverage_transport_gap,
    failure_detection_auroc,
    five_label_hamming_loss,
    hamming_error_per_study,
    pathology_auprc,
    pathology_auroc,
    pathology_binary_error,
    pathology_brier_score,
    risk_transport_gap,
    selective_risk,
)
from .split_checks import assert_selection_allowed, validate_split_isolation
from .study_aggregation import aggregate_images_to_studies
from .synthetic_data import generate_synthetic_records, synthetic_counts
from .threshold_policy import (
    apply_classification_thresholds,
    fit_source_threshold_policy,
    minimum_margin_confidence,
)

PENDING_FIELDS = [
    "exact MIMIC pre-diagnostic section mapping",
    "exact image backbone",
    "exact text backbone",
    "actual dataset counts",
    "real-data batch-size feasibility",
    "three-seed ensemble feasibility",
    "verified AUGRC implementation",
]

EXACT_COMMANDS = [
    "cd protocols/C3E6_stage2 && sha256sum -c MANIFEST.sha256 && cd ../..",
    "c3e_audit_toolkit/.venv/bin/python protocols/C3E6_stage2/scripts/validate_protocol.py",
    "c3e_audit_toolkit/.venv/bin/python -m unittest discover -s protocols/C3E6_stage2/tests -v",
    "cd c3e_audit_toolkit && .venv/bin/python -m pytest tests -q && cd ..",
    "cd c3e_audit_toolkit && .venv/bin/python -m pytest tests/preflight -q && cd ..",
    "scripts/run_stage2b_preflight.sh",
]


def _condition(
    studies: pd.DataFrame,
    *,
    site_id: str,
    split_id: str,
    intervention: str,
) -> pd.DataFrame:
    out = studies[
        studies["site_id"].eq(site_id)
        & studies["split_id"].eq(split_id)
        & studies["intervention"].eq(intervention)
    ].copy()
    if out.empty:
        raise ContractError(f"empty synthetic condition: {site_id}/{split_id}/{intervention}")
    return out.sort_values("study_id", kind="stable").reset_index(drop=True)


def _evaluate_condition(frame: pd.DataFrame, policy, abstention_threshold: float) -> dict:
    predictions = apply_classification_thresholds(frame, policy)
    truth = frame[list(PATHOLOGIES)]
    hamming_losses = hamming_error_per_study(truth, predictions)
    failures = any_label_error_per_study(truth, predictions)
    confidence = minimum_margin_confidence(frame)
    pathology_metrics = {}
    for pathology, probability_column in zip(PATHOLOGIES, MULTIMODAL_PROBABILITY_COLUMNS):
        pathology_metrics[pathology] = {
            "binary_error": pathology_binary_error(truth[pathology], predictions[pathology]),
            "AUROC": pathology_auroc(truth[pathology], frame[probability_column]),
            "AUPRC": pathology_auprc(truth[pathology], frame[probability_column]),
            "Brier_score": pathology_brier_score(truth[pathology], frame[probability_column]),
        }
    return {
        "n_studies": int(len(frame)),
        "five_label_Hamming_loss": five_label_hamming_loss(truth, predictions),
        "any_label_error": any_label_error(truth, predictions),
        "minimum_margin_confidence_mean": float(np.mean(confidence)),
        "selective_risk": selective_risk(hamming_losses, confidence, abstention_threshold),
        "coverage": coverage(confidence, abstention_threshold),
        "AURC": aurc(hamming_losses, confidence),
        "failure_detection_AUROC": failure_detection_auroc(failures, confidence),
        "pathology_metrics": pathology_metrics,
    }


def _expect_rejection(name: str, operation: Callable[[], object], rejected: list[str], failed: list[str]) -> None:
    try:
        operation()
    except (ContractError, ValueError, KeyError, NotImplementedError):
        rejected.append(name)
    else:
        failed.append(f"negative case was silently accepted: {name}")


def _negative_case_checks(
    natural: pd.DataFrame,
    interventions: pd.DataFrame,
    studies: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    rejected: list[str] = []
    failed: list[str] = []

    duplicate = pd.concat([natural, natural.iloc[[0]]], ignore_index=True)
    _expect_rejection("duplicate image IDs", lambda: validate_data_contract(duplicate), rejected, failed)

    multi_patient = natural.copy()
    row = multi_patient.iloc[0].copy()
    row["image_id"] = "SYN-INVALID-UNIQUE-IMAGE"
    row["patient_id"] = "SYN-INVALID-OTHER-PERSON"
    multi_patient = pd.concat([multi_patient, pd.DataFrame([row])], ignore_index=True)
    _expect_rejection("one study assigned to multiple patients", lambda: validate_data_contract(multi_patient), rejected, failed)

    multi_study = natural.copy()
    row = multi_study.iloc[0].copy()
    row["study_id"] = "SYN-INVALID-OTHER-STUDY"
    multi_study = pd.concat([multi_study, pd.DataFrame([row])], ignore_index=True)
    _expect_rejection("one image assigned to multiple studies", lambda: validate_data_contract(multi_study), rejected, failed)

    split_overlap = natural.copy()
    train_patient = split_overlap[
        split_overlap["site_id"].eq(SOURCE_SITE_ID) & split_overlap["split_id"].eq("train")
    ]["patient_id"].iloc[0]
    calibration_index = split_overlap[
        split_overlap["site_id"].eq(SOURCE_SITE_ID) & split_overlap["split_id"].eq("calibration")
    ].index[0]
    split_overlap.at[calibration_index, "patient_id"] = train_patient
    _expect_rejection("patient overlap across source splits", lambda: validate_split_isolation(split_overlap), rejected, failed)

    _expect_rejection("missing required identifiers", lambda: validate_data_contract(natural.drop(columns=["patient_id"])), rejected, failed)
    _expect_rejection("missing pathology columns", lambda: validate_data_contract(natural.drop(columns=[PATHOLOGIES[0]])), rejected, failed)
    bad_value = natural.copy(); bad_value.at[bad_value.index[0], PATHOLOGIES[0]] = 2
    _expect_rejection("invalid pathology values", lambda: validate_data_contract(bad_value), rejected, failed)
    unsupported = natural.copy(); unsupported["label_source"] = "unsupported_labels.json"
    _expect_rejection("unsupported label sources", lambda: validate_data_contract(unsupported), rejected, failed)
    report_source = natural.copy(); report_source["label_source"] = "report_fixed.json"
    _expect_rejection("report_fixed.json", lambda: validate_data_contract(report_source), rejected, failed)

    for column, name in (
        ("findings", "Findings as model input"),
        ("impression", "Impression as model input"),
        ("full_report", "complete report as model input"),
    ):
        contaminated = natural.copy(); contaminated[column] = "forbidden synthetic payload"
        _expect_rejection(name, lambda frame=contaminated: validate_context_payload(frame), rejected, failed)

    inconsistent = natural.copy()
    informative_index = inconsistent[inconsistent["context_state"].eq("informative")].index[0]
    inconsistent.at[informative_index, "context_text"] = ""
    _expect_rejection("inconsistent natural context states", lambda: validate_data_contract(inconsistent), rejected, failed)

    for column, replacement, name in (
        ("context_donor_patient_id", lambda frame: frame["patient_id"], "C2 same-patient pairing"),
        ("context_donor_site_id", lambda frame: "SYN-CROSS-SITE", "C2 cross-site pairing"),
        ("context_donor_split_id", lambda frame: "SYN-CROSS-SPLIT", "C2 cross-split pairing"),
    ):
        invalid = interventions.copy()
        mask = invalid["intervention"].eq("C2")
        value = replacement(invalid.loc[mask])
        invalid.loc[mask, column] = value
        _expect_rejection(name, lambda frame=invalid: validate_interventions(frame), rejected, failed)

    external_calibration_attempt = studies[studies["site_id"].eq(EXTERNAL_SITE_ID)].copy()
    _expect_rejection(
        "target-site threshold fitting",
        lambda: fit_source_threshold_policy(external_calibration_attempt),
        rejected,
        failed,
    )
    for action, name in (
        ("temperature_selection", "target-site temperature fitting"),
        ("architecture_selection", "target-site architecture selection"),
        ("context_rule_revision", "target-site context-rule revision"),
    ):
        _expect_rejection(
            name,
            lambda selected_action=action: assert_selection_allowed(
                site_id=EXTERNAL_SITE_ID, action=selected_action
            ),
            rejected,
            failed,
        )
    return rejected, failed


def run_preflight(protocol_root: str | Path) -> dict:
    protocol_root = Path(protocol_root)
    protocol = validate_frozen_protocol(protocol_root)
    positive_checks: list[str] = ["frozen protocol lock validated"]
    failed_checks: list[str] = []

    primary = generate_synthetic_records(label_source=PRIMARY_LABEL_SOURCE)
    sensitivity = generate_synthetic_records(label_source="findings_fixed.json")
    validate_data_contract(primary)
    validate_data_contract(sensitivity)
    validate_split_isolation(primary)
    validate_context_payload(primary)
    positive_checks += [
        "primary synthetic data contract validated",
        "findings sensitivity synthetic contract validated",
        "patient split isolation validated",
        "forbidden input leakage checks passed",
    ]

    interventions = create_context_interventions(primary)
    validate_interventions(interventions)
    positive_checks += [
        "C0/C1/C2 study sets validated",
        "C2 donor constraints validated",
        "image-only invariance validated",
    ]
    studies = aggregate_images_to_studies(interventions)
    if studies.duplicated(["study_id", "intervention"]).any():
        failed_checks.append("study aggregation produced duplicate study/intervention rows")
    else:
        positive_checks.append("study-equal aggregation produced one row per study")

    calibration = _condition(
        studies, site_id=SOURCE_SITE_ID, split_id="calibration", intervention="C0"
    )
    policy = fit_source_threshold_policy(calibration)
    positive_checks.append("classification and abstention thresholds frozen from source calibration only")
    tau = policy.abstention_thresholds[0.80]

    conditions: dict[str, dict] = {}
    for site_name, site_id, split_id in (
        ("source", SOURCE_SITE_ID, "test"),
        ("external", EXTERNAL_SITE_ID, EXTERNAL_SPLIT),
    ):
        for intervention in ("C0", "C1", "C2"):
            key = f"{site_name}_{intervention}"
            conditions[key] = _evaluate_condition(
                _condition(studies, site_id=site_id, split_id=split_id, intervention=intervention),
                policy,
                tau,
            )
    positive_checks.append("all mandatory Stage 2B metrics executed")

    transport = {
        "risk_transport_gap_C0": risk_transport_gap(
            conditions["external_C0"]["selective_risk"],
            conditions["source_C0"]["selective_risk"],
        ),
        "coverage_transport_gap_C0": coverage_transport_gap(
            conditions["external_C0"]["coverage"],
            conditions["source_C0"]["coverage"],
        ),
        "source_no_context_penalty": controlled_context_penalty(
            conditions["source_C1"]["selective_risk"],
            conditions["source_C0"]["selective_risk"],
        ),
        "external_no_context_penalty": controlled_context_penalty(
            conditions["external_C1"]["selective_risk"],
            conditions["external_C0"]["selective_risk"],
        ),
        "compound_shift_interaction_C1": compound_shift_interaction(
            conditions["external_C1"]["selective_risk"],
            conditions["external_C0"]["selective_risk"],
            conditions["source_C1"]["selective_risk"],
            conditions["source_C0"]["selective_risk"],
        ),
    }

    rejected, negative_failures = _negative_case_checks(primary, interventions, studies)
    failed_checks.extend(negative_failures)
    if not negative_failures:
        positive_checks.append("all deliberate negative fixtures rejected")

    intervention_counts = {
        name: {
            "images": int(part["image_id"].nunique()),
            "studies": int(part["study_id"].nunique()),
        }
        for name, part in interventions.groupby("intervention", observed=True)
    }
    natural_context_counts = {
        str(key): int(value)
        for key, value in primary.drop_duplicates("study_id")["context_state"].value_counts().items()
    }
    metrics_executed = [
        "five-label Hamming loss",
        "any-label error",
        "pathology-specific binary error",
        "study-level minimum-margin confidence",
        "selective risk",
        "coverage",
        "risk transport gap",
        "coverage transport gap",
        "controlled context penalty",
        "compound-shift interaction",
        "AURC",
        "failure-detection AUROC",
        "AUROC",
        "AUPRC",
        "Brier score",
    ]
    return {
        "status": "PASS" if not failed_checks else "FAIL",
        "declarations": [
            "SYNTHETIC DATA ONLY",
            "NO MEDICAL IMAGES LOADED",
            "NO MODEL TRAINING PERFORMED",
            "EXTERNAL TUNING DISABLED",
        ],
        "protocol_id": protocol["protocol_id"],
        "protocol_version": protocol["protocol_version"],
        "deterministic_seed": BOOTSTRAP_SEED,
        "synthetic_counts": synthetic_counts(primary),
        "natural_context_study_counts": natural_context_counts,
        "context_intervention_counts": intervention_counts,
        "source_only_synthetic_thresholds": policy.as_dict(),
        "metrics_successfully_executed": metrics_executed,
        "metric_results": {"conditions": conditions, "transport": transport},
        "positive_checks_passed": positive_checks,
        "deliberate_negative_cases_rejected": rejected,
        "failed_checks": failed_checks,
        "unresolved_pending_fields": PENDING_FIELDS,
        "exact_commands": EXACT_COMMANDS,
        "test_execution": [],
        "positive_tests_passed": {},
    }


def _test_count(text: str) -> int | None:
    for pattern in (r"(\d+) passed", r"Ran (\d+) tests?"):
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def run_relevant_tests(project_root: Path, python_executable: str) -> list[dict]:
    specs = [
        (
            "protocol tests",
            [python_executable, "-m", "unittest", "discover", "-s", "protocols/C3E6_stage2/tests", "-v"],
            "c3e_audit_toolkit/.venv/bin/python -m unittest discover -s protocols/C3E6_stage2/tests -v",
        ),
        (
            "audit toolkit and Stage 2B tests",
            [python_executable, "-m", "pytest", "tests", "-q"],
            "cd c3e_audit_toolkit && .venv/bin/python -m pytest tests -q && cd ..",
        ),
        (
            "Stage 2B tests",
            [python_executable, "-m", "pytest", "tests/preflight", "-q"],
            "cd c3e_audit_toolkit && .venv/bin/python -m pytest tests/preflight -q && cd ..",
        ),
    ]
    outcomes = []
    for name, command, display in specs:
        cwd = project_root if name == "protocol tests" else project_root / "c3e_audit_toolkit"
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        combined = completed.stdout + "\n" + completed.stderr
        outcomes.append({
            "suite": name,
            "command": display,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "tests_passed": _test_count(combined) if completed.returncode == 0 else None,
            "return_code": completed.returncode,
        })
    return outcomes


def _markdown(report: dict) -> str:
    lines = [
        "# C3-E6 Stage 2B Synthetic Preflight Report",
        "",
        f"Status: **{report['status']}**",
        "",
    ]
    lines += [f"- **{item}**" for item in report["declarations"]]
    counts = report["synthetic_counts"]
    lines += [
        "",
        "## Protocol and cohort",
        "",
        f"- Protocol: `{report['protocol_id']}` version `{report['protocol_version']}`",
        f"- Deterministic seed: `{report['deterministic_seed']}`",
        f"- Synthetic patients: {counts['patients']}",
        f"- Synthetic studies: {counts['studies']}",
        f"- Synthetic images: {counts['images']}",
        "",
        "## Context interventions",
        "",
    ]
    for intervention, values in report["context_intervention_counts"].items():
        lines.append(f"- {intervention}: {values['studies']} studies / {values['images']} images")
    lines += ["", "## Frozen source-only thresholds", "", "```json"]
    lines += json.dumps(report["source_only_synthetic_thresholds"], indent=2).splitlines()
    lines += ["```", "", "## Execution status", ""]
    lines.append(f"- Metrics executed: {len(report['metrics_successfully_executed'])}")
    lines.append(f"- Positive checks passed: {len(report['positive_checks_passed'])}")
    lines.append(f"- Deliberate negative cases rejected: {len(report['deliberate_negative_cases_rejected'])}")
    for test in report["test_execution"]:
        lines.append(f"- {test['suite']}: {test['status']} ({test['tests_passed']} passed)")
    lines += ["", "## Failed checks", ""]
    lines += [f"- {item}" for item in report["failed_checks"]] or ["- None"]
    lines += ["", "## Unresolved pending fields", ""]
    lines += [f"- {item}" for item in report["unresolved_pending_fields"]]
    lines += ["", "## Exact commands", "", "```bash"]
    lines += report["exact_commands"]
    lines += ["```", ""]
    return "\n".join(lines)


def write_reports(report: dict, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "stage2b_preflight_report.json"
    md_path = output / "stage2b_preflight_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    safety = scan_tree(output, delete_unsafe=False)
    if not safety["clean"]:
        json_path.unlink(missing_ok=True)
        md_path.unlink(missing_ok=True)
        raise ContractError(f"generated preflight report failed safety scan: {safety['unsafe_files']}")


def execute(
    *,
    protocol_root: str | Path,
    output_dir: str | Path,
    project_root: str | Path,
    run_tests: bool,
) -> int:
    try:
        report = run_preflight(protocol_root)
        if run_tests:
            outcomes = run_relevant_tests(Path(project_root), sys.executable)
            report["test_execution"] = outcomes
            report["positive_tests_passed"] = {
                item["suite"]: item["tests_passed"]
                for item in outcomes
                if item["status"] == "PASS"
            }
            failures = [item for item in outcomes if item["status"] != "PASS"]
            if failures:
                report["failed_checks"].extend(
                    f"test suite failed: {item['suite']}" for item in failures
                )
                report["status"] = "FAIL"
        write_reports(report, output_dir)
        print(json.dumps({
            "status": report["status"],
            "positive_checks": len(report["positive_checks_passed"]),
            "negative_cases_rejected": len(report["deliberate_negative_cases_rejected"]),
            "failed_checks": len(report["failed_checks"]),
            "output_dir": "results/c3e_preflight",
        }, indent=2))
        return 0 if report["status"] == "PASS" else 1
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "declarations": [
                "SYNTHETIC DATA ONLY",
                "NO MEDICAL IMAGES LOADED",
                "NO MODEL TRAINING PERFORMED",
                "EXTERNAL TUNING DISABLED",
            ],
            "protocol_id": "C3E6-STAGE2",
            "protocol_version": "unknown",
            "deterministic_seed": BOOTSTRAP_SEED,
            "synthetic_counts": {"patients": 0, "studies": 0, "images": 0},
            "natural_context_study_counts": {},
            "context_intervention_counts": {},
            "source_only_synthetic_thresholds": {},
            "metrics_successfully_executed": [],
            "metric_results": {},
            "positive_checks_passed": [],
            "deliberate_negative_cases_rejected": [],
            "failed_checks": [f"{type(exc).__name__}: {exc}"],
            "unresolved_pending_fields": PENDING_FIELDS,
            "exact_commands": EXACT_COMMANDS,
            "test_execution": [],
            "positive_tests_passed": {},
        }
        try:
            write_reports(failure, output_dir)
        except Exception:
            pass
        print(f"Stage 2B preflight failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    project_default = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Run the synthetic-only C3-E6 Stage 2B preflight")
    parser.add_argument("--protocol-root", default=str(project_default / "protocols" / "C3E6_stage2"))
    parser.add_argument("--output", default=str(project_default / "results" / "c3e_preflight"))
    parser.add_argument("--project-root", default=str(project_default))
    parser.add_argument("--run-tests", action="store_true")
    args = parser.parse_args(argv)
    return execute(
        protocol_root=args.protocol_root,
        output_dir=args.output,
        project_root=args.project_root,
        run_tests=args.run_tests,
    )


if __name__ == "__main__":
    raise SystemExit(main())
