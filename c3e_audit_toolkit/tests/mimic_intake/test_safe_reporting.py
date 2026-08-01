import json
from pathlib import Path

import pytest

from c3e.mimic_intake.contracts import GateStatus, IntakeContractError
from c3e.mimic_intake.inventory import build_inventory
from c3e.mimic_intake.runner import _gate_payload, _write_outputs
from c3e.mimic_intake.safety import validate_safe_payload


def test_report_text_and_restricted_paths_never_enter_outputs(
    tmp_path: Path, intake_config
):
    data_root = tmp_path / "data" / "mimic"
    report = data_root / "reports" / "p123456" / "s987654.txt"
    report.parent.mkdir(parents=True)
    sentinel = "SYNTHETIC_SENTINEL_REPORT_BODY_NEVER_EXPORT"
    report.write_text(sentinel, encoding="utf-8")
    inventory = build_inventory(data_root, intake_config)
    gate = _gate_payload(
        GateStatus.BLOCKED,
        inventory,
        intake_config,
        missing=sorted(intake_config.required_categories),
        failures=[],
        git_ignored=True,
        protocol_valid=True,
    )
    output = tmp_path / "results" / "c3e_mimic" / "intake"
    _write_outputs(output, inventory, gate, project_root=tmp_path)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in output.iterdir())
    assert sentinel not in combined
    assert "p123456" not in combined
    assert "s987654" not in combined
    assert str(data_root.resolve()) not in combined
    payload = json.loads((output / "file_inventory.json").read_text(encoding="utf-8"))
    record = next(item for item in payload["records"] if item["category"] == "report_resource")
    assert record["content_access"] == "blocked_report_text"
    assert record["relative_path"] is None


def test_unsafe_output_fields_are_rejected(tmp_path: Path):
    with pytest.raises(IntakeContractError, match="unsafe output fields"):
        validate_safe_payload({"report_text": "forbidden"}, project_root=tmp_path)
    with pytest.raises(IntakeContractError, match="unsafe output fields"):
        validate_safe_payload({"patient_id": "not-exportable"}, project_root=tmp_path)


def test_absolute_restricted_data_path_is_rejected(tmp_path: Path):
    with pytest.raises(IntakeContractError, match="absolute project"):
        validate_safe_payload(
            {"relative_path": str(tmp_path / "data" / "mimic")}, project_root=tmp_path
        )
