from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
import numpy as np
import yaml

from .text import normalize, token_count, classify_mentions, is_low_information

def load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_context(df: pd.DataFrame, context_columns: list[str]) -> pd.Series:
    missing = [c for c in context_columns if c not in df.columns]
    if len(missing) == len(context_columns):
        raise KeyError(f"None of the configured context columns exist: {context_columns}")
    present = [c for c in context_columns if c in df.columns]
    values = df[present].fillna("").astype(str)
    return values.apply(lambda r: " ".join(x.strip() for x in r if x.strip()).strip(), axis=1)

def add_context_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    out = df.copy()
    if "context" not in out.columns:
        out["context"] = build_context(out, cfg["context_columns"])
    out["context"] = out["context"].map(normalize)
    out["context_present"] = out["context"].str.len().gt(0)
    out["context_tokens"] = out["context"].map(token_count)
    low_cfg = cfg["low_information"]
    out["context_low_info"] = out["context"].map(
        lambda x: is_low_information(x, low_cfg["min_tokens"], low_cfg["generic_phrases"])
    )
    out["context_usable"] = out["context_present"] & ~out["context_low_info"]
    out["context_state"] = np.select(
        [~out["context_present"], out["context_low_info"], out["context_usable"]],
        ["absent", "low_information", "usable"],
        default="unknown",
    )
    return out

