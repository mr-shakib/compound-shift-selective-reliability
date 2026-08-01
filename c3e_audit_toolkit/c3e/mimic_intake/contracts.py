"""Strict contracts for the C3-E6 Stage 3A metadata-readiness gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml


class IntakeContractError(ValueError):
    """Raised when Stage 3A configuration or output violates its contract."""


class GateStatus(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    FAIL = "FAIL"


DECLARATIONS = (
    "STAGE 3A ONLY",
    "METADATA AND ACCESS INVENTORY",
    "NO MEDICAL IMAGES OPENED",
    "NO REPORT TEXT EXPORTED",
    "NO MODEL TRAINING",
    "NO CHEXBERT EXECUTION",
    "NO EXTERNAL DATA ACCESSED",
    "NO TARGET-SITE TUNING",
)

ALLOWED_OUTPUT_FILENAMES = (
    "file_inventory.json",
    "file_inventory.csv",
    "access_gate_report.json",
    "access_gate_report.md",
    "safe_artifact_hashes.sha256",
    "environment.txt",
)

RESOURCE_CATEGORIES = (
    "report_resource",
    "study_metadata",
    "image_metadata",
    "official_split_definition",
    "official_auxiliary_labels",
    "image_file",
    "unknown",
    "archive",
    "checksum_or_manifest",
)

_KNOWN_CONFIG_FIELDS = {
    "stage",
    "data_root",
    "output_dir",
    "required_categories",
    "resource_patterns",
    "image_extensions",
    "archive_extensions",
    "max_scan_depth",
    "max_entries",
    "hash_chunk_size",
}


def _relative_path(value: Any, field: str, expected: str | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntakeContractError(f"{field} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise IntakeContractError(f"{field} must not be absolute or traverse parents")
    normalized = path.as_posix().rstrip("/")
    if expected is not None and normalized != expected:
        raise IntakeContractError(f"{field} must be {expected!r}")
    return normalized


def _extensions(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise IntakeContractError(f"{field} must be a non-empty list")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.startswith(".") or "/" in item:
            raise IntakeContractError(f"invalid extension in {field}: {item!r}")
        result.append(item.lower())
    if len(result) != len(set(result)):
        raise IntakeContractError(f"{field} contains duplicates")
    return tuple(result)


@dataclass(frozen=True)
class IntakeConfig:
    data_root: str
    output_dir: str
    required_categories: tuple[str, ...]
    resource_patterns: Mapping[str, tuple[str, ...]]
    image_extensions: tuple[str, ...]
    archive_extensions: tuple[str, ...]
    max_scan_depth: int
    max_entries: int
    hash_chunk_size: int

    def resolve_data_root(self, project_root: Path) -> Path:
        return project_root / self.data_root

    def resolve_output_dir(self, project_root: Path) -> Path:
        return project_root / self.output_dir


def validate_intake_config(raw: Any) -> IntakeConfig:
    if not isinstance(raw, dict):
        raise IntakeContractError("config root must be a mapping")
    unknown = sorted(set(raw) - _KNOWN_CONFIG_FIELDS)
    if unknown:
        raise IntakeContractError(f"unknown config fields: {unknown}")
    missing = sorted(_KNOWN_CONFIG_FIELDS - set(raw))
    if missing:
        raise IntakeContractError(f"missing config fields: {missing}")
    if raw["stage"] != "C3-E6 Stage 3A":
        raise IntakeContractError("stage must be 'C3-E6 Stage 3A'")

    data_root = _relative_path(raw["data_root"], "data_root", "data/mimic")
    output_dir = _relative_path(
        raw["output_dir"], "output_dir", "results/c3e_mimic/intake"
    )

    required = raw["required_categories"]
    if not isinstance(required, list) or not required:
        raise IntakeContractError("required_categories must be a non-empty list")
    invalid_required = sorted(set(required) - set(RESOURCE_CATEGORIES))
    if invalid_required:
        raise IntakeContractError(f"unknown required categories: {invalid_required}")
    if "image_file" in required:
        raise IntakeContractError("image files cannot be required by Stage 3A")

    patterns = raw["resource_patterns"]
    if not isinstance(patterns, dict) or not patterns:
        raise IntakeContractError("resource_patterns must be a non-empty mapping")
    unknown_categories = sorted(set(patterns) - set(RESOURCE_CATEGORIES))
    if unknown_categories:
        raise IntakeContractError(f"unknown resource pattern categories: {unknown_categories}")
    normalized_patterns: dict[str, tuple[str, ...]] = {}
    for category, values in patterns.items():
        if category in {"image_file", "unknown", "archive"}:
            raise IntakeContractError(f"{category} is classified by policy, not patterns")
        if not isinstance(values, list) or not values:
            raise IntakeContractError(f"resource_patterns.{category} must be a non-empty list")
        checked = []
        for pattern in values:
            if not isinstance(pattern, str) or not pattern or Path(pattern).is_absolute():
                raise IntakeContractError(f"unsafe pattern for {category}: {pattern!r}")
            if ".." in PurePosixPath(pattern).parts:
                raise IntakeContractError(f"unsafe parent traversal pattern: {pattern!r}")
            checked.append(pattern.lower())
        normalized_patterns[category] = tuple(checked)

    def bounded_int(field: str, minimum: int, maximum: int) -> int:
        value = raw[field]
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise IntakeContractError(f"{field} must be an integer in [{minimum}, {maximum}]")
        return value

    return IntakeConfig(
        data_root=data_root,
        output_dir=output_dir,
        required_categories=tuple(required),
        resource_patterns=normalized_patterns,
        image_extensions=_extensions(raw["image_extensions"], "image_extensions"),
        archive_extensions=_extensions(raw["archive_extensions"], "archive_extensions"),
        max_scan_depth=bounded_int("max_scan_depth", 1, 8),
        max_entries=bounded_int("max_entries", 1, 1_000_000),
        hash_chunk_size=bounded_int("hash_chunk_size", 4096, 16 * 1024 * 1024),
    )


def load_intake_config(path: str | Path) -> IntakeConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise IntakeContractError(f"could not load intake config: {type(exc).__name__}") from exc
    return validate_intake_config(raw)
