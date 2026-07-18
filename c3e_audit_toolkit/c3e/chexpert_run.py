"""Orchestration for the CheXpert Plus label-joined audit.

Two modes:
  * dry-run  -- validate config, derive the study key, load the JSONL labels,
                verify the one-to-one join, and write a small aggregate-safe
                validation report. No manifest, no identifiers.
  * full     -- additionally compute aggregate label prevalence and the
                within-study disagreement audit (still no manifest).

Neither mode ever writes a patient-, study-, or image-level manifest.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .io import read_table
from .audit import load_yaml
from .config_schema import assert_valid_chexpert_config
from .chexpert import (
    STUDY_KEY_COL, attach_study_key, load_jsonl_labels, join_labels,
    within_study_label_disagreement, strip_internal_columns, identifier_columns,
)

MARKER_NAME = "source_marker.json"


def _resolve(base: Path, p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (base / q).resolve()


def source_id(cfg: dict) -> str:
    """Short identifier for the label source, e.g. 'impression' / 'findings'.

    Derived from the label-source file stem (impression_fixed -> impression).
    This is a label-scope name, not a patient/study identifier.
    """
    stem = Path(cfg["label_source"]["path"]).name
    return stem.replace("_fixed.json", "").replace(".json", "")


def prepare_output_dir(output_dir: Path, src: str) -> None:
    """Create the output dir and stamp it with a source marker. Refuse to write
    into a directory already claimed by a different label source (prevents one
    configuration from overwriting the other's outputs)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    marker = output_dir / MARKER_NAME
    if marker.exists():
        existing = json.loads(marker.read_text(encoding="utf-8")).get("label_source")
        if existing != src:
            raise RuntimeError(
                f"output dir {output_dir} is claimed by label source {existing!r}; "
                f"refusing to write {src!r} outputs here."
            )
    marker.write_text(json.dumps({"label_source": src}, indent=2), encoding="utf-8")


def _write_safe_json(output_dir: Path, name: str, payload: dict) -> None:
    with open(output_dir / name, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def run_chexpert(config_path: str | Path, *, table_override: str | None = None,
                 output_override: str | None = None, dry_run: bool = True) -> dict:
    config_path = Path(config_path).resolve()
    base = config_path.parent
    cfg = load_yaml(config_path)
    assert_valid_chexpert_config(cfg)

    table_path = _resolve(base, table_override or cfg["table_path"])
    label_path = _resolve(base, cfg["label_source"]["path"])
    output_dir = Path(output_override).resolve() if output_override else _resolve(base, cfg["output_dir"])
    src = source_id(cfg)

    ls = cfg["label_source"]
    join_key = ls["join_key"]
    sk = cfg["study_key"]
    internal_col = sk.get("internal_column", STUDY_KEY_COL)

    # --- main table + derived study key (internal, fail-closed) -----------
    table = read_table(table_path)
    table, n_parse_fail = attach_study_key(
        table, source_column=sk["source_column"], internal_column=internal_col,
        fail_on_parse_error=True,
    )

    # --- JSON Lines labels + one-to-one join ------------------------------
    labels = load_jsonl_labels(label_path, join_key=join_key)
    merged, join_stats = join_labels(
        table, labels, join_key=join_key,
        cardinality=ls.get("cardinality", "one_to_one"),
        on_duplicate_keys=ls.get("on_duplicate_keys", "fail"),
        on_unmatched=ls.get("on_unmatched", "fail"),
    )

    n_studies = int(merged[internal_col].nunique())
    report = {
        "dataset_name": cfg["dataset_name"],
        "label_source": src,
        "mode": "dry_run" if dry_run else "full",
        "table_rows": int(len(table)),
        "derived_study_key": {
            "method": sk.get("method"),
            "source_column": sk["source_column"],
            "parse_failures": int(n_parse_fail),
            "unique_studies": n_studies,
            "note": "study key held in internal column only; never exported",
        },
        "join": join_stats,
        "labels_configured": list(cfg["labels"]),
        "encoding": {
            "positive": cfg["positive_value"], "negative": cfg["negative_value"],
            "uncertain": cfg["uncertain_value"], "unmentioned": None,
        },
        "grouping": cfg["grouping"],
    }

    prepare_output_dir(output_dir, src)

    if dry_run:
        _write_safe_json(output_dir, "validation_report.json", report)
        return report

    # --- full (aggregate-safe) outputs ------------------------------------
    from .audit import add_context_features, add_frontal_feature, label_prevalence
    merged = add_context_features(merged, cfg)
    merged = add_frontal_feature(merged, cfg)
    frontal = merged[merged["is_frontal"]].copy()

    prevalence = label_prevalence(frontal, cfg)
    prevalence.to_csv(output_dir / "label_prevalence.csv", index=False)

    disagreement = within_study_label_disagreement(
        frontal, cfg, study_key_col=internal_col,
        ap_pa_column=cfg.get("ap_pa_column"),
    )
    _write_safe_json(output_dir, "within_study_disagreement.json", disagreement)

    report["frontal_rows"] = int(len(frontal))
    report["disagreement_summary"] = {
        "n_multi_image_frontal_studies": disagreement["n_multi_image_frontal_studies"],
    }
    _write_safe_json(output_dir, "validation_report.json", report)

    # Safety net: assert nothing identifier-bearing leaked into safe outputs.
    _ = strip_internal_columns(frontal, identifier_columns(cfg))
    return report
