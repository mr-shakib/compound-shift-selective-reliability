"""C3-E6 Stage 3E: prespecified patient-disjoint evaluation partition.

The official MIMIC test split carries only 282 patients in the Stage 3C cohort,
which Stage 3D showed is materially power-limited for H1. This module carves a
prespecified, patient-disjoint evaluation partition out of the MIMIC *train*
split, leaving the official validate and test splits untouched as secondary
confirmation.

Partitioning is deterministic under the frozen bootstrap seed and depends only
on patient identifiers - never on any label, outcome, image, or model output.
It is therefore a design-stage construction, not a data-dependent selection.

Also reports the image-download budget per tier so the cohort can be fetched
without pulling the full MIMIC-CXR-JPG release.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys
from typing import Any

import numpy as np
import pandas as pd

from .contracts import IntakeContractError
from .safety import validate_safe_payload
from .stage3b_reports import sha256_file
from .stage3c_cohort import (
    FRONTAL_VIEWS,
    IMAGE_METADATA,
    RECORD_LIST,
    SPLIT_FILE,
    STUDY_LIST,
    THRESHOLD_PRIMARY,
    _parse_reports,
)

STAGE = "C3-E6 Stage 3E"
TITLE = "PRESPECIFIED PATIENT-DISJOINT EVALUATION PARTITION"

DECLARATIONS = (
    "STAGE 3E ONLY",
    "DESIGN-STAGE PARTITION CONSTRUCTION",
    "PARTITION DEPENDS ONLY ON PATIENT IDENTIFIERS AND A FROZEN SEED",
    "NO LABEL, OUTCOME, OR MODEL OUTPUT USED",
    "NO MEDICAL IMAGES OPENED",
    "NO CHEXBERT EXECUTION",
    "NO MODEL TRAINING OR INFERENCE",
    "NO IDENTIFIERS IN SAFE OUTPUTS",
)

OUTPUT_FILENAMES = (
    "stage3e_partition_audit.json",
    "stage3e_partition_audit.md",
    "stage3e_partition_summary.csv",
    "stage3e_image_budget.csv",
    "stage3e_manifest.json",
)

DATA_ROOT = "data/mimic"
OUTPUT_DIR = "results/c3e_mimic/stage3e"
# Path manifests contain patient and study identifiers, so they are written into
# the gitignored restricted-data tree, never into results/.
MANIFEST_DIR = "data/mimic/download_manifests"

PARTITION_SEED = 20260718

# Prespecified tier sizes, in patients, carved from the Stage 3C train cohort.
EVAL_PATIENTS = 5000
CALIBRATION_PATIENTS = 3000
# Training-budget options reported so the image download can be sized.
TRAIN_BUDGET_OPTIONS = (5000, 10000, 20000, 40000, None)

# Estimated from the published MIMIC-CXR-JPG release size divided by image count.
# Flagged as an estimate: verify against a small sample before committing.
EST_MB_PER_IMAGE = 1.51


def _build_cohort_frame(data_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (Stage 3C cohort frame, frontal image frame)."""
    study = pd.read_csv(data_root / STUDY_LIST, dtype=str)
    record = pd.read_csv(data_root / RECORD_LIST, dtype=str)
    meta = pd.read_csv(data_root / IMAGE_METADATA, dtype=str)
    split = pd.read_csv(data_root / SPLIT_FILE, dtype=str)

    frontal = meta[meta.ViewPosition.isin(FRONTAL_VIEWS)][["dicom_id", "study_id", "subject_id"]]
    frontal_studies = set(frontal.study_id)
    study_split = split.groupby("study_id").split.first().to_dict()

    reports = _parse_reports(data_root)
    frame = study.merge(reports, on="path", how="left")
    frame["split"] = frame.study_id.map(study_split)

    eligible = (
        frame.has_any_recognised_section.fillna(False)
        & ~frame.has_combined_label_section.fillna(False)
        & frame.study_id.isin(frontal_studies)
        & frame.split.notna()
        & (frame.context_tokens.fillna(0) >= THRESHOLD_PRIMARY)
        & frame.has_impression.fillna(False)
    )
    cohort = frame[eligible].copy()
    frontal = frontal[frontal.study_id.isin(set(cohort.study_id))]
    # Attach relative JPG paths for the download manifest.
    rec = record[record.dicom_id.isin(set(frontal.dicom_id))][["dicom_id", "path"]]
    frontal = frontal.merge(rec, on="dicom_id", how="left")
    frontal["jpg_path"] = frontal["path"].str.replace(r"\.dcm$", ".jpg", regex=True)
    return cohort, frontal