def add_frontal_feature(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    out = df.copy()
    col = cfg.get("view_column")
    if col and col in out.columns:
        valid = {str(x).upper() for x in cfg.get("frontal_values", ["AP", "PA"])}
        out["is_frontal"] = out[col].astype(str).str.upper().isin(valid)
    else:
        out["is_frontal"] = True
    return out

def add_mentions(df: pd.DataFrame, cfg: dict, terms: dict) -> pd.DataFrame:
    out = df.copy()
    for label in cfg["labels"]:
        label_terms = terms.get(label, {})
        direct = label_terms.get("direct", [label.lower()])
        synonyms = label_terms.get("synonyms", [])
        all_terms = list(dict.fromkeys(direct + synonyms))
        direct_col = f"{label}__direct"
        out[direct_col] = out["context"].map(
            lambda t: classify_mentions(t, direct)["mention_any"]
        )
        cls = out["context"].map(lambda t: classify_mentions(t, all_terms))
        for key in ("mention_any", "mention_affirmed", "mention_negated", "mention_speculative"):
            out[f"{label}__{key}"] = cls.map(lambda d: d[key])
    return out

def section_availability(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    rows = []
    for state, count in df["context_state"].value_counts(dropna=False).items():
        rows.append({"context_state": state, "studies": int(count), "fraction": float(count / total)})
    return pd.DataFrame(rows).sort_values("context_state")

def label_prevalence(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rows = []
    for label in cfg["labels"]:
        if label not in df.columns:
            rows.append({"label": label, "status": "missing_column"})
            continue
        s = pd.to_numeric(df[label], errors="coerce")
        rows.append({
            "label": label,
            "status": "ok",
            "n": int(s.notna().sum()),
            "positive": int((s == cfg["positive_value"]).sum()),
            "negative": int((s == cfg["negative_value"]).sum()),
            "uncertain": int((s == cfg["uncertain_value"]).sum()),
            "unmentioned_or_missing": int(s.isna().sum()),
            "positive_fraction_known": float((s == cfg["positive_value"]).sum() / max(1, s.notna().sum())),
        })
    return pd.DataFrame(rows)

def leakage_by_label(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rows = []
    for label in cfg["labels"]:
        if label not in df.columns:
            continue
        y = pd.to_numeric(df[label], errors="coerce")
        for subset_name, mask in {
            "all": pd.Series(True, index=df.index),
            "positive": y.eq(cfg["positive_value"]),
            "negative": y.eq(cfg["negative_value"]),
            "uncertain": y.eq(cfg["uncertain_value"]),
        }.items():
            n = int(mask.sum())
            row = {"label": label, "subset": subset_name, "n": n}
            for key in ("direct", "mention_any", "mention_affirmed", "mention_negated", "mention_speculative"):
                col = f"{label}__{key}"
                row[f"{key}_fraction"] = float(df.loc[mask, col].mean()) if n else None
            rows.append(row)
    return pd.DataFrame(rows)

def missingness_by_label(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rows = []
    for label in cfg["labels"]:
        if label not in df.columns:
            continue
        y = pd.to_numeric(df[label], errors="coerce")
        for status_name, val in (
            ("positive", cfg["positive_value"]),
            ("negative", cfg["negative_value"]),
            ("uncertain", cfg["uncertain_value"]),
        ):
            mask = y.eq(val)
            n = int(mask.sum())
            rows.append({
                "label": label,
                "label_state": status_name,
                "n": n,
                "context_absent_fraction": float((~df.loc[mask, "context_present"]).mean()) if n else None,
                "context_low_info_fraction": float(df.loc[mask, "context_low_info"].mean()) if n else None,
                "context_usable_fraction": float(df.loc[mask, "context_usable"].mean()) if n else None,
            })
    return pd.DataFrame(rows)

def split_overlap(df: pd.DataFrame, cfg: dict) -> dict:
    split_col = cfg.get("split_column")
    patient_col = cfg["id_columns"]["patient"]
    if not split_col or split_col not in df.columns or patient_col not in df.columns:
        return {"available": False}
    groups = {
        str(split): set(g[patient_col].dropna().astype(str))
        for split, g in df.groupby(split_col)
    }
    names = sorted(groups)
    overlaps = {}
    for i, a in enumerate(names):
        for b in names[i+1:]:
            overlaps[f"{a}__{b}"] = len(groups[a] & groups[b])
    return {"available": True, "patients_per_split": {k: len(v) for k, v in groups.items()}, "overlap": overlaps}

def gate_report(df: pd.DataFrame, cfg: dict, role: str) -> dict:
    gate = cfg["gate"]
    section = section_availability(df)
    fractions = dict(zip(section["context_state"], section["fraction"]))
    pos_threshold = gate["min_source_positive"] if role == "source" else gate["min_target_positive"]
    viable = []
    leakage_fail = []
    for label in cfg["labels"]:
        if label not in df.columns:
            continue
        y = pd.to_numeric(df[label], errors="coerce")
        pos_n = int(y.eq(cfg["positive_value"]).sum())
        direct_col = f"{label}__direct"
        pos_mask = y.eq(cfg["positive_value"])
        direct_frac = float(df.loc[pos_mask, direct_col].mean()) if pos_n else 1.0
        if pos_n >= pos_threshold:
            viable.append(label)
        if pos_n >= pos_threshold and direct_frac > gate["max_direct_mention_fraction_among_positives"]:
            leakage_fail.append({"label": label, "direct_fraction": direct_frac})
    missing_or_low = fractions.get("absent", 0.0) + fractions.get("low_information", 0.0)
    checks = {
        "usable_context": fractions.get("usable", 0.0) >= gate["min_usable_context_fraction"],
        "enough_missing_or_low_information": missing_or_low >= gate["min_missing_or_low_info_fraction"],
        "enough_viable_labels": len(viable) >= gate["min_viable_labels"],
        "direct_mentions_below_limit_for_viable_labels": len(leakage_fail) == 0,
    }
    return {
        "role": role,
        "checks": checks,
        "passed": all(checks.values()),
        "viable_labels": viable,
        "leakage_failures": leakage_fail,
        "fractions": {
            "usable": fractions.get("usable", 0.0),
            "absent": fractions.get("absent", 0.0),
            "low_information": fractions.get("low_information", 0.0),
        },
    }

def write_outputs(df: pd.DataFrame, cfg: dict, output: str | Path, role: str) -> None:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    section_availability(df).to_csv(output / "section_availability.csv", index=False)
    label_prevalence(df, cfg).to_csv(output / "label_prevalence.csv", index=False)
    leakage_by_label(df, cfg).to_csv(output / "leakage_by_label.csv", index=False)
    missingness_by_label(df, cfg).to_csv(output / "missingness_by_label.csv", index=False)
    safe_summary = {
        "dataset_name": cfg["dataset_name"],
        "studies": int(len(df)),
        "frontal_studies": int(df["is_frontal"].sum()),
        "median_context_tokens": float(df["context_tokens"].median()),
        "patient_split_check": split_overlap(df, cfg),
    }
    with open(output / "summary.json", "w", encoding="utf-8") as f:
        json.dump(safe_summary, f, indent=2)
    with open(output / "gate_report.json", "w", encoding="utf-8") as f:
        json.dump(gate_report(df, cfg, role), f, indent=2)
    # Sensitive local artifact: contains identifiers and text. Never share externally.
    df.to_csv(output / "study_aggregate.csv", index=False)
