from __future__ import annotations

from pathlib import Path

import pytest

from c3e.mimic_intake.contracts import IntakeConfig, validate_intake_config


@pytest.fixture
def intake_config() -> IntakeConfig:
    return validate_intake_config(
        {
            "stage": "C3-E6 Stage 3A",
            "data_root": "data/mimic",
            "output_dir": "results/c3e_mimic/intake",
            "required_categories": [
                "report_resource",
                "image_metadata",
                "official_split_definition",
                "checksum_or_manifest",
            ],
            "resource_patterns": {
                "official_split_definition": ["**/*split*.csv.gz", "*split*.csv.gz"],
                "official_auxiliary_labels": ["**/*chexpert*.csv.gz"],
                "checksum_or_manifest": ["**/*manifest*", "*.sha256"],
                "study_metadata": ["**/*study*metadata*.csv.gz"],
                "image_metadata": ["**/*metadata*.csv.gz", "*metadata*.csv.gz"],
                "report_resource": ["**/*report*.zip", "reports/**/*.txt"],
            },
            "image_extensions": [".dcm", ".dicom", ".jpg", ".jpeg", ".png"],
            "archive_extensions": [".zip", ".tar", ".tar.gz", ".gz"],
            "max_scan_depth": 4,
            "max_entries": 1000,
            "hash_chunk_size": 4096,
        }
    )


@pytest.fixture
def empty_data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data" / "mimic"
    root.mkdir(parents=True)
    return root
