"""C3-E6 Stage 4: generate CheXbert labels for the MIMIC source site.

Runs the validated CheXbert port over two report scopes, matching the frozen
label-source policy:

- impression scope -> primary label endpoint
- findings scope   -> sensitivity label endpoint

Row-level labels are restricted data and are written only into the gitignored
data tree. Nothing but aggregate prevalence and provenance reaches results/.

The port must pass its fidelity gate against the upstream reference labels
before any project label is generated; this runner refuses to proceed otherwise.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys
import time
from typing import Any
import zipfile

import pandas as pd

from ..mimic_intake.contracts import IntakeContractError
from ..mimic_intake.safety import validate_safe_payload
from ..mimic_intake.stage3b_reports import HEADER_RE, SECTION_MAP, sha256_file
from ..mimic_intake.stage3c_cohort import (
    FRONTAL_VIEWS,
    IMAGE_METADATA,
    SPLIT_FILE,
    STUDY_LIST,
    THRESHOLD_PRIMARY,
    _parse_reports,
)
from ..mimic_intake.stage3e_partition import assign_partitions
from .chexbert_port import C3E_TARGETS, CheXbertLabeler, validate_against_reference

STAGE = "C3-E6 Stage 4"
TITLE = "SOURCE-SITE LABEL GENERATION (CHEXBERT)"

DECLARATIONS = (
    "STAGE 4 ONLY",
    "LABEL GENERATION AT THE SOURCE SITE",
    "NO MEDICAL IMAGES OPENED",
    "NO MODEL TRAINING",
    "NO PREDICTION THRESHOLD SELECTION",
    "NO EVALUATION OR METRIC COMPUTATION",
    "NO EXTERNAL SITE LABELS GENERATED IN THIS RUN",
    "ROW-LEVEL LABELS CONFINED TO THE PROTECTED DATA TREE",
    "NO REPORT TEXT EXPORTED",
)

OUTPUT_FILENAMES = (
    "stage4_label_summary.json",
    "stage4_label_summary.md",
    "stage4_label_prevalence.csv",
    "stage4_provenance.json",
    "stage4_manifest.json",
)

DATA_ROOT = "data/mimic"
OUTPUT_DIR = "results/c3e_mimic/stage4_labels"
LABEL_DIR = "data/mimic/labels"  # gitignored; row-level restricted output
REPORTS_ZIP = "reports/mimic-cxr-reports.zip"

IMPRESSION_SECTIONS = ("impression",)
FINDINGS_SECTIONS = ("findings",)


def extract_sections(text: str, wanted: tuple[str, ...]) -> str:
    """Concatenate the requested canonical sections, header-driven."""
    matches = list(HEADER_RE.finditer(text))
    parts: list[str] = []
    for position, match in enumerate(matches):
        raw = re.sub(r"\s+", " ", match.group(1)).strip()
        mapped = SECTION_MAP.get(raw)
        if mapped is None or mapped[0] not in wanted:
            continue
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        if body:
            parts.append(body)
    return " ".join(parts)


def build_cohort(data_root: Path) -> pd.DataFrame:
    study = pd.read_csv(data_root / STUDY_LIST, dtype=str)
    meta = pd.read_csv(data_root / IMAGE_METADATA, dtype=str)
    split = pd.read_csv(data_root / SPLIT_FILE, dtype=str)
    frontal_studies = set(meta.loc[meta.ViewPosition.isin(FRONTAL_VIEWS), "study_id"])
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
    return assign_partitions(frame[eligible])


def read_scope_text(data_root: Path, paths: set[str], wanted: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    with zipfile.ZipFile(data_root / REPORTS_ZIP) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename not in paths:
                continue
            text = zf.read(info).decode("utf-8", errors="replace")
            out[info.filename] = extract_sections(text, wanted)
            del text
    return out


def _prevalence(frame: pd.DataFrame, endpoint: str) -> list[dict[str, Any]]:
    rows = []
    total = len(frame)
    for name in C3E_TARGETS:
        col = frame[name]
        positive = int((col == 1.0).sum())
        negative = int((col == 0.0).sum())
        uncertain = int((col == -1.0).sum())
        unmentioned = int(col.isna().sum())
        rows.append({
            "endpoint": endpoint,
            "pathology": name,
            "studies": total,
            "positive": positive,
            "negative": negative,
            "uncertain": uncertain,
            "unmentioned": unmentioned,
            "positive_fraction": round(positive / total, 6) if total else 0.0,
            "uncertain_fraction": round(uncertain / total, 6) if total else 0.0,
            "unmentioned_fraction": round(unmentioned / total, 6) if total else 0.0,
        })
    return rows


def run(*, project_root: str | Path, checkpoint: str | Path, batch_size: int = 32,
        limit: int | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    data_root = root / DATA_ROOT
    output_dir = root / OUTPUT_DIR
    label_dir = root / LABEL_DIR
    label_dir.mkdir(parents=True, exist_ok=True)

    labeler = CheXbertLabeler(checkpoint, batch_size=batch_size)

    # Fidelity gate. Refuse to label project data with an unvalidated port.
    gate = validate_against_reference(labeler, root / "data/models/CheXbert/src")
    if not gate["exact_match"]:
        raise IntakeContractError(
            f"CheXbert port failed its fidelity gate: {gate['cells_agreeing']}/"
            f"{gate['cells_compared']} cells agree. Refusing to label project data."
        )

    cohort = build_cohort(data_root)
    if limit:
        cohort = cohort.head(limit)
    paths = set(cohort["path"])

    endpoints = {
        "impression": IMPRESSION_SECTIONS,
        "findings": FINDINGS_SECTIONS,
    }
    # Endpoint names are carried as values, never as mapping keys: the shared
    # safe-payload validator reserves 'findings' and 'impression' as unsafe keys.
    summaries: list[dict[str, Any]] = []
    prevalence_rows: list[dict[str, Any]] = []
    written: list[dict[str, Any]] = []

    for endpoint, wanted in endpoints.items():
        started = time.time()
        texts = read_scope_text(data_root, paths, wanted)
        sub = cohort[cohort["path"].map(lambda p: bool(texts.get(p, "").strip()))].copy()
        reports = [texts[p] for p in sub["path"]]

        labels = labeler.label_c3e_targets(reports)
        label_frame = pd.DataFrame(labels)
        for name in C3E_TARGETS:
            sub[name] = label_frame[name].values

        target = label_dir / f"mimic_{endpoint}_labels.csv"
        keep = ["subject_id", "study_id", "split", "tier", *C3E_TARGETS]
        sub[keep].to_csv(target, index=False)
        written.append({
            "endpoint": endpoint,
            "relative_path": f"{LABEL_DIR}/{target.name}",
            "rows": int(len(sub)),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        })

        prevalence_rows.extend(_prevalence(sub, endpoint))
        summaries.append({
            "endpoint": endpoint,
            "studies_with_scope_text": int(len(sub)),
            "studies_in_cohort": int(len(cohort)),
            "coverage_fraction": round(len(sub) / len(cohort), 6) if len(cohort) else 0.0,
            "elapsed_seconds": round(time.time() - started, 1),
        })

    provenance = {
        "stage": STAGE,
        "labeler": labeler.provenance().as_dict(),
        "checkpoint_source": "https://huggingface.co/StanfordAIMI/RRG_scorers (chexbert.pth)",
        "checkpoint_source_note": (
            "the upstream repository's Box link returns HTTP 404 (issues #9-#12); "
            "StanfordAIMI is the same lab and hosts the checkpoint on HuggingFace"
        ),
        "fidelity_gate": {k: v for k, v in gate.items() if k != "disagreements"},
        "port_deviations": [
            "encoder built from explicit BertConfig rather than from_pretrained; upstream "
            "overwrites all pretrained weights from the checkpoint, so the download is redundant",
            "nn.DataParallel not used; the checkpoint's 'module.' key prefix is stripped explicitly",
            "tokenizer encode_plus (removed in transformers 5.x) replaced by explicit "
            "[CLS] + convert_tokens_to_ids + [SEP], which is what it did for pre-tokenized input",
        ],
        "state_dict_load": {
            "missing_keys": len(labeler.missing_keys),
            "unexpected_keys": len(labeler.unexpected_keys),
        },
        "label_encoding": {"positive": 1.0, "negative": 0.0, "uncertain": -1.0, "unmentioned": None},
        "section_extraction": "header-driven, frozen synonym map from experiment_registry text_policy",
        "missing_section_behavior": "study omitted from that endpoint; not imputed",
        "row_level_outputs": written,
        "row_level_location_note": (
            "row-level labels contain patient and study identifiers and are confined to the "
            "gitignored data tree; only aggregates appear under results/"
        ),
    }

    report = {
        "stage": STAGE,
        "title": TITLE,
        "status": "PASS",
        "declarations": list(DECLARATIONS),
        "cohort_studies": int(len(cohort)),
        "endpoints": summaries,
        "prevalence": prevalence_rows,
        "fidelity_gate_passed": gate["exact_match"],
        "compliance": {
            "images_accessed": False,
            "model_training": False,
            "threshold_selection": False,
            "evaluation_performed": False,
            "report_text_exported": False,
            "external_site_labels_generated": False,
            "identifiers_emitted_to_results": False,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
        },
    }

    _write_outputs(output_dir, report, provenance, root)
    return report


def _csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return stream.getvalue()


def _render_md(report: dict[str, Any]) -> str:
    lines = [
        f"# {STAGE} — Source-Site Label Generation",
        "",
        f"Status: **{report['status']}**",
        "",
    ]
    lines += [f"- **{d}**" for d in report["declarations"]]
    lines += [
        "",
        f"Fidelity gate passed: **{report['fidelity_gate_passed']}**",
        f"Cohort studies: {report['cohort_studies']}",
        "",
        "## Endpoint coverage",
        "",
        "| endpoint | studies with scope text | coverage | elapsed (s) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for meta in report["endpoints"]:
        lines.append(
            f"| {meta['endpoint']} | {meta['studies_with_scope_text']} | {meta['coverage_fraction']:.4%} | "
            f"{meta['elapsed_seconds']} |"
        )
    lines += [
        "",
        "## Label prevalence",
        "",
        "| endpoint | pathology | positive | negative | uncertain | unmentioned | positive % |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["prevalence"]:
        lines.append(
            f"| {row['endpoint']} | {row['pathology']} | {row['positive']} | {row['negative']} | "
            f"{row['uncertain']} | {row['unmentioned']} | {row['positive_fraction']:.2%} |"
        )
    lines += [
        "",
        "Row-level labels are restricted data and are not included here.",
        "",
    ]
    return "\n".join(lines)


def _write_outputs(output_dir: Path, report: dict[str, Any], provenance: dict[str, Any],
                   project_root: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    foreign = {p.name for p in output_dir.iterdir() if p.is_file()} - set(OUTPUT_FILENAMES)
    if foreign:
        raise IntakeContractError(f"refusing to write beside unknown artifacts: {sorted(foreign)}")

    validate_safe_payload(report, project_root=project_root)

    (output_dir / "stage4_label_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "stage4_label_summary.md").write_text(_render_md(report), encoding="utf-8")
    (output_dir / "stage4_label_prevalence.csv").write_text(
        _csv_text(report["prevalence"],
                  ["endpoint", "pathology", "studies", "positive", "negative", "uncertain",
                   "unmentioned", "positive_fraction", "uncertain_fraction",
                   "unmentioned_fraction"]),
        encoding="utf-8")
    (output_dir / "stage4_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    hashed = [n for n in OUTPUT_FILENAMES if n != "stage4_manifest.json"]
    manifest = {
        "stage": STAGE,
        "title": TITLE,
        "status": report["status"],
        "declarations": list(DECLARATIONS),
        "output_dir": OUTPUT_DIR,
        "artifacts": [
            {"name": n, "byte_size": (output_dir / n).stat().st_size,
             "sha256": sha256_file(output_dir / n)}
            for n in hashed
        ],
        "compliance": report["compliance"],
        "environment": report["environment"],
    }
    validate_safe_payload(manifest, project_root=project_root)
    (output_dir / "stage4_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    restricted = re.compile(
        r"(?:patient|subject|study|image)\d+|(?:^|[/\\])[ps]\d{3,}(?:[/\\]|\.|$)", re.IGNORECASE)
    root_text = str(project_root.resolve())
    for path in sorted(output_dir.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if root_text in text:
            raise IntakeContractError(f"absolute project path leaked into {path.name}")
        if restricted.search(text):
            raise IntakeContractError(f"restricted row-level value detected in {path.name}")


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Run C3-E6 Stage 4 CheXbert label generation")
    parser.add_argument("--project-root", type=Path, default=default_root)
    parser.add_argument("--checkpoint", type=Path,
                        default=default_root / "data/models/chexbert/chexbert.pth")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    try:
        report = run(project_root=args.project_root, checkpoint=args.checkpoint,
                     batch_size=args.batch_size, limit=args.limit)
    except Exception as exc:  # noqa: BLE001
        print(f"Stage 4 FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"stage": STAGE, "status": report["status"],
                      "endpoints": report["endpoints"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
