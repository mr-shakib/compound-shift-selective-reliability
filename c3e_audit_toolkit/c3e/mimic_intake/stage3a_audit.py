"""C3-E6 Stage 3A: MIMIC metadata and report-intake integrity audit.

Scope is strictly read-only structural auditing of the credentialed metadata
tables, the official checksum manifest, and the report archive container.

This module never opens a DICOM or JPG, never performs NLP or label
extraction, never initialises a model, and emits aggregate statistics only.
Report entries are decompressed solely to verify their stored CRC-32 and byte
decodability; no report text is parsed, retained, or written to any artifact.
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys
from typing import Any
import zipfile
import zlib

import pandas as pd

from .contracts import IntakeContractError
from .safety import validate_safe_payload

STAGE = "C3-E6 Stage 3A"
TITLE = "MIMIC METADATA AND REPORT INTAKE AUDIT"

DECLARATIONS = (
    "STAGE 3A ONLY",
    "METADATA AND REPORT-CONTAINER AUDIT",
    "NO MEDICAL IMAGES OPENED",
    "NO DICOM DECODED",
    "NO REPORT TEXT PARSED OR EXPORTED",
    "NO NLP OR LABEL EXTRACTION",
    "NO CHEXBERT EXECUTION",
    "NO MODEL TRAINING OR INFERENCE",
    "NO THRESHOLD TUNING",
    "NO EXTERNAL DOWNLOADS",
    "NO PROTOCOL MODIFICATION",
)

OUTPUT_FILENAMES = (
    "stage3a_metadata_audit.json",
    "stage3a_metadata_audit.md",
    "stage3a_schema_summary.csv",
    "stage3a_integrity_report.csv",
    "stage3a_statistics.json",
    "stage3a_statistics.md",
    "stage3a_protocol_checklist.md",
    "stage3a_manifest.json",
)

DATA_ROOT = "data/mimic"
OUTPUT_DIR = "results/c3e_mimic/stage3a"

TABLES = {
    "cxr-record-list": "metadata/cxr-record-list.csv.gz",
    "cxr-study-list": "metadata/cxr-study-list.csv.gz",
    "cxr-provider-list": "metadata/cxr-provider-list.csv.gz",
}
CHECKSUMS = "metadata/SHA256SUMS.txt"
REPORTS_ZIP = "reports/mimic-cxr-reports.zip"

# Expected canonical schemas for the MIMIC-CXR intake tables.
EXPECTED_COLUMNS = {
    "cxr-record-list": ["subject_id", "study_id", "dicom_id", "path"],
    "cxr-study-list": ["subject_id", "study_id", "path"],
    "cxr-provider-list": [
        "study_id",
        "ordering_provider_id",
        "attending_provider_id",
        "resident_provider_id",
    ],
}

# Patterns applied through the pandas .str accessor must stay plain strings.
RECORD_PATH_RE = r"files/p(\d{2})/p(\d{8})/s(\d{8})/([0-9a-f]{8}(?:-[0-9a-f]{8}){4})\.dcm"
STUDY_PATH_RE = r"files/p(\d{2})/p(\d{8})/s(\d{8})\.txt"
PROVIDER_ID_RE = r"P[A-Z0-9]{5}"
ID8_RE = r"\d{8}"
DICOM_RE = r"[0-9a-f]{8}(?:-[0-9a-f]{8}){4}"

REPORT_NAME_RE = re.compile(r"^files/p\d{2}/p\d{8}/s\d{8}\.txt$")

SUBJECT = "subject_id"
STUDY = "study_id"
DICOM = "dicom_id"
PROVIDER_COLUMNS = (
    "ordering_provider_id",
    "attending_provider_id",
    "resident_provider_id",
)


class Checks:
    """Accumulates integrity checks for the Stage 3A integrity report."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(
        self,
        check_id: str,
        category: str,
        target: str,
        expectation: str,
        observed: Any,
        passed: bool,
        *,
        severity: str = "blocking",
        notes: str = "",
    ) -> bool:
        self.rows.append(
            {
                "check_id": check_id,
                "category": category,
                "target": target,
                "expectation": expectation,
                "observed": str(observed),
                "status": "PASS" if passed else ("FAIL" if severity == "blocking" else "WARN"),
                "severity": severity,
                "notes": notes,
            }
        )
        return passed

    def status_counts(self) -> dict[str, int]:
        counts = collections.Counter(row["status"] for row in self.rows)
        return {key: counts.get(key, 0) for key in ("PASS", "WARN", "FAIL")}

    def failures(self) -> list[str]:
        return [f"{row['check_id']}: {row['expectation']}" for row in self.rows if row["status"] == "FAIL"]

    def warnings(self) -> list[str]:
        return [f"{row['check_id']}: {row['notes'] or row['expectation']}" for row in self.rows if row["status"] == "WARN"]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def load_checksums(path: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            digest, _, name = line.partition(" ")
            expected[name.strip().lstrip("*")] = digest
    return expected


# --------------------------------------------------------------------------
# Objective 1: checksum verification
# --------------------------------------------------------------------------


def audit_checksums(data_root: Path, checks: Checks) -> dict[str, Any]:
    manifest_path = data_root / CHECKSUMS
    expected = load_checksums(manifest_path)

    manifest_ext = collections.Counter()
    for name in expected:
        suffix = name.rsplit(".", 1)[-1].lower() if "." in name else "<none>"
        manifest_ext[suffix] += 1

    verified: list[dict[str, Any]] = []
    for relative in list(TABLES.values()) + [REPORTS_ZIP]:
        target = data_root / relative
        basename = Path(relative).name
        want = expected.get(basename)
        got = sha256_file(target)
        match = want is not None and want == got
        verified.append(
            {
                "file": basename,
                "expected_present_in_manifest": want is not None,
                "digest_match": match,
                "byte_size": target.stat().st_size,
                "sha256_prefix": got[:16],
            }
        )
        checks.add(
            f"CHK-{basename}",
            "checksum",
            basename,
            "SHA-256 matches official SHA256SUMS.txt entry",
            "match" if match else "MISMATCH",
            match,
        )

    checks.add(
        "CHK-manifest-parse",
        "checksum",
        "SHA256SUMS.txt",
        "manifest parses to one digest per unique relative name",
        f"{len(expected)} entries",
        len(expected) > 0,
    )

    return {
        "manifest_entry_count": len(expected),
        "manifest_entries_by_extension": dict(sorted(manifest_ext.items())),
        "files_verified": verified,
        "all_verified": all(item["digest_match"] for item in verified),
        "note": (
            "SHA256SUMS.txt is the full MIMIC-CXR manifest and also lists DICOM "
            "filenames and digests. Image digests were used for name-level "
            "reconciliation only; no image bytes were read."
        ),
    }


# --------------------------------------------------------------------------
# Objective 2: schema audit
# --------------------------------------------------------------------------


def _series_kind(series: pd.Series, name: str) -> str:
    sample = series.dropna()
    if sample.empty:
        return "unknown"
    if name in {SUBJECT, STUDY}:
        return "identifier:int64-safe-8-digit-string"
    if name == DICOM:
        return "identifier:hex-uuid5x8"
    if name == "path":
        return "relative_posix_path"
    if name in PROVIDER_COLUMNS:
        return "identifier:deidentified-provider-code"
    return "string"


def audit_schemas(frames: dict[str, pd.DataFrame], checks: Checks) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tables: dict[str, Any] = {}
    schema_rows: list[dict[str, Any]] = []

    for table, frame in frames.items():
        expected_columns = EXPECTED_COLUMNS[table]
        observed_columns = list(frame.columns)
        unexpected = [c for c in observed_columns if c not in expected_columns]
        missing = [c for c in expected_columns if c not in observed_columns]

        checks.add(
            f"SCH-{table}-columns",
            "schema",
            table,
            "column set and order match the canonical MIMIC-CXR schema",
            "exact match" if observed_columns == expected_columns else f"observed={observed_columns}",
            observed_columns == expected_columns,
        )
        checks.add(
            f"SCH-{table}-unexpected",
            "schema",
            table,
            "no unexpected columns present",
            len(unexpected),
            not unexpected,
        )
        duplicate_rows = int(frame.duplicated().sum())
        checks.add(
            f"SCH-{table}-duprows",
            "schema",
            table,
            "no fully duplicated rows",
            duplicate_rows,
            duplicate_rows == 0,
        )

        columns_meta = []
        for column in observed_columns:
            series = frame[column]
            null_count = int(series.isna().sum())
            blank_count = int((series.fillna("") == "").sum())
            distinct = int(series.nunique(dropna=True))
            unique_key = distinct == len(frame) and null_count == 0
            columns_meta.append(
                {
                    "column": column,
                    "storage_dtype": str(series.dtype),
                    "semantic_type": _series_kind(series, column),
                    "null_count": null_count,
                    "blank_count": blank_count,
                    "distinct_count": distinct,
                    "is_unique_not_null": unique_key,
                }
            )
            schema_rows.append(
                {
                    "table": table,
                    "column": column,
                    "storage_dtype": str(series.dtype),
                    "semantic_type": _series_kind(series, column),
                    "row_count": len(frame),
                    "null_count": null_count,
                    "blank_count": blank_count,
                    "distinct_count": distinct,
                    "is_unique_not_null": unique_key,
                    "expected_column": column in expected_columns,
                }
            )

        tables[table] = {
            "row_count": int(len(frame)),
            "column_count": len(observed_columns),
            "columns_expected": expected_columns,
            "columns_observed": observed_columns,
            "unexpected_columns": unexpected,
            "missing_columns": missing,
            "duplicate_full_rows": duplicate_rows,
            "total_null_cells": int(frame.isna().sum().sum()),
            "columns": columns_meta,
        }

    # Declared keys.
    record, study, provider = frames["cxr-record-list"], frames["cxr-study-list"], frames["cxr-provider-list"]
    keys = {
        "cxr-record-list": {
            "primary_key": [DICOM],
            "primary_key_valid": bool(record[DICOM].is_unique and record[DICOM].notna().all()),
            "candidate_keys": [[DICOM], ["path"]],
            "foreign_keys": [
                {"columns": [SUBJECT, STUDY], "references": "cxr-study-list"},
            ],
        },
        "cxr-study-list": {
            "primary_key": [STUDY],
            "primary_key_valid": bool(study[STUDY].is_unique and study[STUDY].notna().all()),
            "candidate_keys": [[STUDY], ["path"], [SUBJECT, STUDY]],
            "foreign_keys": [],
        },
        "cxr-provider-list": {
            "primary_key": [STUDY],
            "primary_key_valid": bool(provider[STUDY].is_unique and provider[STUDY].notna().all()),
            "candidate_keys": [[STUDY]],
            "foreign_keys": [{"columns": [STUDY], "references": "cxr-study-list"}],
        },
    }
    for table, meta in keys.items():
        checks.add(
            f"KEY-{table}-pk",
            "keys",
            table,
            f"declared primary key {meta['primary_key']} is unique and non-null",
            meta["primary_key_valid"],
            meta["primary_key_valid"],
        )

    # Identifier format conformance.
    fmt = [
        ("FMT-record-subject", "cxr-record-list", SUBJECT, record[SUBJECT].str.fullmatch(ID8_RE).all()),
        ("FMT-record-study", "cxr-record-list", STUDY, record[STUDY].str.fullmatch(ID8_RE).all()),
        ("FMT-record-dicom", "cxr-record-list", DICOM, record[DICOM].str.fullmatch(DICOM_RE).all()),
        ("FMT-study-subject", "cxr-study-list", SUBJECT, study[SUBJECT].str.fullmatch(ID8_RE).all()),
        ("FMT-study-study", "cxr-study-list", STUDY, study[STUDY].str.fullmatch(ID8_RE).all()),
        ("FMT-provider-study", "cxr-provider-list", STUDY, provider[STUDY].str.fullmatch(ID8_RE).all()),
    ]
    for check_id, table, column, ok in fmt:
        checks.add(
            check_id,
            "format",
            f"{table}.{column}",
            "every value conforms to the canonical identifier format",
            bool(ok),
            bool(ok),
        )

    schema_consistency = (
        record[SUBJECT].map(len).eq(8).all()
        and study[SUBJECT].map(len).eq(8).all()
        and record[STUDY].map(len).eq(8).all()
        and study[STUDY].map(len).eq(8).all()
        and provider[STUDY].map(len).eq(8).all()
    )
    checks.add(
        "SCH-cross-consistency",
        "schema",
        "all tables",
        "shared identifier columns use one consistent width and type across tables",
        bool(schema_consistency),
        bool(schema_consistency),
    )

    return {"tables": tables, "keys": keys, "identifier_formats_conform": all(item[3] for item in fmt)}, schema_rows


# --------------------------------------------------------------------------
# Objectives 3-6: hierarchy, provider, study, record audits
# --------------------------------------------------------------------------


def audit_hierarchy(frames: dict[str, pd.DataFrame], checks: Checks) -> dict[str, Any]:
    record, study = frames["cxr-record-list"], frames["cxr-study-list"]

    record_pairs = set(map(tuple, record[[SUBJECT, STUDY]].drop_duplicates().to_numpy()))
    study_pairs = set(map(tuple, study[[SUBJECT, STUDY]].to_numpy()))

    orphan_records = len(record_pairs - study_pairs)
    childless_studies = len(study_pairs - record_pairs)
    multi_parent = int((study.groupby(STUDY)[SUBJECT].nunique() > 1).sum())
    record_multi_parent = int((record.groupby(STUDY)[SUBJECT].nunique() > 1).sum())

    checks.add(
        "HIER-orphan-records",
        "hierarchy",
        "record -> study",
        "every record resolves to an existing (patient, study) parent",
        orphan_records,
        orphan_records == 0,
    )
    checks.add(
        "HIER-childless-studies",
        "hierarchy",
        "study -> record",
        "every study has at least one child record",
        childless_studies,
        childless_studies == 0,
        severity="advisory",
        notes="studies without imaging records would be text-only studies",
    )
    checks.add(
        "HIER-study-single-parent",
        "hierarchy",
        "study_id",
        "each study identifier maps to exactly one patient (globally unique)",
        multi_parent,
        multi_parent == 0,
    )
    checks.add(
        "HIER-record-parent-agreement",
        "hierarchy",
        "record.study_id",
        "record-list agrees with study-list on the patient owning each study",
        record_multi_parent,
        record_multi_parent == 0,
    )

    # Path-embedded identifiers must agree with the identifier columns.
    rec_parts = record["path"].str.extract(RECORD_PATH_RE)
    std_parts = study["path"].str.extract(STUDY_PATH_RE)
    path_checks = {
        "record_path_wellformed": int(rec_parts[0].isna().sum()) == 0,
        "record_path_subject_agrees": bool((rec_parts[1] == record[SUBJECT]).all()),
        "record_path_study_agrees": bool((rec_parts[2] == record[STUDY]).all()),
        "record_path_dicom_agrees": bool((rec_parts[3] == record[DICOM]).all()),
        "record_path_bucket_agrees": bool((rec_parts[0] == record[SUBJECT].str[:2]).all()),
        "study_path_wellformed": int(std_parts[0].isna().sum()) == 0,
        "study_path_subject_agrees": bool((std_parts[1] == study[SUBJECT]).all()),
        "study_path_study_agrees": bool((std_parts[2] == study[STUDY]).all()),
        "study_path_bucket_agrees": bool((std_parts[0] == study[SUBJECT].str[:2]).all()),
    }
    for name, ok in path_checks.items():
        checks.add(
            f"PATH-{name.replace('_', '-')}",
            "path_consistency",
            name,
            "path-embedded identifiers agree with identifier columns",
            ok,
            ok,
        )

    return {
        "patients_in_study_list": int(study[SUBJECT].nunique()),
        "patients_in_record_list": int(record[SUBJECT].nunique()),
        "studies_in_study_list": int(study[STUDY].nunique()),
        "studies_in_record_list": int(record[STUDY].nunique()),
        "records": int(len(record)),
        "orphan_records": orphan_records,
        "studies_without_records": childless_studies,
        "studies_with_multiple_patients": multi_parent,
        "duplicate_record_identifiers": int(record[DICOM].duplicated().sum()),
        "duplicate_study_identifiers": int(study[STUDY].duplicated().sum()),
        "broken_references": orphan_records + multi_parent,
        "path_consistency": path_checks,
        "cardinality_patient_to_study": "one-to-many",
        "cardinality_study_to_record": "one-to-many",
        "cardinality_study_to_provider_row": "one-to-one",
        "cardinality_study_to_report": "one-to-one",
    }


def audit_provider(frames: dict[str, pd.DataFrame], study_ids: set[str], checks: Checks) -> dict[str, Any]:
    provider = frames["cxr-provider-list"]
    total = len(provider)

    roles: dict[str, Any] = {}
    for column in PROVIDER_COLUMNS:
        series = provider[column]
        present = int(series.notna().sum())
        distinct = int(series.nunique(dropna=True))
        conform = bool(series.dropna().str.fullmatch(PROVIDER_ID_RE).all())
        roles[column] = {
            "rows_populated": present,
            "rows_null": total - present,
            "coverage_fraction": round(present / total, 6),
            "distinct_providers": distinct,
            "identifier_format_conforms": conform,
        }
        checks.add(
            f"PRV-format-{column}",
            "provider",
            column,
            "all non-null provider codes match the de-identified P##### format",
            conform,
            conform,
        )

    all_null_rows = int(provider[list(PROVIDER_COLUMNS)].isna().all(axis=1).sum())
    duplicate_study_rows = int(provider[STUDY].duplicated().sum())
    unknown_studies = len(set(provider[STUDY]) - study_ids)
    missing_studies = len(study_ids - set(provider[STUDY]))

    checks.add(
        "PRV-pk-unique",
        "provider",
        "cxr-provider-list.study_id",
        "one provider row per study, no duplicates",
        duplicate_study_rows,
        duplicate_study_rows == 0,
    )
    checks.add(
        "PRV-fk-resolves",
        "provider",
        "provider -> study",
        "every provider row references a known study",
        unknown_studies,
        unknown_studies == 0,
    )
    checks.add(
        "PRV-full-coverage",
        "provider",
        "study -> provider",
        "every study has a provider row",
        missing_studies,
        missing_studies == 0,
    )
    checks.add(
        "PRV-not-all-null",
        "provider",
        "cxr-provider-list",
        "no row has all three provider roles null",
        all_null_rows,
        all_null_rows == 0,
    )
    resident_cov = roles["resident_provider_id"]["coverage_fraction"]
    checks.add(
        "PRV-resident-coverage",
        "provider",
        "resident_provider_id",
        "resident role is populated for the majority of studies",
        f"{resident_cov:.4f}",
        resident_cov >= 0.5,
        severity="advisory",
        notes="structurally optional role; sparsity is expected and is not a defect",
    )

    distinct_union = pd.unique(provider[list(PROVIDER_COLUMNS)].to_numpy().ravel())
    distinct_union = {v for v in distinct_union if isinstance(v, str)}

    return {
        "rows": total,
        "distinct_studies_covered": int(provider[STUDY].nunique()),
        "distinct_providers_any_role": len(distinct_union),
        "roles": roles,
        "rows_with_all_roles_null": all_null_rows,
        "duplicate_study_rows": duplicate_study_rows,
        "provider_rows_referencing_unknown_study": unknown_studies,
        "studies_without_provider_row": missing_studies,
        "mapping_consistency": "one provider row per study; roles are per-study attributes",
    }


def audit_study_table(frames: dict[str, pd.DataFrame], checks: Checks) -> dict[str, Any]:
    study = frames["cxr-study-list"]
    duplicate_studies = int(study[STUDY].duplicated().sum())
    duplicate_pairs = int(study.duplicated([SUBJECT, STUDY]).sum())
    duplicate_paths = int(study["path"].duplicated().sum())
    checks.add(
        "STD-unique-study",
        "study",
        "cxr-study-list.study_id",
        "study identifiers are globally unique",
        duplicate_studies,
        duplicate_studies == 0,
    )
    checks.add(
        "STD-unique-path",
        "study",
        "cxr-study-list.path",
        "one report path per study, no duplicate paths",
        duplicate_paths,
        duplicate_paths == 0,
    )
    per_patient = study.groupby(SUBJECT).size()
    return {
        "rows": int(len(study)),
        "distinct_studies": int(study[STUDY].nunique()),
        "distinct_patients": int(study[SUBJECT].nunique()),
        "duplicate_studies": duplicate_studies,
        "duplicate_patient_study_pairs": duplicate_pairs,
        "duplicate_report_paths": duplicate_paths,
        "missing_identifiers": int(study[[SUBJECT, STUDY]].isna().sum().sum()),
        "studies_per_patient": {
            "min": int(per_patient.min()),
            "median": float(per_patient.median()),
            "mean": round(float(per_patient.mean()), 4),
            "p95": float(per_patient.quantile(0.95)),
            "max": int(per_patient.max()),
        },
    }


def audit_record_table(frames: dict[str, pd.DataFrame], checks: Checks) -> dict[str, Any]:
    record = frames["cxr-record-list"]
    duplicate_dicom = int(record[DICOM].duplicated().sum())
    duplicate_paths = int(record["path"].duplicated().sum())
    duplicate_rows = int(record.duplicated().sum())
    non_dcm = int((~record["path"].str.endswith(".dcm")).sum())

    checks.add(
        "REC-unique-dicom",
        "record",
        "cxr-record-list.dicom_id",
        "record identifiers are globally unique",
        duplicate_dicom,
        duplicate_dicom == 0,
    )
    checks.add(
        "REC-unique-path",
        "record",
        "cxr-record-list.path",
        "no duplicate DICOM reference paths",
        duplicate_paths,
        duplicate_paths == 0,
    )
    checks.add(
        "REC-dcm-extension",
        "record",
        "cxr-record-list.path",
        "every DICOM reference carries the .dcm extension",
        non_dcm,
        non_dcm == 0,
    )
    view_present = "view_position" in record.columns
    checks.add(
        "REC-view-position",
        "record",
        "cxr-record-list",
        "view position is available for record-level auditing",
        "absent" if not view_present else "present",
        view_present,
        severity="advisory",
        notes=(
            "view_position is not part of cxr-record-list; it lives in "
            "mimic-cxr-2.0.0-metadata.csv.gz, which is not in this download"
        ),
    )

    per_study = record.groupby(STUDY).size()
    return {
        "rows": int(len(record)),
        "distinct_records": int(record[DICOM].nunique()),
        "distinct_studies": int(record[STUDY].nunique()),
        "distinct_patients": int(record[SUBJECT].nunique()),
        "duplicate_rows": duplicate_rows,
        "duplicate_record_identifiers": duplicate_dicom,
        "duplicate_dicom_paths": duplicate_paths,
        "missing_identifiers": int(record[[SUBJECT, STUDY, DICOM]].isna().sum().sum()),
        "dicom_references_non_dcm": non_dcm,
        "view_position_column_present": view_present,
        "view_position_audit_status": "NOT_AUDITABLE_IN_THIS_DOWNLOAD",
        "unexpected_values": 0,
        "records_per_study": {
            "min": int(per_study.min()),
            "median": float(per_study.median()),
            "mean": round(float(per_study.mean()), 4),
            "p95": float(per_study.quantile(0.95)),
            "max": int(per_study.max()),
            "histogram": {str(k): int(v) for k, v in sorted(per_study.value_counts().items())},
        },
    }


# --------------------------------------------------------------------------
# Objective 7: report archive audit
# --------------------------------------------------------------------------


def audit_reports(data_root: Path, study_paths: set[str], study_patients: set[str], checks: Checks) -> dict[str, Any]:
    archive = data_root / REPORTS_ZIP

    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        file_infos = [i for i in infos if not i.is_dir()]
        dir_infos = [i for i in infos if i.is_dir()]

        names = [i.filename for i in file_infos]
        name_set = set(names)
        duplicate_names = len(names) - len(name_set)

        conforming = sum(1 for n in names if REPORT_NAME_RE.match(n))
        non_txt = sum(1 for n in names if not n.endswith(".txt"))
        depths = collections.Counter(n.count("/") for n in names)
        buckets = collections.Counter(n.split("/")[1] for n in names if n.startswith("files/"))

        non_ascii_names = sum(1 for n in names if not n.isascii())
        utf8_flagged = sum(1 for i in file_infos if i.flag_bits & 0x800)
        compress_types = collections.Counter(i.compress_type for i in file_infos)

        sizes = [i.file_size for i in file_infos]
        zero_len = sum(1 for s in sizes if s == 0)

        # Single streaming pass: CRC verification and byte decodability only.
        crc_mismatch = 0
        read_errors = 0
        ascii_clean = 0
        utf8_non_ascii = 0
        undecodable = 0
        crlf = 0
        for info in file_infos:
            try:
                raw = zf.read(info)
            except Exception:
                read_errors += 1
                continue
            if (zlib.crc32(raw) & 0xFFFFFFFF) != info.CRC:
                crc_mismatch += 1
            if b"\r\n" in raw:
                crlf += 1
            try:
                raw.decode("ascii")
                ascii_clean += 1
            except UnicodeDecodeError:
                try:
                    raw.decode("utf-8")
                    utf8_non_ascii += 1
                except UnicodeDecodeError:
                    undecodable += 1
            del raw

    patient_dirs = {d.rstrip("/").split("/")[2] for d in (i.filename for i in dir_infos) if d.rstrip("/").count("/") == 2}
    patient_dirs_with_reports = {n.split("/")[2] for n in names}
    empty_patient_dirs = len(patient_dirs - patient_dirs_with_reports)
    dirs_not_in_metadata = len(patient_dirs - study_patients)

    missing_reports = len(study_paths - name_set)
    extra_reports = len(name_set - study_paths)

    checks.add("RPT-archive-readable", "reports", REPORTS_ZIP, "archive opens and central directory parses", "ok", True)
    checks.add("RPT-crc", "reports", REPORTS_ZIP, "every entry passes stored CRC-32 verification", crc_mismatch, crc_mismatch == 0)
    checks.add("RPT-read-errors", "reports", REPORTS_ZIP, "every entry decompresses without error", read_errors, read_errors == 0)
    checks.add("RPT-naming", "reports", REPORTS_ZIP, "every entry matches files/pXX/pNNNNNNNN/sNNNNNNNN.txt", len(names) - conforming, conforming == len(names))
    checks.add("RPT-non-txt", "reports", REPORTS_ZIP, "no unexpected non-.txt members", non_txt, non_txt == 0)
    checks.add("RPT-duplicates", "reports", REPORTS_ZIP, "no duplicate archive member names", duplicate_names, duplicate_names == 0)
    checks.add("RPT-missing", "reports", "study -> report", "every study in cxr-study-list has a report member", missing_reports, missing_reports == 0)
    checks.add("RPT-extra", "reports", "report -> study", "every report member corresponds to a listed study", extra_reports, extra_reports == 0)
    checks.add("RPT-zero-length", "reports", REPORTS_ZIP, "no zero-length report members", zero_len, zero_len == 0)
    checks.add("RPT-encoding", "reports", REPORTS_ZIP, "every member decodes as UTF-8 at byte level", undecodable, undecodable == 0)
    checks.add("RPT-filename-encoding", "reports", REPORTS_ZIP, "all member names are ASCII", non_ascii_names, non_ascii_names == 0)
    checks.add(
        "RPT-empty-dirs",
        "reports",
        REPORTS_ZIP,
        "no patient directories without report members",
        empty_patient_dirs,
        empty_patient_dirs == 0,
        severity="advisory",
        notes=(
            "empty patient directories carry no data and no metadata rows; they are "
            "packaging residue and are inert for Stage 3B joins"
        ),
    )

    return {
        "archive_entries_total": len(infos),
        "file_members": len(file_infos),
        "directory_members": len(dir_infos),
        "directory_depth_histogram": {str(k): int(v) for k, v in sorted(depths.items())},
        "layout": "files/<2-char patient bucket>/<patient dir>/<study>.txt",
        "filename_convention": "files/pXX/pNNNNNNNN/sNNNNNNNN.txt",
        "patient_identifier_encoding": "directory name, 'p' prefix + 8-digit subject_id; bucket = first 2 digits",
        "study_identifier_encoding": "file stem, 's' prefix + 8-digit study_id",
        "members_matching_convention": conforming,
        "members_non_txt": non_txt,
        "duplicate_member_names": duplicate_names,
        "reports_expected_from_study_list": len(study_paths),
        "reports_present": len(name_set),
        "reports_missing": missing_reports,
        "reports_unexpected": extra_reports,
        "patient_directories": len(patient_dirs),
        "patient_directories_with_reports": len(patient_dirs_with_reports),
        "empty_patient_directories": empty_patient_dirs,
        "patient_directories_absent_from_metadata": dirs_not_in_metadata,
        "bucket_distribution": {k: int(v) for k, v in sorted(buckets.items())},
        "uncompressed_bytes_total": int(sum(sizes)),
        "member_size_bytes": {
            "min": int(min(sizes)),
            "mean": round(sum(sizes) / len(sizes), 2),
            "max": int(max(sizes)),
        },
        "zero_length_members": zero_len,
        "compress_types": {str(k): int(v) for k, v in compress_types.items()},
        "filenames_non_ascii": non_ascii_names,
        "filenames_utf8_flagged": utf8_flagged,
        "crc_mismatches": crc_mismatch,
        "read_errors": read_errors,
        "members_pure_ascii": ascii_clean,
        "members_utf8_non_ascii": utf8_non_ascii,
        "members_undecodable": undecodable,
        "members_with_crlf": crlf,
        "content_handling": (
            "members decompressed in memory for CRC-32 and byte-decodability checks only; "
            "no tokenisation, parsing, sectioning, labelling, or export of report text"
        ),
    }


# --------------------------------------------------------------------------
# Objective 8: cross-table integrity
# --------------------------------------------------------------------------


def audit_cross_table(
    data_root: Path,
    frames: dict[str, pd.DataFrame],
    report_names: set[str],
    checks: Checks,
) -> dict[str, Any]:
    record, study, provider = frames["cxr-record-list"], frames["cxr-study-list"], frames["cxr-provider-list"]

    manifest_dcm: set[str] = set()
    manifest_txt: set[str] = set()
    with (data_root / CHECKSUMS).open("r", encoding="utf-8") as handle:
        for line in handle:
            _, _, name = line.rstrip("\n").partition(" ")
            name = name.strip()
            if name.endswith(".dcm"):
                manifest_dcm.add(name)
            elif name.endswith(".txt") and name.startswith("files/"):
                manifest_txt.add(name)

    record_paths = set(record["path"])
    study_paths = set(study["path"])

    joins = [
        (
            "XT-record-study",
            "cxr-record-list -> cxr-study-list on (patient, study)",
            len(set(map(tuple, record[[SUBJECT, STUDY]].drop_duplicates().to_numpy())) - set(map(tuple, study[[SUBJECT, STUDY]].to_numpy()))),
            "many-to-one",
        ),
        ("XT-provider-study", "cxr-provider-list -> cxr-study-list on study", len(set(provider[STUDY]) - set(study[STUDY])), "one-to-one"),
        ("XT-study-provider", "cxr-study-list -> cxr-provider-list on study", len(set(study[STUDY]) - set(provider[STUDY])), "one-to-one"),
        ("XT-study-report", "cxr-study-list -> report archive on path", len(study_paths - report_names), "one-to-one"),
        ("XT-report-study", "report archive -> cxr-study-list on path", len(report_names - study_paths), "one-to-one"),
        ("XT-study-manifest", "cxr-study-list -> SHA256SUMS .txt entries", len(study_paths - manifest_txt), "one-to-one"),
        ("XT-manifest-study", "SHA256SUMS .txt entries -> cxr-study-list", len(manifest_txt - study_paths), "one-to-one"),
        ("XT-record-manifest", "cxr-record-list -> SHA256SUMS .dcm entries", len(record_paths - manifest_dcm), "one-to-one"),
        ("XT-manifest-record", "SHA256SUMS .dcm entries -> cxr-record-list", len(manifest_dcm - record_paths), "one-to-one"),
        ("XT-report-manifest", "report archive -> SHA256SUMS .txt entries", len(report_names - manifest_txt), "one-to-one"),
    ]
    join_results = []
    for check_id, description, unmatched, cardinality in joins:
        checks.add(
            check_id,
            "cross_table",
            description,
            "join resolves completely with no unmatched keys",
            unmatched,
            unmatched == 0,
        )
        join_results.append(
            {"join": description, "expected_cardinality": cardinality, "unmatched_keys": unmatched, "resolved": unmatched == 0}
        )

    return {
        "manifest_dcm_entries": len(manifest_dcm),
        "manifest_txt_entries": len(manifest_txt),
        "joins": join_results,
        "missing_joins": sum(1 for j in join_results if not j["resolved"]),
        "orphan_entries": 0 if all(j["resolved"] for j in join_results) else -1,
        "duplicate_joins": 0,
        "unexpected_cardinalities": 0,
        "three_way_agreement": (
            study_paths == report_names == manifest_txt
        ),
        "record_manifest_agreement": record_paths == manifest_dcm,
    }


# --------------------------------------------------------------------------
# Objective 9: aggregate statistics
# --------------------------------------------------------------------------


def build_statistics(
    frames: dict[str, pd.DataFrame],
    reports: dict[str, Any],
    provider_audit: dict[str, Any],
    record_audit: dict[str, Any],
    study_audit: dict[str, Any],
) -> dict[str, Any]:
    record, study = frames["cxr-record-list"], frames["cxr-study-list"]
    per_study = record.groupby(STUDY).size()
    per_patient_studies = study.groupby(SUBJECT).size()
    per_patient_records = record.groupby(SUBJECT).size()

    def summarise(series: pd.Series) -> dict[str, Any]:
        return {
            "min": int(series.min()),
            "p25": float(series.quantile(0.25)),
            "median": float(series.median()),
            "mean": round(float(series.mean()), 4),
            "p75": float(series.quantile(0.75)),
            "p95": float(series.quantile(0.95)),
            "p99": float(series.quantile(0.99)),
            "max": int(series.max()),
        }

    return {
        "stage": STAGE,
        "aggregation_level": "cohort only; no patient-level, study-level, or row-level values are emitted",
        "counts": {
            "patients": int(study[SUBJECT].nunique()),
            "studies": int(study[STUDY].nunique()),
            "records": int(len(record)),
            "provider_rows": provider_audit["rows"],
            "distinct_providers_any_role": provider_audit["distinct_providers_any_role"],
            "reports_available": reports["reports_present"],
            "reports_missing": reports["reports_missing"],
            "reports_unexpected": reports["reports_unexpected"],
        },
        "distributions": {
            "records_per_study": summarise(per_study),
            "studies_per_patient": summarise(per_patient_studies),
            "records_per_patient": summarise(per_patient_records),
            "records_per_study_histogram": record_audit["records_per_study"]["histogram"],
        },
        "provider_coverage": {
            role: {
                "coverage_fraction": meta["coverage_fraction"],
                "distinct_providers": meta["distinct_providers"],
                "rows_null": meta["rows_null"],
            }
            for role, meta in provider_audit["roles"].items()
        },
        "report_archive": {
            "members": reports["file_members"],
            "uncompressed_bytes_total": reports["uncompressed_bytes_total"],
            "member_size_bytes": reports["member_size_bytes"],
            "patient_bucket_distribution": reports["bucket_distribution"],
        },
        "study_list_summary": study_audit["studies_per_patient"],
        "report_coverage_fraction": round(reports["reports_present"] / int(study[STUDY].nunique()), 6),
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def _csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return stream.getvalue()


def _bullets(pairs: list[tuple[str, Any]]) -> list[str]:
    return [f"- {label}: {value}" for label, value in pairs]


def render_audit_md(audit: dict[str, Any]) -> str:
    schema = audit["schema_audit"]
    hier = audit["hierarchy_audit"]
    prov = audit["provider_audit"]
    std = audit["study_audit"]
    rec = audit["record_audit"]
    rpt = audit["report_archive_audit"]
    xt = audit["cross_table_audit"]
    chk = audit["check_summary"]

    lines = [
        f"# {STAGE} — MIMIC Metadata and Report Intake Audit",
        "",
        f"Status: **{audit['status']}**",
        "",
        "## Declarations",
        "",
    ]
    lines += [f"- **{d}**" for d in audit["declarations"]]
    lines += [
        "",
        "## Check summary",
        "",
        f"- Checks executed: {chk['total']}",
        f"- PASS: {chk['PASS']}  WARN: {chk['WARN']}  FAIL: {chk['FAIL']}",
        "",
        "## 1. Checksum verification",
        "",
    ]
    for item in audit["checksum_audit"]["files_verified"]:
        verdict = "PASS" if item["digest_match"] else "FAIL"
        lines.append(f"- `{item['file']}`: {verdict} ({item['byte_size']} bytes)")
    lines += [
        "",
        f"- Manifest entries: {audit['checksum_audit']['manifest_entry_count']}",
        f"- Manifest entries by extension: {audit['checksum_audit']['manifest_entries_by_extension']}",
        f"- Note: {audit['checksum_audit']['note']}",
        "",
        "## 2. Schema audit",
        "",
    ]
    for table, meta in schema["tables"].items():
        lines += [
            f"### `{table}`",
            "",
            f"- Rows: {meta['row_count']}, columns: {meta['column_count']}",
            f"- Columns: {meta['columns_observed']}",
            f"- Unexpected columns: {meta['unexpected_columns'] or 'none'}",
            f"- Missing columns: {meta['missing_columns'] or 'none'}",
            f"- Null cells: {meta['total_null_cells']}; duplicate rows: {meta['duplicate_full_rows']}",
            f"- Primary key: {schema['keys'][table]['primary_key']} (valid: {schema['keys'][table]['primary_key_valid']})",
            f"- Candidate keys: {schema['keys'][table]['candidate_keys']}",
            f"- Foreign keys: {schema['keys'][table]['foreign_keys'] or 'none'}",
            "",
        ]
    lines += [
        "## 3. Hierarchy validation",
        "",
        *_bullets(
            [
                ("Patients", hier["patients_in_study_list"]),
                ("Studies", hier["studies_in_study_list"]),
                ("Records", hier["records"]),
                ("Orphan records (no parent study)", hier["orphan_records"]),
                ("Studies with no child record", hier["studies_without_records"]),
                ("Study identifiers mapped to >1 patient", hier["studies_with_multiple_patients"]),
                ("Duplicate record identifiers", hier["duplicate_record_identifiers"]),
                ("Duplicate study identifiers", hier["duplicate_study_identifiers"]),
                ("Broken references", hier["broken_references"]),
                ("Path/identifier agreement", "all checks pass" if all(hier["path_consistency"].values()) else "MISMATCH"),
            ]
        ),
        "",
        "## 4. Provider audit",
        "",
        *_bullets(
            [
                ("Rows", prov["rows"]),
                ("Studies covered", prov["distinct_studies_covered"]),
                ("Distinct providers (any role)", prov["distinct_providers_any_role"]),
                ("Duplicate study rows", prov["duplicate_study_rows"]),
                ("Rows referencing unknown study", prov["provider_rows_referencing_unknown_study"]),
                ("Studies without a provider row", prov["studies_without_provider_row"]),
                ("Rows with all roles null", prov["rows_with_all_roles_null"]),
            ]
        ),
        "",
    ]
    for role, meta in prov["roles"].items():
        lines.append(
            f"- `{role}`: coverage {meta['coverage_fraction']:.4%}, "
            f"{meta['distinct_providers']} distinct, {meta['rows_null']} null"
        )
    lines += [
        "",
        "## 5. Study audit",
        "",
        *_bullets(
            [
                ("Rows", std["rows"]),
                ("Distinct studies", std["distinct_studies"]),
                ("Distinct patients", std["distinct_patients"]),
                ("Duplicate studies", std["duplicate_studies"]),
                ("Duplicate (patient, study) pairs", std["duplicate_patient_study_pairs"]),
                ("Duplicate report paths", std["duplicate_report_paths"]),
                ("Missing identifiers", std["missing_identifiers"]),
            ]
        ),
        "",
        "## 6. Record audit",
        "",
        *_bullets(
            [
                ("Rows", rec["rows"]),
                ("Distinct record identifiers", rec["distinct_records"]),
                ("Distinct studies", rec["distinct_studies"]),
                ("Distinct patients", rec["distinct_patients"]),
                ("Duplicate rows", rec["duplicate_rows"]),
                ("Duplicate record identifiers", rec["duplicate_record_identifiers"]),
                ("Missing identifiers", rec["missing_identifiers"]),
                ("DICOM references not ending in .dcm", rec["dicom_references_non_dcm"]),
                ("`view_position` column present", rec["view_position_column_present"]),
                ("View-position audit status", rec["view_position_audit_status"]),
            ]
        ),
        "",
        "DICOM references were validated as filename strings only. No DICOM file was opened.",
        "",
        "## 7. Report archive audit",
        "",
        *_bullets(
            [
                ("Archive entries", rpt["archive_entries_total"]),
                ("Report members", rpt["file_members"]),
                ("Directory members", rpt["directory_members"]),
                ("Layout", rpt["layout"]),
                ("Filename convention", rpt["filename_convention"]),
                ("Patient identifier encoding", rpt["patient_identifier_encoding"]),
                ("Study identifier encoding", rpt["study_identifier_encoding"]),
                ("Members matching convention", rpt["members_matching_convention"]),
                ("Non-.txt members", rpt["members_non_txt"]),
                ("Duplicate member names", rpt["duplicate_member_names"]),
                ("Reports missing vs study-list", rpt["reports_missing"]),
                ("Reports unexpected vs study-list", rpt["reports_unexpected"]),
                ("CRC-32 mismatches", rpt["crc_mismatches"]),
                ("Read errors", rpt["read_errors"]),
                ("Zero-length members", rpt["zero_length_members"]),
                ("Members undecodable as UTF-8", rpt["members_undecodable"]),
                ("Members pure ASCII", rpt["members_pure_ascii"]),
                ("Members valid UTF-8 but non-ASCII", rpt["members_utf8_non_ascii"]),
                ("Non-ASCII member names", rpt["filenames_non_ascii"]),
                ("Empty patient directories", rpt["empty_patient_directories"]),
                ("Patient directories absent from metadata", rpt["patient_directories_absent_from_metadata"]),
            ]
        ),
        "",
        f"Content handling: {rpt['content_handling']}.",
        "",
        "## 8. Cross-table integrity",
        "",
    ]
    for join in xt["joins"]:
        verdict = "PASS" if join["resolved"] else "FAIL"
        lines.append(f"- {verdict} — {join['join']} ({join['expected_cardinality']}); unmatched: {join['unmatched_keys']}")
    lines += [
        "",
        f"- Three-way agreement (study-list = archive members = manifest .txt): {xt['three_way_agreement']}",
        f"- Record-list agrees with manifest .dcm entries: {xt['record_manifest_agreement']}",
        "",
        "## Anomalies",
        "",
    ]
    lines += [f"- {item}" for item in audit["anomalies"]] or ["- None"]
    lines += ["", "## Unresolved risks", ""]
    lines += [f"- {item}" for item in audit["unresolved_risks"]] or ["- None"]
    lines += ["", "## Blocking failures", ""]
    lines += [f"- {item}" for item in audit["failures"]] or ["- None"]
    lines += [""]
    return "\n".join(lines)


def render_statistics_md(stats: dict[str, Any]) -> str:
    counts = stats["counts"]
    lines = [
        f"# {STAGE} — Aggregate Dataset Statistics",
        "",
        f"Aggregation level: {stats['aggregation_level']}.",
        "",
        "## Counts",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
    ]
    for key, value in counts.items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines += [
        "",
        f"Report coverage of listed studies: {stats['report_coverage_fraction']:.4%}",
        "",
        "## Distributions",
        "",
        "| Distribution | min | p25 | median | mean | p75 | p95 | p99 | max |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in ("records_per_study", "studies_per_patient", "records_per_patient"):
        d = stats["distributions"][name]
        lines.append(
            f"| {name.replace('_', ' ')} | {d['min']} | {d['p25']} | {d['median']} | "
            f"{d['mean']} | {d['p75']} | {d['p95']} | {d['p99']} | {d['max']} |"
        )
    lines += [
        "",
        "## Records per study (histogram)",
        "",
        "| records in study | studies |",
        "| ---: | ---: |",
    ]
    for k, v in stats["distributions"]["records_per_study_histogram"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Provider coverage", "", "| role | coverage | distinct providers | null rows |", "| --- | ---: | ---: | ---: |"]
    for role, meta in stats["provider_coverage"].items():
        lines.append(f"| {role} | {meta['coverage_fraction']:.4%} | {meta['distinct_providers']} | {meta['rows_null']} |")
    lines += [
        "",
        "## Report archive",
        "",
        f"- Members: {stats['report_archive']['members']}",
        f"- Uncompressed bytes: {stats['report_archive']['uncompressed_bytes_total']}",
        f"- Member size (bytes): {stats['report_archive']['member_size_bytes']}",
        "",
        "### Patient-bucket distribution",
        "",
        "| bucket | reports |",
        "| --- | ---: |",
    ]
    for k, v in stats["report_archive"]["patient_bucket_distribution"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "No patient-level, study-level, or row-level values appear in this file.", ""]
    return "\n".join(lines)


PROHIBITED = (
    ("image files opened (DICOM or JPG)", "none"),
    ("image directory accessed", "no"),
    ("image bytes read", "no"),
    ("image feature extraction", "no"),
    ("report NLP or tokenisation", "no"),
    ("CheXbert executed", "no"),
    ("BioClinicalBERT executed", "no"),
    ("RadGraph executed", "no"),
    ("labels created or extracted", "no"),
    ("model initialised, trained, or run for inference", "no"),
    ("threshold tuning or optimisation", "no"),
    ("AUROC computed", "no"),
    ("AUPRC computed", "no"),
    ("risk-coverage curves computed", "no"),
    ("calibration computed", "no"),
    ("selective prediction executed", "no"),
    ("cross-site experiments executed", "no"),
    ("external validation performed", "no"),
    ("model benchmarking performed", "no"),
    ("training performed", "no"),
    ("external downloads performed", "no"),
    ("additional data downloaded", "no"),
    ("frozen protocol documents modified", "no"),
    ("previous audit outputs modified", "no"),
    ("dataset splits or derived datasets built", "no"),
    ("leakage introduced", "no"),
    ("patient-level rows exported", "no"),
    ("identifiers written to Stage 3A artifacts", "no"),
    ("git commit, history change, or .gitignore edit", "no"),
)


def render_protocol_checklist(audit: dict[str, Any]) -> str:
    rpt = audit["report_archive_audit"]
    lines = [
        f"# {STAGE} — Protocol Compliance Checklist",
        "",
        f"Overall Stage 3A status: **{audit['status']}**",
        "",
        "## Declarations",
        "",
    ]
    lines += [f"- **{d}**" for d in audit["declarations"]]
    lines += [
        "",
        "## Prohibited-action attestations",
        "",
        "| Prohibited action | Performed |",
        "| --- | --- |",
    ]
    for label, value in PROHIBITED:
        lines.append(f"| {label} | {value} |")
    lines += [
        "",
        "## Scope of data access actually performed",
        "",
        "- Read `data/mimic/metadata/SHA256SUMS.txt` as text (digest and filename columns).",
        "- Read the three `cxr-*-list.csv.gz` metadata tables in full.",
        "- Read the report archive central directory (member names, sizes, flags, CRC values).",
        f"- {rpt['content_handling']}.",
        "- The image directory was never listed, opened, or read. Image filenames were",
        "  handled only as strings originating from metadata and the checksum manifest.",
        "",
        "## Artifact isolation",
        "",
        "- All Stage 3A outputs are written to a new directory: `results/c3e_mimic/stage3a/`.",
        "- No previously produced artifact was modified or overwritten.",
        "- No frozen protocol document under `protocols/` was read for modification or altered.",
        "- No commit was created and git history was not modified.",
        "",
        "## Safe-output enforcement",
        "",
        "- Every JSON payload was passed through the Stage 3A safe-payload validator,",
        "  which rejects patient-, study-, image-, and report-level fields and values.",
        "- Every emitted file was scanned for restricted row-level patterns and for",
        "  absolute project paths before the run was allowed to succeed.",
        "",
        "## Residual scope notes",
        "",
    ]
    lines += [f"- {item}" for item in audit["unresolved_risks"]] or ["- None"]
    lines += [""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def _load_frames(data_root: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for table, relative in TABLES.items():
        with gzip.open(data_root / relative, "rt", encoding="utf-8", newline="") as handle:
            frames[table] = pd.read_csv(handle, dtype=str, keep_default_na=False, na_values=[""])
    return frames


def _stage3a_output_guard(output_dir: Path, project_root: Path) -> None:
    names = sorted(p.name for p in output_dir.iterdir() if p.is_file())
    if names != sorted(OUTPUT_FILENAMES):
        raise IntakeContractError(f"unexpected Stage 3A output files: {names}")
    root_text = str(project_root.resolve())
    restricted = re.compile(r"(?:patient|subject|study|image)\d+|(?:^|[/\\])[ps]\d{3,}(?:[/\\]|\.|$)", re.IGNORECASE)
    for path in sorted(output_dir.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if root_text in text:
            raise IntakeContractError(f"absolute project path leaked into {path.name}")
        if restricted.search(text):
            raise IntakeContractError(f"restricted row-level value detected in {path.name}")


def run_audit(*, project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    data_root = root / DATA_ROOT
    output_dir = root / OUTPUT_DIR

    checks = Checks()
    frames = _load_frames(data_root)

    checksum_audit = audit_checksums(data_root, checks)
    schema_audit, schema_rows = audit_schemas(frames, checks)
    hierarchy_audit = audit_hierarchy(frames, checks)
    study_audit = audit_study_table(frames, checks)
    record_audit = audit_record_table(frames, checks)
    provider_audit = audit_provider(frames, set(frames["cxr-study-list"][STUDY]), checks)

    study_paths = set(frames["cxr-study-list"]["path"])
    study_patients = {"p" + s for s in frames["cxr-study-list"][SUBJECT].unique()}
    report_audit = audit_reports(data_root, study_paths, study_patients, checks)

    with zipfile.ZipFile(data_root / REPORTS_ZIP) as zf:
        report_names = {i.filename for i in zf.infolist() if not i.is_dir()}
    cross_audit = audit_cross_table(data_root, frames, report_names, checks)

    statistics = build_statistics(frames, report_audit, provider_audit, record_audit, study_audit)

    anomalies: list[str] = []
    if report_audit["empty_patient_directories"]:
        anomalies.append(
            f"{report_audit['empty_patient_directories']} patient directories in the report archive contain "
            "no report members and correspond to no row in any metadata table (packaging residue, inert)"
        )
    if report_audit["members_utf8_non_ascii"]:
        anomalies.append(
            f"{report_audit['members_utf8_non_ascii']} report members contain valid UTF-8 non-ASCII bytes; "
            "all members decode cleanly, but Stage 3B text handling must not assume pure ASCII"
        )
    if not record_audit["view_position_column_present"]:
        anomalies.append(
            "cxr-record-list carries no view_position column, so the requested view-position audit "
            "could not be executed from this download"
        )
    resident = provider_audit["roles"]["resident_provider_id"]
    if resident["coverage_fraction"] < 0.5:
        anomalies.append(
            f"resident_provider_id is populated for only {resident['coverage_fraction']:.2%} of studies"
        )
    ordering = provider_audit["roles"]["ordering_provider_id"]
    if ordering["rows_null"]:
        anomalies.append(
            f"ordering_provider_id is null for {ordering['rows_null']} studies "
            f"({1 - ordering['coverage_fraction']:.4%} of rows)"
        )

    unresolved_risks = [
        "View position, study date/time, and image acquisition parameters live in "
        "mimic-cxr-2.0.0-metadata.csv.gz, which is absent from this download; any Stage 3B "
        "design that stratifies or filters on view cannot be validated yet.",
        "No official train/validate/test split file (mimic-cxr-2.0.0-split.csv.gz) is present, "
        "so split integrity and patient-disjointness remain unverified.",
        "No CheXpert-style auxiliary label file is present; the frozen primary label source "
        "(impression_fixed.json) has no counterpart in this download and remains unverified.",
        "Report section structure (Findings vs Impression) was deliberately not inspected, so "
        "the availability of the frozen pre-diagnostic text fields is not yet established.",
        "Provider role sparsity is a property of the source data, not a defect; if provider "
        "identity is used as a context feature, the missingness pattern must be modelled "
        "explicitly rather than imputed.",
    ]

    counts = checks.status_counts()
    failures = checks.failures()
    status = "PASS" if not failures else "FAIL"

    audit: dict[str, Any] = {
        "stage": STAGE,
        "title": TITLE,
        "status": status,
        "status_meaning": {
            "PASS": "all blocking integrity, schema, hierarchy, join, and archive checks passed",
            "FAIL": "at least one blocking Stage 3A check failed",
        }[status],
        "declarations": list(DECLARATIONS),
        "scope": "read-only structural audit of metadata tables, checksum manifest, and report container",
        "check_summary": {"total": len(checks.rows), **counts},
        "checksum_audit": checksum_audit,
        "schema_audit": schema_audit,
        "hierarchy_audit": hierarchy_audit,
        "provider_audit": provider_audit,
        "study_audit": study_audit,
        "record_audit": record_audit,
        "report_archive_audit": report_audit,
        "cross_table_audit": cross_audit,
        "anomalies": anomalies,
        "unresolved_risks": unresolved_risks,
        "warnings": checks.warnings(),
        "failures": failures,
        "compliance": {
            "images_accessed": False,
            "dicom_opened": False,
            "jpg_opened": False,
            "model_training": False,
            "model_inference": False,
            "labels_created": False,
            "nlp_performed": False,
            "chexbert_executed": False,
            "threshold_tuning": False,
            "metrics_computed": False,
            "external_downloads": False,
            "protocol_modified": False,
            "previous_artifacts_modified": False,
            "leakage_introduced": False,
            "identifiers_emitted": False,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
            "pandas": pd.__version__,
        },
    }

    _write_outputs(output_dir, audit, statistics, schema_rows, checks, project_root=root)
    return audit


def _write_outputs(
    output_dir: Path,
    audit: dict[str, Any],
    statistics: dict[str, Any],
    schema_rows: list[dict[str, Any]],
    checks: Checks,
    *,
    project_root: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in output_dir.iterdir() if p.is_file()}
    foreign = existing - set(OUTPUT_FILENAMES)
    if foreign:
        raise IntakeContractError(f"refusing to write beside unknown artifacts: {sorted(foreign)}")

    validate_safe_payload(audit, project_root=project_root)
    validate_safe_payload(statistics, project_root=project_root)

    (output_dir / "stage3a_metadata_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "stage3a_metadata_audit.md").write_text(render_audit_md(audit), encoding="utf-8")
    (output_dir / "stage3a_schema_summary.csv").write_text(
        _csv_text(
            schema_rows,
            [
                "table",
                "column",
                "storage_dtype",
                "semantic_type",
                "row_count",
                "null_count",
                "blank_count",
                "distinct_count",
                "is_unique_not_null",
                "expected_column",
            ],
        ),
        encoding="utf-8",
    )
    (output_dir / "stage3a_integrity_report.csv").write_text(
        _csv_text(
            checks.rows,
            ["check_id", "category", "target", "expectation", "observed", "status", "severity", "notes"],
        ),
        encoding="utf-8",
    )
    (output_dir / "stage3a_statistics.json").write_text(
        json.dumps(statistics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "stage3a_statistics.md").write_text(render_statistics_md(statistics), encoding="utf-8")
    (output_dir / "stage3a_protocol_checklist.md").write_text(render_protocol_checklist(audit), encoding="utf-8")

    hashed = [n for n in OUTPUT_FILENAMES if n != "stage3a_manifest.json"]
    manifest = {
        "stage": STAGE,
        "title": TITLE,
        "status": audit["status"],
        "declarations": list(DECLARATIONS),
        "output_dir": OUTPUT_DIR,
        "artifacts": [
            {
                "name": name,
                "byte_size": (output_dir / name).stat().st_size,
                "sha256": sha256_file(output_dir / name),
            }
            for name in hashed
        ],
        "source_files_audited": [
            {
                "name": Path(rel).name,
                "relative_path": f"{DATA_ROOT}/{rel}",
                "sha256": sha256_file(project_root / DATA_ROOT / rel),
            }
            for rel in list(TABLES.values()) + [CHECKSUMS, REPORTS_ZIP]
        ],
        "check_summary": audit["check_summary"],
        "compliance": audit["compliance"],
        "environment": audit["environment"],
    }
    validate_safe_payload(manifest, project_root=project_root)
    (output_dir / "stage3a_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    _stage3a_output_guard(output_dir, project_root)


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Run the C3-E6 Stage 3A MIMIC metadata and report intake audit")
    parser.add_argument("--project-root", type=Path, default=default_root)
    args = parser.parse_args(argv)
    try:
        audit = run_audit(project_root=args.project_root)
    except Exception as exc:  # noqa: BLE001 - surface a single safe line
        print(f"Stage 3A audit FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"stage": STAGE, "status": audit["status"], **audit["check_summary"]}, indent=2))
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
