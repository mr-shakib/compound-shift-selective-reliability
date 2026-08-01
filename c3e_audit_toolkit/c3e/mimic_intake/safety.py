"""Safe-output enforcement for Stage 3A inventory artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .contracts import ALLOWED_OUTPUT_FILENAMES, IntakeContractError


_UNSAFE_KEYS = {
    "absolute_path",
    "report_text",
    "report_body",
    "patient_id",
    "subject_id",
    "study_id",
    "image_id",
    "dicom_id",
    "findings",
    "impression",
    "full_report",
    "context_text",
}
_RESTRICTED_VALUE = re.compile(
    r"(?:patient|subject|study|image)\d+|(?:^|[/\\])[ps]\d{3,}(?:[/\\]|\.|$)",
    re.IGNORECASE,
)


def validate_safe_payload(value: Any, *, project_root: Path | None = None) -> None:
    """Reject fields and strings that could expose restricted row-level content."""
    root_text = str(project_root.resolve()) if project_root is not None else None

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            unsafe = set(item) & _UNSAFE_KEYS
            if unsafe:
                raise IntakeContractError(f"unsafe output fields rejected: {sorted(unsafe)}")
            for nested in item.values():
                walk(nested)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                walk(nested)
        elif isinstance(item, str):
            if root_text and root_text in item:
                raise IntakeContractError("absolute project or restricted-data path in safe output")
            if _RESTRICTED_VALUE.search(item):
                raise IntakeContractError("patient/study/image-level value in safe output")

    walk(value)


def audit_output_directory(output_dir: Path, *, project_root: Path) -> None:
    names = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    if names != sorted(ALLOWED_OUTPUT_FILENAMES):
        raise IntakeContractError(f"unexpected Stage 3A output files: {names}")
    root_text = str(project_root.resolve())
    for path in sorted(output_dir.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if root_text in text:
            raise IntakeContractError(f"absolute project path leaked into {path.name}")
        if _RESTRICTED_VALUE.search(text):
            raise IntakeContractError(f"restricted row-level value detected in {path.name}")
        if path.suffix == ".json":
            validate_safe_payload(json.loads(text), project_root=project_root)
