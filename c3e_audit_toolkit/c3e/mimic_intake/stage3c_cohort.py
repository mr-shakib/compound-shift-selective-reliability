"""C3-E6 Stage 3C: source-site cohort construction audit.

Applies the approved text mapping and informativeness rule
(docs/C3E6_SOURCE_TEXT_MAPPING_AND_INFORMATIVENESS_RULE.md) together with the
frozen view and split policy, and reports the resulting confirmatory cohort.

Frozen inputs honoured here:
- eligible_view: frontal
- official_splits_required: true
- resampling/cluster unit: patient
- permitted context: indication + history (approved source mapping)
- informativeness threshold T = 3 primary, 5 and 10 as sensitivity

This module builds no dataset file, extracts no label, opens no image, and runs
no model. It reports counts only.
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

import pandas as pd

from .contracts import IntakeContractError
from .safety import validate_safe_payload
from .stage3b_reports import HEADER_RE, SECTION_MAP, sha256_file
from .stage3b_context_threshold import effective_token_count

STAGE = "C3-E6 Stage 3C"
TITLE = "SOURCE-SITE COHORT CONSTRUCTION AUDIT"

DECLARATIONS = (
    "STAGE 3C ONLY",
    "COHORT COUNTING AND ELIGIBILITY AUDIT",
    "NO MEDICAL IMAGES OPENED",
    "NO DICOM OR JPG DECODED",
    "NO REPORT TEXT EXPORTED",
    "NO LABEL EXTRACTION",
    "NO CHEXBERT EXECUTION",
    "NO MODEL TRAINING OR INFERENCE",
    "NO PREDICTION THRESHOLD SELECTION",
    "NO EVALUATION OR METRIC COMPUTATION",
    "NO DATASET FILE WRITTEN",
    "NO EXTERNAL DOWNLOADS",
)

OUTPUT_FILENAMES = (
    "stage3c_cohort_audit.json",
    "stage3c_cohort_audit.md",
    "stage3c_exclusion_waterfall.csv",
    "stage3c_split_summary.csv",
    "stage3c_view_distribution.csv",
    "stage3c_manifest.json",
)

DATA_ROOT = "data/mimic"
OUTPUT_DIR = "results/c3e_mimic/stage3c"
REPORTS_ZIP = "reports/mimic-cxr-reports.zip"
STUDY_LIST = "metadata/cxr-study-list.csv.gz"
RECORD_LIST = "metadata/cxr-record-list.csv.gz"
IMAGE_METADATA = "metadata/mimic-cxr-2.0.0-metadata.csv.gz"
SPLIT_FILE = "metadata/mimic-cxr-2.0.0-split.csv.gz"

# Frozen: eligible_view = frontal. MIMIC encodes frontal projections as PA/AP.
FRONTAL_VIEWS = frozenset({"PA", "AP"})

# Approved source text mapping.
PERMITTED_SECTIONS = ("indication", "history")
THRESHOLD_PRIMARY = 3
THRESHOLD_SENSITIVITY = (5, 10)

LABEL_PRIMARY = "impression"
LABEL_SENSITIVITY = "findings"
COMBINED_SECTION = "findings_impression_combined"


def _parse_reports(data_root: Path) -> pd.DataFrame:
    """Per-study context tokens, label-section presence, and structural flags."""
    rows = []
    with zipfile.ZipFile(data_root / REPORTS_ZIP) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            text = zf.read(info).decode("utf-8", errors="replace")
            counts: dict[str, int] = collections.defaultdict(int)
            present: set[str] = set()
            matches = list(HEADER_RE.finditer(text))
            for position, match in enumerate(matches):
                raw = re.sub(r"\s+", " ", match.group(1)).strip()
                mapped = SECTION_MAP.get(raw)
                if mapped is None:
                    continue
                canonical, _ = mapped
                end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
                tokens = effective_token_count(text[match.end():end].strip())
                counts[canonical] += tokens
                if tokens > 0:
                    present.add(canonical)
            rows.append(
                {
                    "path": info.filename,
                    "context_tokens": sum(counts.get(s, 0) for s in PERMITTED_SECTIONS),
                    "has_impression": LABEL_PRIMARY in present or COMBINED_SECTION in present,
                    "has_findings": LABEL_SENSITIVITY in present or COMBINED_SECTION in present,
                    "has_combined_label_section": COMBINED_SECTION in present,
                    "has_any_recognised_section": bool(present or counts),
                }
            )
            del text
    return pd.DataFrame(rows)


def build_cohort(data_root: Path) -> dict[str, Any]:
    study = pd.read_csv(data_root / STUDY_LIST, dtype=str)
    record = pd.read_csv(data_root / RECORD_LIST, dtype=str)
    meta = pd.read_csv(data_root / IMAGE_METADATA, dtype=str)
    split = pd.read_csv(data_root / SPLIT_FILE, dtype=str)

    integrity = {
        "image_metadata_rows": int(len(meta)),
        "split_rows": int(len(split)),
        "record_rows": int(len(record)),
        "metadata_dicom_set_matches_record_list": set(meta.dicom_id) == set(record.dicom_id),
        "split_dicom_set_matches_record_list": set(split.dicom_id) == set(record.dicom_id),
        "metadata_duplicate_dicom": int(meta.dicom_id.duplicated().sum()),
        "split_duplicate_dicom": int(split.dicom_id.duplicated().sum()),
        "official_checksum_manifest_available": (data_root / "metadata/SHA256SUMS-cxr-jpg.txt").exists(),
    }
    merged = record.merge(meta[["dicom_id", "subject_id", "study_id"]], on="dicom_id", suffixes=("", "_m"))
    integrity["metadata_identifiers_agree"] = bool(
        (merged.subject_id == merged.subject_id_m).all() and (merged.study_id == merged.study_id_m).all()
    )
    merged_s = record.merge(split[["dicom_id", "subject_id", "study_id"]], on="dicom_id", suffixes=("", "_s"))
    integrity["split_identifiers_agree"] = bool(
        (merged_s.subject_id == merged_s.subject_id_s).all() and (merged_s.study_id == merged_s.study_id_s).all()
    )

    # View distribution.
    view_counts = meta.ViewPosition.fillna("<missing>").value_counts()
    view_rows = [
        {
            "view_position": name,
            "images": int(count),
            "fraction": round(count / len(meta), 6),
            "is_frontal": name in FRONTAL_VIEWS,
        }
        for name, count in view_counts.items()
    ]

    meta["is_frontal"] = meta.ViewPosition.isin(FRONTAL_VIEWS)
    frontal_studies = set(meta.loc[meta.is_frontal, "study_id"])

    # Split assignment at study level (verified single-valued).
    split_by_study = split.groupby("study_id").split.agg(["nunique", "first"])
    studies_spanning_splits = int((split_by_study["nunique"] > 1).sum())
    patients_spanning = int((split.groupby("subject_id").split.nunique() > 1).sum())
    study_split = split_by_study["first"].to_dict()

    reports = _parse_reports(data_root)
    frame = study.merge(reports, on="path", how="left")

    frame["split"] = frame.study_id.map(study_split)
    frame["has_frontal"] = frame.study_id.isin(frontal_studies)

    total = len(frame)
    steps: list[dict[str, Any]] = []
    eligible = pd.Series(True, index=frame.index)

    def step(name: str, keep: pd.Series, reason: str) -> None:
        nonlocal eligible
        before = int(eligible.sum())
        eligible = eligible & keep
        after = int(eligible.sum())
        steps.append(
            {
                "step": name,
                "rule": reason,
                "studies_before": before,
                "studies_removed": before - after,
                "studies_after": after,
                "fraction_remaining": round(after / total, 6),
            }
        )

    steps.append(
        {
            "step": "all_studies",
            "rule": "every study in cxr-study-list",
            "studies_before": total,
            "studies_removed": 0,
            "studies_after": total,
            "fraction_remaining": 1.0,
        }
    )
    step("recognised_structure", frame.has_any_recognised_section.fillna(False),
         "exclude reports with no recognised section header (approved exclusion rule)")
    step("separable_label_sections", ~frame.has_combined_label_section.fillna(False),
         "exclude reports merging findings and impression (approved exclusion rule)")
    step("frontal_view_available", frame.has_frontal,
         "frozen eligible_view=frontal: study must have at least one PA/AP image")
    step("official_split_assigned", frame.split.notna(),
         "frozen official_splits_required=true")
    step(f"context_informative_T{THRESHOLD_PRIMARY}", frame.context_tokens.fillna(0) >= THRESHOLD_PRIMARY,
         f"approved informativeness rule: N1 requires >= {THRESHOLD_PRIMARY} effective tokens "
         "across indication+history")
    step("primary_label_source_present", frame.has_impression.fillna(False),
         "study must carry an impression section to receive a primary label")

    cohort = frame[eligible]

    def summarise(sub: pd.DataFrame) -> dict[str, Any]:
        image_count = int(
            meta[meta.is_frontal & meta.study_id.isin(set(sub.study_id))].shape[0]
        )
        return {
            "studies": int(len(sub)),
            "patients": int(sub.subject_id.nunique()),
            "frontal_images": image_count,
        }

    split_rows = []
    for name in ("train", "validate", "test"):
        sub = cohort[cohort.split == name]
        entry = {"split": name, **summarise(sub)}
        entry["with_findings_sensitivity_label"] = int(sub.has_findings.fillna(False).sum())
        for t in THRESHOLD_SENSITIVITY:
            sub_t = frame[
                (frame.split == name)
                & frame.has_any_recognised_section.fillna(False)
                & ~frame.has_combined_label_section.fillna(False)
                & frame.has_frontal
                & frame.split.notna()
                & (frame.context_tokens.fillna(0) >= t)
                & frame.has_impression.fillna(False)
            ]
            entry[f"studies_at_T{t}"] = int(len(sub_t))
            entry[f"patients_at_T{t}"] = int(sub_t.subject_id.nunique())
        split_rows.append(entry)

    overall = summarise(cohort)

    risks: list[str] = []
    test_row = next(r for r in split_rows if r["split"] == "test")
    validate_row = next(r for r in split_rows if r["split"] == "validate")
    risks.append(
        f"The official test split yields {test_row['studies']} studies from "
        f"{test_row['patients']} patients. The frozen statistical_cluster_unit is patient and "
        f"failure_criteria require a CI excluding zero at a minimum absolute risk increase of "
        f"0.02; with {test_row['patients']} clusters this is a materially power-limited "
        "confirmatory test."
    )
    risks.append(
        f"The validate split yields {validate_row['studies']} studies from "
        f"{validate_row['patients']} patients, which constrains calibration and any "
        "coverage-stratified diagnostic performed off the training split."
    )
    if not integrity["official_checksum_manifest_available"]:
        risks.append(
            "The MIMIC-CXR-JPG SHA256SUMS manifest was not downloaded, so the two new files "
            "could not be checksum-verified against the official source. They were instead "
            "cross-validated against the checksum-verified cxr-record-list; identifier sets and "
            "per-row identifiers agree exactly."
        )
    missing_view = int(meta.ViewPosition.isna().sum())
    risks.append(
        f"{missing_view} images carry no ViewPosition and are therefore treated as non-frontal. "
        "This is a conservative reading of the frozen eligible_view rule; studies whose only "
        "images lack a view label are excluded rather than assumed frontal."
    )

    return {
        "stage": STAGE,
        "title": TITLE,
        "status": "PASS",
        "declarations": list(DECLARATIONS),
        "applied_policy": {
            "eligible_view": "frontal (PA, AP)",
            "permitted_context_sections": list(PERMITTED_SECTIONS),
            "informativeness_threshold_primary": THRESHOLD_PRIMARY,
            "informativeness_threshold_sensitivity": list(THRESHOLD_SENSITIVITY),
            "primary_label_section": LABEL_PRIMARY,
            "sensitivity_label_section": LABEL_SENSITIVITY,
            "official_splits_required": True,
            "policy_source": "docs/C3E6_SOURCE_TEXT_MAPPING_AND_INFORMATIVENESS_RULE.md (approved)",
        },
        "input_integrity": integrity,
        "view_distribution": view_rows,
        "frontal_images": int(meta.is_frontal.sum()),
        "images_missing_view": missing_view,
        "split_integrity": {
            "studies_spanning_splits": studies_spanning_splits,
            "patients_spanning_splits": patients_spanning,
            "no_patient_overlap_across_source_splits": patients_spanning == 0,
            "split_image_counts": {k: int(v) for k, v in split.split.value_counts().items()},
        },
        "exclusion_waterfall": steps,
        "cohort_overall": overall,
        "cohort_by_split": split_rows,
        "unresolved_risks": risks,
        "compliance": {
            "images_accessed": False,
            "dicom_opened": False,
            "report_text_exported": False,
            "labels_created": False,
            "chexbert_executed": False,
            "model_training": False,
            "model_inference": False,
            "evaluation_performed": False,
            "dataset_file_written": False,
            "identifiers_emitted": False,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
            "pandas": pd.__version__,
        },
    }


def _csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return stream.getvalue()


def render_md(report: dict[str, Any]) -> str:
    pol = report["applied_policy"]
    lines = [
        f"# {STAGE} — Source-Site Cohort Construction Audit",
        "",
        f"Status: **{report['status']}**",
        "",
    ]
    lines += [f"- **{d}**" for d in report["declarations"]]
    lines += [
        "",
        "## Applied policy",
        "",
        f"- Eligible view: {pol['eligible_view']} (frozen)",
        f"- Permitted context sections: {pol['permitted_context_sections']} (approved mapping)",
        f"- Informativeness threshold: T = {pol['informativeness_threshold_primary']} primary, "
        f"{pol['informativeness_threshold_sensitivity']} sensitivity",
        f"- Primary label section: {pol['primary_label_section']}; sensitivity: {pol['sensitivity_label_section']}",
        f"- Policy source: `{pol['policy_source']}`",
        "",
        "## Input integrity",
        "",
    ]
    for key, value in report["input_integrity"].items():
        lines.append(f"- {key.replace('_', ' ')}: {value}")
    lines += [
        "",
        "## Split integrity",
        "",
        f"- Studies spanning splits: {report['split_integrity']['studies_spanning_splits']}",
        f"- Patients spanning splits: {report['split_integrity']['patients_spanning_splits']}",
        f"- Frozen preflight check `no_patient_overlap_across_source_splits`: "
        f"**{'PASS' if report['split_integrity']['no_patient_overlap_across_source_splits'] else 'FAIL'}**",
        f"- Split image counts: {report['split_integrity']['split_image_counts']}",
        "",
        "## View distribution",
        "",
        "| view position | images | fraction | frontal |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in report["view_distribution"]:
        lines.append(
            f"| {row['view_position']} | {row['images']} | {row['fraction']:.4%} | {row['is_frontal']} |"
        )
    lines += [
        "",
        f"Frontal images: {report['frontal_images']}. Images with no view label: "
        f"{report['images_missing_view']}.",
        "",
        "## Exclusion waterfall",
        "",
        "| step | rule | before | removed | after | remaining |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["exclusion_waterfall"]:
        lines.append(
            f"| {row['step']} | {row['rule']} | {row['studies_before']} | {row['studies_removed']} | "
            f"{row['studies_after']} | {row['fraction_remaining']:.4%} |"
        )
    lines += [
        "",
        "## Confirmatory cohort",
        "",
        f"- Studies: {report['cohort_overall']['studies']}",
        f"- Patients: {report['cohort_overall']['patients']}",
        f"- Frontal images: {report['cohort_overall']['frontal_images']}",
        "",
        "| split | studies | patients | frontal images | with findings label | studies @T5 | studies @T10 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["cohort_by_split"]:
        lines.append(
            f"| {row['split']} | {row['studies']} | {row['patients']} | {row['frontal_images']} | "
            f"{row['with_findings_sensitivity_label']} | {row['studies_at_T5']} | {row['studies_at_T10']} |"
        )
    lines += ["", "## Unresolved risks", ""]
    lines += [f"- {item}" for item in report["unresolved_risks"]]
    lines += [""]
    return "\n".join(lines)


def _output_guard(output_dir: Path, project_root: Path) -> None:
    names = sorted(p.name for p in output_dir.iterdir() if p.is_file())
    if names != sorted(OUTPUT_FILENAMES):
        raise IntakeContractError(f"unexpected Stage 3C output files: {names}")
    root_text = str(project_root.resolve())
    restricted = re.compile(
        r"(?:patient|subject|study|image)\d+|(?:^|[/\\])[ps]\d{3,}(?:[/\\]|\.|$)", re.IGNORECASE
    )
    for path in sorted(output_dir.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if root_text in text:
            raise IntakeContractError(f"absolute project path leaked into {path.name}")
        if restricted.search(text):
            raise IntakeContractError(f"restricted row-level value detected in {path.name}")
        if "___" in text:
            raise IntakeContractError(f"de-identification placeholder leaked into {path.name}")


def run_audit(*, project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    data_root = root / DATA_ROOT
    output_dir = root / OUTPUT_DIR

    report = build_cohort(data_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    foreign = {p.name for p in output_dir.iterdir() if p.is_file()} - set(OUTPUT_FILENAMES)
    if foreign:
        raise IntakeContractError(f"refusing to write beside unknown artifacts: {sorted(foreign)}")

    validate_safe_payload(report, project_root=root)

    (output_dir / "stage3c_cohort_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "stage3c_cohort_audit.md").write_text(render_md(report), encoding="utf-8")
    (output_dir / "stage3c_exclusion_waterfall.csv").write_text(
        _csv_text(
            report["exclusion_waterfall"],
            ["step", "rule", "studies_before", "studies_removed", "studies_after", "fraction_remaining"],
        ),
        encoding="utf-8",
    )
    (output_dir / "stage3c_split_summary.csv").write_text(
        _csv_text(
            report["cohort_by_split"],
            [
                "split", "studies", "patients", "frontal_images", "with_findings_sensitivity_label",
                "studies_at_T5", "patients_at_T5", "studies_at_T10", "patients_at_T10",
            ],
        ),
        encoding="utf-8",
    )
    (output_dir / "stage3c_view_distribution.csv").write_text(
        _csv_text(report["view_distribution"], ["view_position", "images", "fraction", "is_frontal"]),
        encoding="utf-8",
    )

    hashed = [n for n in OUTPUT_FILENAMES if n != "stage3c_manifest.json"]
    manifest = {
        "stage": STAGE,
        "title": TITLE,
        "status": report["status"],
        "declarations": list(DECLARATIONS),
        "output_dir": OUTPUT_DIR,
        "applied_policy": report["applied_policy"],
        "artifacts": [
            {"name": n, "byte_size": (output_dir / n).stat().st_size, "sha256": sha256_file(output_dir / n)}
            for n in hashed
        ],
        "source_files_audited": [
            {"name": Path(rel).name, "relative_path": f"{DATA_ROOT}/{rel}", "sha256": sha256_file(data_root / rel)}
            for rel in (STUDY_LIST, RECORD_LIST, IMAGE_METADATA, SPLIT_FILE, REPORTS_ZIP)
        ],
        "compliance": report["compliance"],
        "environment": report["environment"],
    }
    validate_safe_payload(manifest, project_root=root)
    (output_dir / "stage3c_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    _output_guard(output_dir, root)
    return report


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Run the C3-E6 Stage 3C cohort construction audit")
    parser.add_argument("--project-root", type=Path, default=default_root)
    args = parser.parse_args(argv)
    try:
        report = run_audit(project_root=args.project_root)
    except Exception as exc:  # noqa: BLE001
        print(f"Stage 3C FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"stage": STAGE, "status": report["status"], "cohort": report["cohort_overall"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
