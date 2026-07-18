from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

from .io import read_table
from .reports import read_mimic_reports
from .audit import (
    load_yaml, add_context_features, add_frontal_feature, add_mentions, write_outputs
)
from .compare import compare
from .chexpert_run import run_chexpert

def mimic(args):
    cfg = load_yaml(args.config)
    terms = load_yaml(args.terms)
    reports = read_mimic_reports(args.reports)
    labels = read_table(args.labels)
    metadata = read_table(args.metadata)
    splits = read_table(args.splits)

    # Collapse image-level metadata to one frontal-preferred record per study.
    if "ViewPosition" in metadata.columns:
        metadata["_frontal_rank"] = metadata["ViewPosition"].astype(str).str.upper().isin(
            {str(v).upper() for v in cfg.get("frontal_values", ["AP", "PA"])}
        ).astype(int)
        metadata = metadata.sort_values(
            ["study_id", "_frontal_rank"], ascending=[True, False]
        ).drop_duplicates("study_id")
        metadata = metadata.drop(columns=["_frontal_rank"])

    split_cols = [c for c in ["subject_id", "study_id", "split"] if c in splits.columns]
    study_splits = splits[split_cols].drop_duplicates("study_id")
    df = reports.merge(labels, on="study_id", how="inner", suffixes=("", "_label"))
    if "subject_id_label" in df.columns and "subject_id" not in df.columns:
        df = df.rename(columns={"subject_id_label": "subject_id"})
    elif "subject_id_label" in df.columns:
        df["subject_id"] = df["subject_id"].fillna(df["subject_id_label"])
        df = df.drop(columns=["subject_id_label"])
    df = df.merge(metadata, on="study_id", how="left", suffixes=("", "_meta"))
    df = df.merge(study_splits, on="study_id", how="left", suffixes=("", "_split"))
    for c in ("subject_id_split",):
        if c in df.columns:
            if "subject_id" not in df.columns:
                df = df.rename(columns={c: "subject_id"})
            else:
                df["subject_id"] = df["subject_id"].fillna(df[c])
                df = df.drop(columns=[c])

    df = add_context_features(df, cfg)
    df = add_frontal_feature(df, cfg)
    df = df[df["is_frontal"]].copy()
    df = add_mentions(df, cfg, terms)
    write_outputs(df, cfg, args.output, role="source")
    print(f"Wrote local audit outputs to {args.output}")

def table(args):
    cfg = load_yaml(args.config)
    terms = load_yaml(args.terms)
    df = read_table(args.table)
    df = add_context_features(df, cfg)
    df = add_frontal_feature(df, cfg)
    df = df[df["is_frontal"]].copy()
    df = add_mentions(df, cfg, terms)
    write_outputs(df, cfg, args.output, role="target")
    print(f"Wrote local audit outputs to {args.output}")

def do_compare(args):
    compare(args.source, args.target, args.output)
    print(f"Wrote cross-site comparison to {args.output}")

def chexpert(args):
    if args.dry_run:
        report = run_chexpert(
            args.config, table_override=args.table,
            output_override=args.output, dry_run=True,
        )
        print(f"CheXpert dry-run validation complete for label source "
              f"'{report['label_source']}'.")
        print(f"  table rows:      {report['table_rows']}")
        print(f"  unique studies:  {report['derived_study_key']['unique_studies']}")
        print(f"  parse failures:  {report['derived_study_key']['parse_failures']}")
        print(f"  join cardinality:{report['join']['cardinality']} "
              f"(unmatched main={report['join']['unmatched_main_rows']}, "
              f"label={report['join']['unmatched_label_records']})")
        return
    from .chexpert_audit import run_full_audit
    res = run_full_audit(args.config, table_override=args.table, output_override=args.output)
    s = res["summary"]
    print(f"CheXpert FULL audit complete for label source '{res['source']}'.")
    print(f"  output dir:      {res['output_dir']}")
    print(f"  frontal images:  {s['cohort_structure']['frontal_image_rows']}")
    print(f"  frontal studies: {s['cohort_structure']['study_count_frontal']}")
    print(f"  gate passed:     {s['gate_passed']}")

def main():
    parser = argparse.ArgumentParser(prog="c3e-audit")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("mimic")
    p.add_argument("--reports", required=True)
    p.add_argument("--labels", required=True)
    p.add_argument("--metadata", required=True)
    p.add_argument("--splits", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--terms", default=str(Path(__file__).resolve().parents[1] / "configs" / "terms.yaml"))
    p.add_argument("--output", required=True)
    p.set_defaults(func=mimic)

    p = sub.add_parser("table")
    p.add_argument("--table", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--terms", default=str(Path(__file__).resolve().parents[1] / "configs" / "terms.yaml"))
    p.add_argument("--output", required=True)
    p.set_defaults(func=table)

    p = sub.add_parser("compare")
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=do_compare)

    p = sub.add_parser("chexpert", help="Validate/join a CheXpert Plus config with JSONL labels")
    p.add_argument("--config", required=True)
    p.add_argument("--table", default=None, help="override table_path in the config")
    p.add_argument("--output", default=None, help="override output_dir in the config")
    p.add_argument("--dry-run", action="store_true",
                   help="validate config + labels + join only; no aggregate outputs, no manifest")
    p.set_defaults(func=chexpert)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
