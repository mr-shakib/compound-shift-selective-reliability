from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
from .text import token_count

def compare(source_path: str | Path, target_path: str | Path, output: str | Path) -> None:
    source = pd.read_csv(source_path)
    target = pd.read_csv(target_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, df in (("source", source), ("target", target)):
        rows.append({
            "site": name,
            "n": len(df),
            "context_present_fraction": float(df["context_present"].mean()),
            "context_low_info_fraction": float(df["context_low_info"].mean()),
            "context_usable_fraction": float(df["context_usable"].mean()),
            "median_context_tokens": float(df["context_tokens"].median()),
            "frontal_fraction": float(df["is_frontal"].mean()),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(output / "cross_site_comparison.csv", index=False)

    src = summary.set_index("site").loc["source"]
    tgt = summary.set_index("site").loc["target"]
    diffs = {
        "usable_context_absolute_difference": float(tgt["context_usable_fraction"] - src["context_usable_fraction"]),
        "low_info_absolute_difference": float(tgt["context_low_info_fraction"] - src["context_low_info_fraction"]),
        "median_token_difference": float(tgt["median_context_tokens"] - src["median_context_tokens"]),
    }
    meaningful = (
        abs(diffs["usable_context_absolute_difference"]) >= 0.05
        or abs(diffs["low_info_absolute_difference"]) >= 0.05
        or abs(diffs["median_token_difference"]) >= 3
    )
    report = {
        "cross_site_missingness_or_quality_shift_detected": bool(meaningful),
        "differences": diffs,
    }
    with open(output / "cross_site_gate.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
