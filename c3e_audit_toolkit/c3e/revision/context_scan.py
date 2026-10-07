"""Aggregate scan of extracted pre-diagnostic context (post hoc; Revision R1).

Section headers show where text sits in a report, not when it was written.
This scan counts, per site, the share of intervention-cohort studies whose
extracted context contains report-section headers, conclusion-style phrases,
comparison language, query language, or a target-finding term. Only shares are
emitted; no text leaves the protected environment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .c2_audit import TARGET_TERMS
from .inference import frames

PATTERNS = {
    "report_section_header": r"\b(?:findings|impression|wet read|addendum|conclusion)\s*:",
    "conclusion_language": (r"\b(?:consistent with|compatible with|suggestive of|likely represents|"
                            r"no acute cardiopulmonary|unchanged from|interval (?:improvement|worsening|"
                            r"increase|decrease)|again (?:seen|noted|demonstrated))\b"),
    "comparison_language": r"\b(?:compared (?:to|with)|comparison|prior (?:study|exam|radiograph|film))\b",
    "query_language": r"(?:\?|\b(?:eval|evaluate|r/o|rule out|assess|concern for|question)\b)",
    "names_a_target_finding": "|".join(t for v in TARGET_TERMS.values() for t in v),
}


def scan(root: Path) -> list[dict[str, Any]]:
    rows = []
    for site, tier in (("source", "prespecified_eval"), ("external", "external")):
        df = frames(Path(root), site, tier, conditions=("C0",))["C0"].drop_duplicates("study_id")
        text = df["context"].astype(str).str.lower()
        for name, pat in PATTERNS.items():
            rows.append({"site": site, "pattern": name, "studies": int(len(df)),
                         "share": float(text.str.contains(pat, regex=True).mean())})
    return rows
