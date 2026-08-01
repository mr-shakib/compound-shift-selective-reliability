from pathlib import Path
import subprocess

import pytest

from c3e.mimic_intake.contracts import IntakeContractError, validate_intake_config
from c3e.mimic_intake.inventory import build_inventory


def test_corrupted_and_unsafe_config_is_rejected():
    with pytest.raises(IntakeContractError, match="missing config fields"):
        validate_intake_config({"stage": "C3-E6 Stage 3A"})
    with pytest.raises(IntakeContractError, match="must be 'results/c3e_mimic/intake'"):
        validate_intake_config(
            {
                "stage": "C3-E6 Stage 3A",
                "data_root": "data/mimic",
                "output_dir": "data/mimic/unsafe-output",
                "required_categories": ["report_resource"],
                "resource_patterns": {"report_resource": ["*report*"]},
                "image_extensions": [".jpg"],
                "archive_extensions": [".zip"],
                "max_scan_depth": 1,
                "max_entries": 1,
                "hash_chunk_size": 4096,
            }
        )


def test_symbolic_link_is_a_contract_failure(empty_data_root: Path, intake_config):
    outside = empty_data_root.parent / "outside.bin"
    outside.write_bytes(b"synthetic")
    (empty_data_root / "unsafe-link").symlink_to(outside)
    inventory = build_inventory(empty_data_root, intake_config)
    assert inventory.contract_errors == ("symbolic links are forbidden under data/mimic",)


def test_frozen_protocol_manifest_remains_valid_after_stage3a_inventory(
    empty_data_root: Path, intake_config
):
    project_root = Path(__file__).resolve().parents[3]
    protocol_root = project_root / "protocols" / "C3E6_stage2"
    before = subprocess.run(
        ["sha256sum", "-c", "MANIFEST.sha256"],
        cwd=protocol_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert before.returncode == 0, before.stdout + before.stderr
    build_inventory(empty_data_root, intake_config)
    after = subprocess.run(
        ["sha256sum", "-c", "MANIFEST.sha256"],
        cwd=protocol_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert after.returncode == 0, after.stdout + after.stderr
