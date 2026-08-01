"""Deterministic, metadata-first resource inventory for MIMIC Stage 3A."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import fnmatch
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
from typing import Iterator

from .contracts import IntakeConfig, IntakeContractError


_CATEGORY_PRIORITY = (
    "official_split_definition",
    "official_auxiliary_labels",
    "checksum_or_manifest",
    "study_metadata",
    "image_metadata",
    "report_resource",
)
_RESTRICTED_PATH = re.compile(
    r"(?:^|/)(?:patient|study|subject|image|p|s)?\d{3,}(?:/|\.|$)", re.IGNORECASE
)


@dataclass(frozen=True)
class InventoryRecord:
    resource_key: str
    relative_path: str | None
    category: str
    file_type: str
    byte_size: int | None
    modification_time_utc: str | None
    sha256: str | None
    availability: str
    content_access: str
    observed_count: int
    truncated: bool

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class InventoryResult:
    records: tuple[InventoryRecord, ...]
    category_counts: dict[str, int]
    scan_truncated: bool
    entries_examined: int
    contract_errors: tuple[str, ...]


def _suffix(path: Path) -> str:
    return "".join(path.suffixes).lower()


def _matches(relative_path: str, pattern: str) -> bool:
    rel = relative_path.lower()
    name = PurePosixPath(rel).name
    return fnmatch.fnmatchcase(rel, pattern) or fnmatch.fnmatchcase(name, pattern)


def classify_file(relative_path: str, config: IntakeConfig) -> str:
    """Classify from a relative name only; this function never opens a file."""
    path = Path(relative_path)
    suffix = _suffix(path)
    if any(suffix.endswith(ext) for ext in config.image_extensions):
        return "image_file"
    for category in _CATEGORY_PRIORITY:
        for pattern in config.resource_patterns.get(category, ()):
            if _matches(relative_path, pattern):
                return category
    if any(suffix.endswith(ext) for ext in config.archive_extensions):
        return "archive"
    return "unknown"


def hash_non_image_file(path: Path, *, chunk_size: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=UTC).isoformat().replace("+00:00", "Z")


def _iter_files(root: Path, *, max_depth: int, max_entries: int) -> Iterator[tuple[Path, os.stat_result]]:
    examined = 0
    pending: list[tuple[Path, int]] = [(root, 0)]
    while pending:
        directory, depth = pending.pop()
        try:
            with os.scandir(directory) as scan:
                entries = sorted(scan, key=lambda entry: entry.name)
        except OSError as exc:
            raise IntakeContractError(
                f"directory metadata unavailable under restricted data root: {type(exc).__name__}"
            ) from exc
        child_dirs: list[Path] = []
        for entry in entries:
            examined += 1
            if examined > max_entries:
                return examined - 1
            try:
                if entry.is_symlink():
                    raise IntakeContractError("symbolic links are forbidden under data/mimic")
                if entry.is_dir(follow_symlinks=False):
                    if depth < max_depth:
                        child_dirs.append(Path(entry.path))
                    continue
                if entry.is_file(follow_symlinks=False):
                    yield Path(entry.path), entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise IntakeContractError(
                    f"file metadata unavailable under restricted data root: {type(exc).__name__}"
                ) from exc
        for child in reversed(child_dirs):
            pending.append((child, depth + 1))


def _safe_path(relative_path: str) -> str | None:
    return None if _RESTRICTED_PATH.search(relative_path) else relative_path


def build_inventory(data_root: Path, config: IntakeConfig) -> InventoryResult:
    """Inventory resource metadata, blocking image and report-text content access."""
    if not data_root.exists():
        return InventoryResult((), {}, False, 0, ())
    if not data_root.is_dir():
        return InventoryResult((), {}, False, 0, ("data/mimic is not a directory",))
    if data_root.is_symlink():
        return InventoryResult((), {}, False, 0, ("data/mimic must not be a symbolic link",))

    records: list[InventoryRecord] = []
    image_count = 0
    image_bytes = 0
    report_text_count = 0
    report_text_bytes = 0
    report_text_unreadable = 0
    examined = 0
    truncated = False
    errors: list[str] = []

    try:
        iterator = _iter_files(
            data_root, max_depth=config.max_scan_depth, max_entries=config.max_entries
        )
        while True:
            try:
                path, stat = next(iterator)
                examined += 1
            except StopIteration as stop:
                if stop.value is not None:
                    truncated = True
                    examined = max(examined, int(stop.value))
                break
            relative = path.relative_to(data_root).as_posix()
            category = classify_file(relative, config)
            if category == "image_file":
                image_count += 1
                image_bytes += int(stat.st_size)
                continue
            if category == "report_resource" and path.suffix.lower() == ".txt":
                report_text_count += 1
                report_text_bytes += int(stat.st_size)
                if stat.st_mode & 0o444 == 0:
                    report_text_unreadable += 1
                continue

            safe_path = _safe_path(relative)
            try:
                digest = hash_non_image_file(path, chunk_size=config.hash_chunk_size)
            except OSError as exc:
                errors.append(
                    "non-image resource was not readable for checksum: "
                    f"{type(exc).__name__}"
                )
                break
            records.append(
                InventoryRecord(
                    resource_key=f"resource_{len(records) + 1:04d}",
                    relative_path=safe_path,
                    category=category,
                    file_type=_suffix(path) or "no_extension",
                    byte_size=int(stat.st_size),
                    modification_time_utc=_timestamp(stat.st_mtime),
                    sha256=digest,
                    availability="available_readable",
                    content_access="checksum_only",
                    observed_count=1,
                    truncated=False,
                )
            )
    except IntakeContractError as exc:
        errors.append(str(exc))

    if report_text_count:
        records.append(
            InventoryRecord(
                resource_key="report_text_aggregate",
                relative_path=None,
                category="report_resource",
                file_type="extracted_report_text_aggregate",
                byte_size=report_text_bytes,
                modification_time_utc=None,
                sha256=None,
                availability=(
                    "available_readable_metadata"
                    if report_text_unreadable == 0
                    else "present_not_readable"
                ),
                content_access="blocked_report_text",
                observed_count=report_text_count,
                truncated=truncated,
            )
        )
    if image_count:
        records.append(
            InventoryRecord(
                resource_key="image_file_aggregate",
                relative_path=None,
                category="image_file",
                file_type="medical_image_aggregate",
                byte_size=image_bytes,
                modification_time_utc=None,
                sha256=None,
                availability="metadata_only",
                content_access="blocked_medical_image",
                observed_count=image_count,
                truncated=truncated,
            )
        )

    records.sort(key=lambda item: (item.category, item.relative_path or "", item.resource_key))
    # Resource keys are deliberately generic and assigned after stable sorting.
    stable_records = []
    for index, record in enumerate(records, start=1):
        stable_records.append(
            InventoryRecord(**{**record.as_dict(), "resource_key": f"resource_{index:04d}"})
        )
    counts: dict[str, int] = {}
    for record in stable_records:
        counts[record.category] = counts.get(record.category, 0) + record.observed_count
    return InventoryResult(
        records=tuple(stable_records),
        category_counts=dict(sorted(counts.items())),
        scan_truncated=truncated,
        entries_examined=examined,
        contract_errors=tuple(errors),
    )