def assign_partitions(cohort: pd.DataFrame) -> pd.DataFrame:
    """Deterministic patient-level tier assignment within the train split."""
    train_patients = np.sort(cohort.loc[cohort.split == "train", "subject_id"].unique())
    rng = np.random.default_rng(PARTITION_SEED)
    order = rng.permutation(len(train_patients))
    shuffled = train_patients[order]

    eval_ids = set(shuffled[:EVAL_PATIENTS])
    calib_ids = set(shuffled[EVAL_PATIENTS:EVAL_PATIENTS + CALIBRATION_PATIENTS])

    def tier(row: Any) -> str:
        if row.split != "train":
            return f"official_{row.split}"
        if row.subject_id in eval_ids:
            return "prespecified_eval"
        if row.subject_id in calib_ids:
            return "threshold_calibration"
        return "model_train"

    cohort = cohort.copy()
    cohort["tier"] = [tier(r) for r in cohort.itertuples(index=False)]
    return cohort


def build_report(data_root: Path, write_manifests: bool, project_root: Path) -> dict[str, Any]:
    cohort, frontal = _build_cohort_frame(data_root)
    cohort = assign_partitions(cohort)

    study_tier = cohort.set_index("study_id")["tier"].to_dict()
    frontal = frontal.copy()
    frontal["tier"] = frontal.study_id.map(study_tier)

    tiers = [
        "model_train",
        "threshold_calibration",
        "prespecified_eval",
        "official_validate",
        "official_test",
    ]

    summary_rows = []
    for name in tiers:
        sub = cohort[cohort.tier == name]
        imgs = frontal[frontal.tier == name]
        summary_rows.append({
            "tier": name,
            "role": {
                "model_train": "model fitting",
                "threshold_calibration": "frozen threshold selection",
                "prespecified_eval": "primary confirmatory evaluation",
                "official_validate": "secondary confirmation (official split)",
                "official_test": "secondary confirmation (official split)",
            }[name],
            "patients": int(sub.subject_id.nunique()),
            "studies": int(len(sub)),
            "frontal_images": int(len(imgs)),
            "estimated_download_gb": round(len(imgs) * EST_MB_PER_IMAGE / 1024, 2),
        })

    # Disjointness verification.
    patient_sets = {name: set(cohort.loc[cohort.tier == name, "subject_id"]) for name in tiers}
    overlaps = []
    names = list(patient_sets)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = len(patient_sets[a] & patient_sets[b])
            if shared:
                overlaps.append({"tier_a": a, "tier_b": b, "shared_patients": shared})

    # Image-budget options for the training tier.
    train_patients = np.sort(cohort.loc[cohort.tier == "model_train", "subject_id"].unique())
    rng = np.random.default_rng(PARTITION_SEED + 1)
    train_order = train_patients[rng.permutation(len(train_patients))]
    fixed_images = sum(
        r["frontal_images"] for r in summary_rows if r["tier"] != "model_train"
    )
    budget_rows = []
    for budget in TRAIN_BUDGET_OPTIONS:
        chosen = set(train_order) if budget is None else set(train_order[:budget])
        sub = cohort[cohort.subject_id.isin(chosen) & (cohort.tier == "model_train")]
        imgs = int(frontal[frontal.study_id.isin(set(sub.study_id))].shape[0])
        total_imgs = imgs + fixed_images
        budget_rows.append({
            "train_patient_budget": "all" if budget is None else budget,
            "train_patients": int(sub.subject_id.nunique()),
            "train_studies": int(len(sub)),
            "train_frontal_images": imgs,
            "total_images_to_download": total_imgs,
            "estimated_total_gb": round(total_imgs * EST_MB_PER_IMAGE / 1024, 2),
        })

    manifests_written = []
    if write_manifests:
        manifest_dir = project_root / MANIFEST_DIR
        manifest_dir.mkdir(parents=True, exist_ok=True)
        for name in tiers:
            paths = sorted(frontal.loc[frontal.tier == name, "jpg_path"].dropna().unique())
            target = manifest_dir / f"{name}_frontal_jpg_paths.txt"
            target.write_text("\n".join(paths) + "\n", encoding="utf-8")
            manifests_written.append({
                "tier": name,
                "relative_path": f"{MANIFEST_DIR}/{target.name}",
                "line_count": len(paths),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            })

    eval_row = next(r for r in summary_rows if r["tier"] == "prespecified_eval")
    test_row = next(r for r in summary_rows if r["tier"] == "official_test")
    shrink = (eval_row["patients"] / test_row["patients"]) ** 0.5

    findings = [
        f"The prespecified evaluation partition carries {eval_row['patients']} patients and "
        f"{eval_row['studies']} studies, against {test_row['patients']} patients and "
        f"{test_row['studies']} studies in the official test split.",
        f"Standard errors scale as 1/sqrt(patients), so the partition shrinks the confirmatory "
        f"standard error by approximately {shrink:.1f}x relative to the official test split.",
        "Assignment used only patient identifiers and the frozen seed. No label, outcome, image, "
        "or model output entered the partitioning, so this is a design construction rather than "
        "a data-dependent selection.",
        f"All {len(tiers)} tiers are patient-disjoint" +
        ("." if not overlaps else f", EXCEPT: {overlaps}."),
        "Official validate and test splits are untouched and retained for secondary confirmation, "
        "so comparability with published MIMIC baselines is preserved as a reported secondary result.",
    ]

    risks = [
        "Using a non-official evaluation partition amends `official_splits_required: true`. The "
        "official splits are retained as secondary confirmation, but the primary confirmatory "
        "estimate will not be directly comparable to published official-split baselines.",
        "The image-size estimate of "
        f"{EST_MB_PER_IMAGE} MB per image is derived from the published release size divided by "
        "image count. Verify against a small sample before committing to a download budget.",
        "A reduced training budget yields weaker models. The study measures whether selective "
        "reliability transports, not peak accuracy, so this is a stated limitation rather than a "
        "defect - but it must be prespecified, not chosen after seeing results.",
        "Partition sizes were chosen for statistical adequacy and download tractability before any "
        "outcome existed. They must not be revised after any label or model output is generated.",
    ]

    return {
        "stage": STAGE,
        "title": TITLE,
        "status": "PASS" if not overlaps else "FAIL",
        "declarations": list(DECLARATIONS),
        "partition_policy": {
            "seed": PARTITION_SEED,
            "unit": "patient",
            "source_split": "train",
            "eval_patients_requested": EVAL_PATIENTS,
            "calibration_patients_requested": CALIBRATION_PATIENTS,
            "official_splits_retained_as": "secondary confirmation",
            "depends_on": "patient identifiers and frozen seed only",
        },
        "tiers": summary_rows,
        "patient_disjointness_violations": overlaps,
        "all_tiers_patient_disjoint": not overlaps,
        "image_budget_options": budget_rows,
        "estimated_mb_per_image": EST_MB_PER_IMAGE,
        "download_manifests": manifests_written,
        "manifest_location_note": (
            "path manifests contain patient and study identifiers and are written to the "
            "gitignored restricted-data tree, never to results/"
        ),
        "key_findings": findings,
        "unresolved_risks": risks,
        "compliance": {
            "labels_used_in_partitioning": False,
            "outcomes_used_in_partitioning": False,
            "images_accessed": False,
            "model_run": False,
            "chexbert_executed": False,
            "identifiers_emitted_to_results": False,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
            "numpy": np.__version__,
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
    lines = [
        f"# {STAGE} — Prespecified Patient-Disjoint Evaluation Partition",
        "",
        f"Status: **{report['status']}**",
        "",
    ]
    lines += [f"- **{d}**" for d in report["declarations"]]
    pol = report["partition_policy"]
    lines += [
        "",
        "## Partition policy",
        "",
        f"- Unit: {pol['unit']}; seed: {pol['seed']} (frozen)",
        f"- Carved from: `{pol['source_split']}` split of the Stage 3C cohort",
        f"- Depends on: {pol['depends_on']}",
        f"- Official splits: {pol['official_splits_retained_as']}",
        "",
        "## Tiers",
        "",
        "| tier | role | patients | studies | frontal images | est. GB |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["tiers"]:
        lines.append(
            f"| {row['tier']} | {row['role']} | {row['patients']} | {row['studies']} | "
            f"{row['frontal_images']} | {row['estimated_download_gb']} |"
        )
    lines += [
        "",
        f"All tiers patient-disjoint: **{report['all_tiers_patient_disjoint']}**",
        "",
        "## Image download budget options",
        "",
        "Fixed tiers (eval, calibration, official validate/test) are always required. Only the",
        "training tier is variable.",
        "",
        "| train patient budget | train patients | train studies | train images | total images | est. total GB |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["image_budget_options"]:
        lines.append(
            f"| {row['train_patient_budget']} | {row['train_patients']} | {row['train_studies']} | "
            f"{row['train_frontal_images']} | {row['total_images_to_download']} | "
            f"{row['estimated_total_gb']} |"
        )
    lines += [
        "",
        f"Size estimate assumes {report['estimated_mb_per_image']} MB per image — **verify against a "
        "sample before committing**.",
        "",
    ]
    if report["download_manifests"]:
        lines += ["## Download manifests", "", f"{report['manifest_location_note']}.", "",
                  "| tier | path | images |", "| --- | --- | ---: |"]
        for m in report["download_manifests"]:
            lines.append(f"| {m['tier']} | `{m['relative_path']}` | {m['line_count']} |")
        lines.append("")
    lines += ["## Key findings", ""]
    lines += [f"- {item}" for item in report["key_findings"]]
    lines += ["", "## Unresolved risks", ""]
    lines += [f"- {item}" for item in report["unresolved_risks"]]
    lines += [""]
    return "\n".join(lines)


def _output_guard(output_dir: Path, project_root: Path) -> None:
    names = sorted(p.name for p in output_dir.iterdir() if p.is_file())
    if names != sorted(OUTPUT_FILENAMES):
        raise IntakeContractError(f"unexpected Stage 3E output files: {names}")
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


def run(*, project_root: str | Path, write_manifests: bool = True) -> dict[str, Any]:
    root = Path(project_root).resolve()
    data_root = root / DATA_ROOT
    output_dir = root / OUTPUT_DIR

    report = build_report(data_root, write_manifests, root)

    output_dir.mkdir(parents=True, exist_ok=True)
    foreign = {p.name for p in output_dir.iterdir() if p.is_file()} - set(OUTPUT_FILENAMES)
    if foreign:
        raise IntakeContractError(f"refusing to write beside unknown artifacts: {sorted(foreign)}")

    validate_safe_payload(report, project_root=root)

    (output_dir / "stage3e_partition_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "stage3e_partition_audit.md").write_text(render_md(report), encoding="utf-8")
    (output_dir / "stage3e_partition_summary.csv").write_text(
        _csv_text(report["tiers"],
                  ["tier", "role", "patients", "studies", "frontal_images", "estimated_download_gb"]),
        encoding="utf-8",
    )
    (output_dir / "stage3e_image_budget.csv").write_text(
        _csv_text(report["image_budget_options"],
                  ["train_patient_budget", "train_patients", "train_studies",
                   "train_frontal_images", "total_images_to_download", "estimated_total_gb"]),
        encoding="utf-8",
    )

    hashed = [n for n in OUTPUT_FILENAMES if n != "stage3e_manifest.json"]
    manifest = {
        "stage": STAGE,
        "title": TITLE,
        "status": report["status"],
        "declarations": list(DECLARATIONS),
        "output_dir": OUTPUT_DIR,
        "partition_policy": report["partition_policy"],
        "artifacts": [
            {"name": n, "byte_size": (output_dir / n).stat().st_size, "sha256": sha256_file(output_dir / n)}
            for n in hashed
        ],
        "download_manifests": report["download_manifests"],
        "compliance": report["compliance"],
        "environment": report["environment"],
    }
    validate_safe_payload(manifest, project_root=root)
    (output_dir / "stage3e_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    _output_guard(output_dir, root)
    return report


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Run the C3-E6 Stage 3E partition construction")
    parser.add_argument("--project-root", type=Path, default=default_root)
    parser.add_argument("--no-manifests", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run(project_root=args.project_root, write_manifests=not args.no_manifests)
    except Exception as exc:  # noqa: BLE001
        print(f"Stage 3E FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "stage": STAGE,
        "status": report["status"],
        "disjoint": report["all_tiers_patient_disjoint"],
        "tiers": {r["tier"]: r["patients"] for r in report["tiers"]},
    }, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
