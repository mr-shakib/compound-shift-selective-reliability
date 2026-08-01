"""Execute and report the C3-E6 Stage 3A access/readiness gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

from c3e.preflight.contracts import validate_frozen_protocol

from .contracts import (
    ALLOWED_OUTPUT_FILENAMES,
    DECLARATIONS,
    GateStatus,
    IntakeConfig,
    IntakeContractError,
    load_intake_config,
)
from .inventory import InventoryResult, build_inventory
from .safety import audit_output_directory, validate_safe_payload


def check_gitignore(project_root: Path, relative_data_root: str = "data/mimic") -> bool:
    probe = f"{relative_data_root.rstrip('/')}/.stage3a-ignore-probe"
    for target in (relative_data_root, probe):
        completed = subprocess.run(
            ["git", "check-ignore", "--quiet", "--", target],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return False
    return True


def determine_status(
    inventory: InventoryResult,
    config: IntakeConfig,
    *,
    git_ignored: bool,
    protocol_valid: bool,
) -> tuple[GateStatus, list[str], list[str]]:
    failures: list[str] = []
    if not git_ignored:
        failures.append("restricted data directory is not fully ignored by Git")
    if not protocol_valid:
        failures.append("frozen Stage 2 protocol integrity check failed")
    failures.extend(inventory.contract_errors)
    if inventory.scan_truncated:
        failures.append("configured metadata scan limit was reached; inventory is incomplete")
    if failures:
        return GateStatus.FAIL, [], failures

    present = {
        record.category
        for record in inventory.records
        if record.availability in {"available_readable", "available_readable_metadata"}
    }
    missing = sorted(set(config.required_categories) - present)
    if missing:
        return GateStatus.BLOCKED, missing, []
    return GateStatus.PASS, [], []


def _inventory_payload(inventory: InventoryResult) -> dict[str, Any]:
    return {
        "stage": "C3-E6 Stage 3A",
        "scope": "metadata and access inventory only",
        "declarations": list(DECLARATIONS),
        "category_counts": inventory.category_counts,
        "entries_examined": inventory.entries_examined,
        "scan_truncated": inventory.scan_truncated,
        "records": [record.as_dict() for record in inventory.records],
    }


def _gate_payload(
    status: GateStatus,
    inventory: InventoryResult,
    config: IntakeConfig,
    *,
    missing: list[str],
    failures: list[str],
    git_ignored: bool,
    protocol_valid: bool,
) -> dict[str, Any]:
    return {
        "stage": "C3-E6 Stage 3A",
        "title": "METADATA AND ACCESS INVENTORY",
        "status": status.value,
        "status_meaning": {
            "PASS": "required report, metadata, split, and checksum resources are available and readable",
            "BLOCKED": "access or required resources are absent; no scientific defect is claimed",
            "FAIL": "a safety, configuration, protocol-integrity, or contract check failed",
        }[status.value],
        "declarations": list(DECLARATIONS),
        "checks": {
            "frozen_protocol_valid": protocol_valid,
            "restricted_data_gitignored": git_ignored,
            "inventory_complete": not inventory.scan_truncated,
            "medical_image_content_accessed": False,
            "report_text_exported": False,
            "model_initialized_or_trained": False,
            "chexbert_executed": False,
            "external_data_accessed": False,
            "target_site_tuning_performed": False,
        },
        "required_categories": list(config.required_categories),
        "available_category_counts": inventory.category_counts,
        "missing_required_categories": missing,
        "failures": failures,
        "unknown_resource_count": inventory.category_counts.get("unknown", 0),
        "image_files_observed_by_metadata": inventory.category_counts.get("image_file", 0),
        "image_content_access_policy": "blocked",
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# C3-E6 Stage 3A Access Gate Report",
        "",
        f"Status: **{report['status']}**",
        "",
    ]
    lines.extend(f"- **{declaration}**" for declaration in report["declarations"])
    lines.extend(
        [
            "",
            "## Gate interpretation",
            "",
            report["status_meaning"],
            "",
            "## Required resource categories",
            "",
        ]
    )
    for category in report["required_categories"]:
        count = report["available_category_counts"].get(category, 0)
        lines.append(f"- `{category}`: {count} observed")
    lines.extend(["", "## Missing categories", ""])
    lines.extend(f"- `{item}`" for item in report["missing_required_categories"])
    if not report["missing_required_categories"]:
        lines.append("- None")
    lines.extend(["", "## Safety and integrity failures", ""])
    lines.extend(f"- {item}" for item in report["failures"])
    if not report["failures"]:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Inventory notes",
            "",
            f"- Unknown resources reported: {report['unknown_resource_count']}",
            f"- Medical-image entries observed through metadata only: {report['image_files_observed_by_metadata']}",
            "- Medical-image content access policy: blocked",
            "- No patient-level records or report excerpts are included.",
            "",
        ]
    )
    return "\n".join(lines)


def _csv_text(inventory: InventoryResult) -> str:
    fields = [
        "resource_key",
        "relative_path",
        "category",
        "file_type",
        "byte_size",
        "modification_time_utc",
        "sha256",
        "availability",
        "content_access",
        "observed_count",
        "truncated",
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for record in inventory.records:
        writer.writerow(record.as_dict())
    return stream.getvalue()


def _environment_text() -> str:
    packages = []
    for name in ("c3e-audit", "numpy", "pandas", "PyYAML", "pytest"):
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = "not-installed"
        packages.append(f"{name}={version}")
    return "\n".join(
        [
            "STAGE 3A ONLY",
            "METADATA AND ACCESS INVENTORY",
            f"python={platform.python_version()}",
            f"implementation={platform.python_implementation()}",
            f"platform={platform.system()}-{platform.machine()}",
            *packages,
            "medical_image_opened=false",
            "report_text_exported=false",
            "model_training=false",
            "chexbert_execution=false",
            "external_data_access=false",
            "target_site_tuning=false",
            "",
        ]
    )


def _write_outputs(
    output_dir: Path,
    inventory: InventoryResult,
    gate_report: dict[str, Any],
    *,
    project_root: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ALLOWED_OUTPUT_FILENAMES:
        (output_dir / name).unlink(missing_ok=True)

    inventory_payload = _inventory_payload(inventory)
    validate_safe_payload(inventory_payload, project_root=project_root)
    validate_safe_payload(gate_report, project_root=project_root)
    (output_dir / "file_inventory.json").write_text(
        json.dumps(inventory_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "file_inventory.csv").write_text(_csv_text(inventory), encoding="utf-8")
    (output_dir / "access_gate_report.json").write_text(
        json.dumps(gate_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "access_gate_report.md").write_text(_markdown(gate_report), encoding="utf-8")
    (output_dir / "environment.txt").write_text(_environment_text(), encoding="utf-8")

    hashed_names = [
        "file_inventory.json",
        "file_inventory.csv",
        "access_gate_report.json",
        "access_gate_report.md",
        "environment.txt",
    ]
    lines = []
    for name in hashed_names:
        digest = hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (output_dir / "safe_artifact_hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    audit_output_directory(output_dir, project_root=project_root)


def run_gate(
    *, project_root: str | Path, config_path: str | Path, protocol_root: str | Path
) -> GateStatus:
    root = Path(project_root).resolve()
    config = load_intake_config(config_path)
    data_root = config.resolve_data_root(root)
    output_dir = config.resolve_output_dir(root)

    protocol_valid = True
    try:
        validate_frozen_protocol(protocol_root)
    except Exception:
        protocol_valid = False
    git_ignored = check_gitignore(root, config.data_root)
    inventory = build_inventory(data_root, config)
    status, missing, failures = determine_status(
        inventory, config, git_ignored=git_ignored, protocol_valid=protocol_valid
    )
    gate_report = _gate_payload(
        status,
        inventory,
        config,
        missing=missing,
        failures=failures,
        git_ignored=git_ignored,
        protocol_valid=protocol_valid,
    )
    _write_outputs(output_dir, inventory, gate_report, project_root=root)
    return status


def execute(*, project_root: Path, config_path: Path, protocol_root: Path) -> int:
    try:
        status = run_gate(
            project_root=project_root, config_path=config_path, protocol_root=protocol_root
        )
    except Exception as exc:
        print(f"Stage 3A FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"stage": "C3-E6 Stage 3A", "status": status.value}, indent=2))
    return 0 if status in {GateStatus.PASS, GateStatus.BLOCKED} else 2


def main(argv: list[str] | None = None) -> int:
    project_default = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Run the C3-E6 Stage 3A MIMIC intake gate")
    parser.add_argument("--project-root", type=Path, default=project_default)
    parser.add_argument(
        "--config",
        type=Path,
        default=project_default / "c3e_audit_toolkit" / "configs" / "mimic_intake.yaml",
    )
    parser.add_argument(
        "--protocol-root",
        type=Path,
        default=project_default / "protocols" / "C3E6_stage2",
    )
    args = parser.parse_args(argv)
    return execute(
        project_root=args.project_root,
        config_path=args.config,
        protocol_root=args.protocol_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
