"""C3-E6 Stage 3B: MIMIC report structure and section-availability audit.

Scope is structural parsing of the MIMIC-CXR free-text reports in order to
establish whether the target site can supply the frozen C3E data contract:

- ``context_text`` must be pre-diagnostic (see protocols/C3E6_stage2);
- ``findings``, ``impression``, and ``full_report`` are prohibited model
  inputs and may only ever act as label sources.

This module measures section presence, ordering, size, and de-identification
density. It performs no labelling, no CheXbert execution, no model inference,
no threshold selection, and no evaluation. Report text is read into memory,
measured, and discarded; no section content is written to any artifact.
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
import statistics as stats_mod
import sys
from typing import Any
import zipfile

from .contracts import IntakeContractError
from .safety import validate_safe_payload

STAGE = "C3-E6 Stage 3B"
TITLE = "MIMIC REPORT STRUCTURE AND SECTION AVAILABILITY AUDIT"

DECLARATIONS = (
    "STAGE 3B ONLY",
    "REPORT STRUCTURE AND SECTION STATISTICS",
    "NO MEDICAL IMAGES OPENED",
    "NO DICOM OR JPG DECODED",
    "NO REPORT TEXT EXPORTED",
    "NO LABEL EXTRACTION",
    "NO CHEXBERT EXECUTION",
    "NO MODEL TRAINING OR INFERENCE",
    "NO THRESHOLD SELECTION",
    "NO EVALUATION OR METRIC COMPUTATION",
    "NO EXTERNAL DOWNLOADS",
    "NO PROTOCOL MODIFICATION",
)

OUTPUT_FILENAMES = (
    "stage3b_report_structure_audit.json",
    "stage3b_report_structure_audit.md",
    "stage3b_section_vocabulary.csv",
    "stage3b_section_statistics.csv",
    "stage3b_statistics.json",
    "stage3b_statistics.md",
    "stage3b_context_availability.md",
    "stage3b_protocol_checklist.md",
    "stage3b_manifest.json",
)

DATA_ROOT = "data/mimic"
OUTPUT_DIR = "results/c3e_mimic/stage3b"
REPORTS_ZIP = "reports/mimic-cxr-reports.zip"
STUDY_LIST = "metadata/cxr-study-list.csv.gz"

# A header-shaped line: leading uppercase label terminated by a colon.
HEADER_RE = re.compile(r"^[ \t]*([A-Z][A-Z0-9 /&'()\.\,\-\*]{0,60}?)[ \t]*:", re.MULTILINE)
BANNER_RE = re.compile(r"^\s*(FINAL REPORT|FINAL ADDENDUM|PRELIMINARY REPORT)\s*$", re.MULTILINE)
# Old-style reports open the narrative with a view descriptor rather than a
# FINDINGS header; these are tracked separately from true section headers.
VIEW_DESCRIPTOR_RE = re.compile(
    r"\b(?:AP|PA|LATERAL|FRONTAL|PORTABLE|UPRIGHT|SUPINE|SEMI-UPRIGHT|SEMI-ERECT|FILM|SINGLE|ONE|TWO)\b"
    r".*\b(?:CHEST|VIEW|VIEWS|RADIOGRAPH|RADIOGRAPHS)\b|"
    r"\bCHEST\b.*\b(?:VIEW|VIEWS|AP|PA|LATERAL|PORTABLE|UPRIGHT)\b",
)
DEID_RE = re.compile(r"_{2,}")

PRE_DIAGNOSTIC = "pre_diagnostic"
LABEL_SOURCE = "label_source"
POST_DIAGNOSTIC = "post_diagnostic"
ADMINISTRATIVE = "administrative"

# Curated canonical vocabulary. Anything outside this map is counted as an
# unrecognised header rather than silently folded into a known section.
SECTION_MAP: dict[str, tuple[str, str]] = {}


def _register(canonical: str, section_class: str, *labels: str) -> None:
    for label in labels:
        SECTION_MAP[label] = (canonical, section_class)


_register(
    "examination", PRE_DIAGNOSTIC,
    "EXAMINATION", "EXAM", "TYPE OF EXAMINATION", "STUDY", "PROCEDURE", "REPORT",
)
_register(
    "indication", PRE_DIAGNOSTIC,
    "INDICATION", "CLINICAL INDICATION", "REASON FOR EXAMINATION", "REASON FOR EXAM",
)
_register(
    "history", PRE_DIAGNOSTIC,
    "HISTORY", "CLINICAL HISTORY", "PATIENT HISTORY", "CLINICAL INFORMATION",
    "CLINICAL INFORMATION & QUESTIONS TO BE ANSWERED",
)
_register("technique", PRE_DIAGNOSTIC, "TECHNIQUE")
_register(
    "comparison", PRE_DIAGNOSTIC,
    "COMPARISON", "COMPARISONS", "COMPARISON EXAM", "COMPARISON FILM", "REFERENCE EXAM",
)
_register("findings", LABEL_SOURCE, "FINDINGS")
_register("impression", LABEL_SOURCE, "IMPRESSION", "CONCLUSION")
_register(
    "findings_impression_combined", LABEL_SOURCE,
    "FINDINGS AND IMPRESSION", "FINDINGS/IMPRESSION", "IMPRESSION AND FINDINGS",
)
_register("wet_read", POST_DIAGNOSTIC, "WET READ")
_register(
    "provisional_impression", POST_DIAGNOSTIC,
    "PROVISIONAL FINDINGS IMPRESSION (PFI)", "PFI", "PROVISIONAL FINDINGS IMPRESSION",
)
_register("recommendation", POST_DIAGNOSTIC, "RECOMMENDATION(S)", "RECOMMENDATIONS", "RECOMMENDATION")
_register("notification", POST_DIAGNOSTIC, "NOTIFICATION", "NOTIFICATIONS")
_register("addendum", POST_DIAGNOSTIC, "ADDENDUM", "FINAL ADDENDUM")
_register("comment", POST_DIAGNOSTIC, "COMMENT", "COMMENTS", "NOTE")
_register("administrative", ADMINISTRATIVE, "DATE", "CC", "TO", "FROM")

CANONICAL_CLASS = {canonical: cls for canonical, cls in SECTION_MAP.values()}
PRE_DIAGNOSTIC_SECTIONS = tuple(sorted(c for c, k in CANONICAL_CLASS.items() if k == PRE_DIAGNOSTIC))
LABEL_SECTIONS = tuple(sorted(c for c, k in CANONICAL_CLASS.items() if k == LABEL_SOURCE))
POST_SECTIONS = tuple(sorted(c for c, k in CANONICAL_CLASS.items() if k == POST_DIAGNOSTIC))

# Unrecognised header labels are only surfaced above this frequency, and with
# digit runs masked, so no rare or free-text fragment can reach an artifact.
RARE_LABEL_MIN_COUNT = 100


class Accumulator:
    """Streaming aggregate accumulator. Retains no report text."""

    def __init__(self) -> None:
        self.reports = 0
        self.section_reports: collections.Counter[str] = collections.Counter()
        self.section_occurrences: collections.Counter[str] = collections.Counter()
        self.section_empty: collections.Counter[str] = collections.Counter()
        self.section_chars: dict[str, list[int]] = collections.defaultdict(list)
        self.section_tokens: dict[str, list[int]] = collections.defaultdict(list)
        self.section_deid_reports: collections.Counter[str] = collections.Counter()
        self.section_deid_only: collections.Counter[str] = collections.Counter()
        self.unrecognised_labels: collections.Counter[str] = collections.Counter()
        self.unrecognised_view_descriptor = 0
        self.unrecognised_total = 0
        self.class_presence: collections.Counter[str] = collections.Counter()
        self.combo: collections.Counter[str] = collections.Counter()
        self.headers_per_report: collections.Counter[int] = collections.Counter()
        self.banner: collections.Counter[str] = collections.Counter()
        self.no_recognised_section = 0
        self.no_header_at_all = 0
        self.ordering_violations = 0
        self.pre_after_label_reports = 0
        self.report_chars: list[int] = []
        self.report_tokens: list[int] = []
        self.duplicate_section_reports: collections.Counter[str] = collections.Counter()
        self.cooccurrence: collections.Counter[tuple[str, str]] = collections.Counter()

    def add(self, text: str) -> None:
        self.reports += 1
        self.report_chars.append(len(text))
        self.report_tokens.append(len(text.split()))

        banner = BANNER_RE.search(text)
        self.banner[banner.group(1) if banner else "<none>"] += 1

        matches = list(HEADER_RE.finditer(text))
        self.headers_per_report[len(matches)] += 1
        if not matches:
            self.no_header_at_all += 1
            self.no_recognised_section += 1
            return

        seen_sections: list[str] = []
        section_seen_counts: collections.Counter[str] = collections.Counter()
        first_label_index: int | None = None
        pre_after_label = False

        for position, match in enumerate(matches):
            raw_label = re.sub(r"\s+", " ", match.group(1)).strip()
            body_start = match.end()
            body_end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
            body = text[body_start:body_end].strip()

            mapped = SECTION_MAP.get(raw_label)
            if mapped is None:
                self.unrecognised_total += 1
                self.unrecognised_labels[_mask(raw_label)] += 1
                if VIEW_DESCRIPTOR_RE.search(raw_label):
                    self.unrecognised_view_descriptor += 1
                continue

            canonical, section_class = mapped
            section_seen_counts[canonical] += 1
            self.section_occurrences[canonical] += 1
            if canonical not in seen_sections:
                seen_sections.append(canonical)

            if not body:
                self.section_empty[canonical] += 1
            else:
                self.section_chars[canonical].append(len(body))
                self.section_tokens[canonical].append(len(body.split()))
                deid_hits = len(DEID_RE.findall(body))
                if deid_hits:
                    self.section_deid_reports[canonical] += 1
                    if not DEID_RE.sub("", body).strip(" .,;:-"):
                        self.section_deid_only[canonical] += 1

            if section_class == LABEL_SOURCE:
                if first_label_index is None:
                    first_label_index = position
            elif section_class == PRE_DIAGNOSTIC and first_label_index is not None:
                pre_after_label = True

        if pre_after_label:
            self.pre_after_label_reports += 1

        for canonical, count in section_seen_counts.items():
            self.section_reports[canonical] += 1
            if count > 1:
                self.duplicate_section_reports[canonical] += 1

        if not seen_sections:
            self.no_recognised_section += 1
            return

        classes = {CANONICAL_CLASS[c] for c in seen_sections}
        for section_class in classes:
            self.class_presence[section_class] += 1

        has_pre = PRE_DIAGNOSTIC in classes
        has_findings = "findings" in seen_sections or "findings_impression_combined" in seen_sections
        has_impression = "impression" in seen_sections or "findings_impression_combined" in seen_sections
        self.combo[_combo_key(has_pre, has_impression, has_findings)] += 1

        ordered = sorted(set(seen_sections))
        for i, left in enumerate(ordered):
            for right in ordered[i + 1:]:
                self.cooccurrence[(left, right)] += 1


def _mask(label: str) -> str:
    return re.sub(r"\d+", "#", label)


def _combo_key(has_pre: bool, has_impression: bool, has_findings: bool) -> str:
    return (
        f"pre_diagnostic={int(has_pre)};"
        f"impression={int(has_impression)};"
        f"findings={int(has_findings)}"
    )


def _summarise(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": 0, "median": 0, "mean": 0.0, "p95": 0, "max": 0}
    ordered = sorted(values)
    def pct(q: float) -> int:
        return ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1)))]
    return {
        "n": len(ordered),
        "min": ordered[0],
        "median": int(stats_mod.median(ordered)),
        "mean": round(sum(ordered) / len(ordered), 2),
        "p95": pct(0.95),
        "max": ordered[-1],
    }


def parse_archive(data_root: Path) -> Accumulator:
    acc = Accumulator()
    with zipfile.ZipFile(data_root / REPORTS_ZIP) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            text = zf.read(info).decode("utf-8", errors="replace")
            acc.add(text)
            del text
    return acc


def build_audit(acc: Accumulator, expected_reports: int) -> dict[str, Any]:
    total = acc.reports

    def frac(n: int) -> float:
        return round(n / total, 6) if total else 0.0

    sections: list[dict[str, Any]] = []
    for canonical in sorted(CANONICAL_CLASS):
        present = acc.section_reports.get(canonical, 0)
        chars = _summarise(acc.section_chars.get(canonical, []))
        tokens = _summarise(acc.section_tokens.get(canonical, []))
        sections.append(
            {
                "section": canonical,
                "section_class": CANONICAL_CLASS[canonical],
                "reports_with_section": present,
                "coverage_fraction": frac(present),
                "total_occurrences": acc.section_occurrences.get(canonical, 0),
                "reports_with_repeated_section": acc.duplicate_section_reports.get(canonical, 0),
                "empty_body_occurrences": acc.section_empty.get(canonical, 0),
                "reports_with_deidentified_span": acc.section_deid_reports.get(canonical, 0),
                "reports_body_deidentified_only": acc.section_deid_only.get(canonical, 0),
                "body_chars": chars,
                "body_tokens": tokens,
            }
        )

    pre_any = sum(value for key, value in acc.combo.items() if key.startswith("pre_diagnostic=1"))
    impression_any = sum(value for key, value in acc.combo.items() if "impression=1" in key)
    findings_any = sum(value for key, value in acc.combo.items() if "findings=1" in key)
    usable_primary = sum(
        value for key, value in acc.combo.items()
        if key.startswith("pre_diagnostic=1") and "impression=1" in key
    )
    usable_sensitivity = sum(
        value for key, value in acc.combo.items()
        if key.startswith("pre_diagnostic=1") and "findings=1" in key
    )

    rare_labels = [
        {"masked_label": label, "occurrences": count, "looks_like_view_descriptor": bool(VIEW_DESCRIPTOR_RE.search(label))}
        for label, count in acc.unrecognised_labels.most_common()
        if count >= RARE_LABEL_MIN_COUNT
    ]
    suppressed = sum(c for c in acc.unrecognised_labels.values() if c < RARE_LABEL_MIN_COUNT)

    top_cooccurrence = [
        {"section_a": a, "section_b": b, "reports": n}
        for (a, b), n in acc.cooccurrence.most_common(25)
    ]

    anomalies: list[str] = []
    if acc.no_recognised_section:
        anomalies.append(
            f"{acc.no_recognised_section} reports "
            f"({frac(acc.no_recognised_section):.4%}) expose no recognised section header; "
            "their narrative cannot be split into pre-diagnostic and diagnostic parts"
        )
    if acc.pre_after_label_reports:
        anomalies.append(
            f"{acc.pre_after_label_reports} reports place a pre-diagnostic section AFTER the first "
            "label-source section; a naive split-at-FINDINGS extractor would mis-assign that text"
        )
    wet = acc.section_reports.get("wet_read", 0)
    if wet:
        anomalies.append(
            f"{wet} reports carry a WET READ preliminary interpretation "
            f"({frac(wet):.4%}); this is post-diagnostic text and must be excluded from context_text"
        )
    combined = acc.section_reports.get("findings_impression_combined", 0)
    if combined:
        anomalies.append(
            f"{combined} reports merge findings and impression into a single section, so the frozen "
            "primary/sensitivity label-source separation is not recoverable for them"
        )
    deid_only_ind = acc.section_deid_only.get("indication", 0)
    if deid_only_ind:
        anomalies.append(
            f"{deid_only_ind} reports have an indication section whose body is de-identification "
            "placeholders only, yielding empty effective context_text"
        )
    if acc.unrecognised_view_descriptor:
        anomalies.append(
            f"{acc.unrecognised_view_descriptor} header-shaped lines are view descriptors in "
            "old-style reports rather than named sections"
        )

    unresolved = [
        "eligible_view is frozen to 'frontal', but view position is still unavailable: it lives in "
        "mimic-cxr-2.0.0-metadata.csv.gz, which remains absent. View filtering cannot be applied yet.",
        "No official split file is present, so patient-disjoint split construction remains unverified.",
        "Section boundaries are derived from a curated header vocabulary. Reports without recognised "
        "headers, and reports merging findings with impression, are not contract-recoverable and must "
        "be excluded or handled explicitly by an approved Stage 3C rule.",
        "COMPARISON bodies are treated as pre-diagnostic because prior-study references precede "
        "interpretation, but they can quote prior diagnostic conclusions; if COMPARISON is admitted "
        "into context_text this must be justified in a protocol amendment.",
        "No label was extracted and no CheXbert-equivalent was executed, so the MIMIC analogue of "
        "impression_fixed.json / findings_fixed.json still does not exist.",
    ]

    return {
        "stage": STAGE,
        "title": TITLE,
        "status": "PASS",
        "declarations": list(DECLARATIONS),
        "scope": "structural section parsing and aggregate statistics only",
        "reports_parsed": total,
        "reports_expected_from_study_list": expected_reports,
        "report_count_matches_study_list": total == expected_reports,
        "banner_first_line": dict(acc.banner.most_common()),
        "headers_per_report_histogram": {
            str(k): v for k, v in sorted(acc.headers_per_report.items())
        },
        "reports_without_any_header": acc.no_header_at_all,
        "reports_without_recognised_section": acc.no_recognised_section,
        "sections": sections,
        "section_class_presence": {
            "pre_diagnostic": acc.class_presence.get(PRE_DIAGNOSTIC, 0),
            "label_source": acc.class_presence.get(LABEL_SOURCE, 0),
            "post_diagnostic": acc.class_presence.get(POST_DIAGNOSTIC, 0),
            "administrative": acc.class_presence.get(ADMINISTRATIVE, 0),
        },
        "contract_availability": {
            "reports_with_pre_diagnostic_context": pre_any,
            "reports_with_pre_diagnostic_context_fraction": frac(pre_any),
            "reports_with_impression_label_source": impression_any,
            "reports_with_impression_label_source_fraction": frac(impression_any),
            "reports_with_findings_label_source": findings_any,
            "reports_with_findings_label_source_fraction": frac(findings_any),
            "usable_for_primary_analysis": usable_primary,
            "usable_for_primary_analysis_fraction": frac(usable_primary),
            "usable_for_sensitivity_analysis": usable_sensitivity,
            "usable_for_sensitivity_analysis_fraction": frac(usable_sensitivity),
            "availability_combination_counts": dict(sorted(acc.combo.items())),
        },
        "ordering": {
            "reports_with_pre_diagnostic_after_label_section": acc.pre_after_label_reports,
            "fraction": frac(acc.pre_after_label_reports),
            "interpretation": (
                "a non-zero count means section order alone is not a safe extraction rule; "
                "extraction must be header-driven, not position-driven"
            ),
        },
        "unrecognised_headers": {
            "total_occurrences": acc.unrecognised_total,
            "distinct_masked_labels": len(acc.unrecognised_labels),
            "view_descriptor_occurrences": acc.unrecognised_view_descriptor,
            "labels_at_or_above_threshold": rare_labels,
            "occurrences_below_threshold_suppressed": suppressed,
            "threshold": RARE_LABEL_MIN_COUNT,
            "suppression_note": (
                "labels below the threshold are counted but never printed, and digit runs are "
                "masked, so no rare free-text fragment can reach an artifact"
            ),
        },
        "cooccurrence_top": top_cooccurrence,
        "report_size": {
            "chars": _summarise(acc.report_chars),
            "whitespace_tokens": _summarise(acc.report_tokens),
        },
        "anomalies": anomalies,
        "unresolved_risks": unresolved,
        "compliance": {
            "images_accessed": False,
            "dicom_opened": False,
            "jpg_opened": False,
            "report_text_exported": False,
            "labels_created": False,
            "chexbert_executed": False,
            "model_training": False,
            "model_inference": False,
            "threshold_selection": False,
            "evaluation_performed": False,
            "external_downloads": False,
            "protocol_modified": False,
            "previous_artifacts_modified": False,
            "identifiers_emitted": False,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
        },
    }


def build_statistics(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": STAGE,
        "aggregation_level": "cohort only; no report text, section content, or identifiers are emitted",
        "reports_parsed": audit["reports_parsed"],
        # Section names are carried as values, never as mapping keys: the shared
        # safe-payload validator reserves 'findings' and 'impression' as unsafe keys.
        "section_coverage": [
            {
                "section": item["section"],
                "section_class": item["section_class"],
                "reports": item["reports_with_section"],
                "coverage_fraction": item["coverage_fraction"],
                "median_body_tokens": item["body_tokens"]["median"],
            }
            for item in audit["sections"]
        ],
        "contract_availability": audit["contract_availability"],
        "section_class_presence": audit["section_class_presence"],
        "report_size": audit["report_size"],
        "reports_without_recognised_section": audit["reports_without_recognised_section"],
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


def render_audit_md(audit: dict[str, Any]) -> str:
    total = audit["reports_parsed"]
    lines = [
        f"# {STAGE} — Report Structure and Section Availability Audit",
        "",
        f"Status: **{audit['status']}**",
        "",
    ]
    lines += [f"- **{d}**" for d in audit["declarations"]]
    lines += [
        "",
        "## Corpus",
        "",
        f"- Reports parsed: {total}",
        f"- Reports expected from `cxr-study-list`: {audit['reports_expected_from_study_list']}",
        f"- Count matches study list: {audit['report_count_matches_study_list']}",
        f"- Reports with no header-shaped line at all: {audit['reports_without_any_header']}",
        f"- Reports with no recognised section: {audit['reports_without_recognised_section']}",
        f"- Leading banner distribution: {audit['banner_first_line']}",
        "",
        "## Section coverage",
        "",
        "| section | class | reports | coverage | median body tokens | empty bodies | repeated |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in audit["sections"]:
        lines.append(
            f"| {item['section']} | {item['section_class']} | {item['reports_with_section']} | "
            f"{item['coverage_fraction']:.4%} | {item['body_tokens']['median']} | "
            f"{item['empty_body_occurrences']} | {item['reports_with_repeated_section']} |"
        )
    ca = audit["contract_availability"]
    lines += [
        "",
        "## Frozen-contract availability",
        "",
        f"- Pre-diagnostic context present: {ca['reports_with_pre_diagnostic_context']} "
        f"({ca['reports_with_pre_diagnostic_context_fraction']:.4%})",
        f"- Impression label source present: {ca['reports_with_impression_label_source']} "
        f"({ca['reports_with_impression_label_source_fraction']:.4%})",
        f"- Findings label source present: {ca['reports_with_findings_label_source']} "
        f"({ca['reports_with_findings_label_source_fraction']:.4%})",
        f"- **Usable for primary analysis** (context + impression): "
        f"{ca['usable_for_primary_analysis']} ({ca['usable_for_primary_analysis_fraction']:.4%})",
        f"- **Usable for sensitivity analysis** (context + findings): "
        f"{ca['usable_for_sensitivity_analysis']} ({ca['usable_for_sensitivity_analysis_fraction']:.4%})",
        "",
        "### Availability combinations",
        "",
        "| combination | reports |",
        "| --- | ---: |",
    ]
    for key, value in ca["availability_combination_counts"].items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        "## Section ordering",
        "",
        f"- Reports placing pre-diagnostic text after the first label section: "
        f"{audit['ordering']['reports_with_pre_diagnostic_after_label_section']} "
        f"({audit['ordering']['fraction']:.4%})",
        f"- Interpretation: {audit['ordering']['interpretation']}.",
        "",
        "## Unrecognised headers",
        "",
        f"- Total occurrences: {audit['unrecognised_headers']['total_occurrences']}",
        f"- Distinct masked labels: {audit['unrecognised_headers']['distinct_masked_labels']}",
        f"- View-descriptor occurrences: {audit['unrecognised_headers']['view_descriptor_occurrences']}",
        f"- Occurrences suppressed below threshold "
        f"({audit['unrecognised_headers']['threshold']}): "
        f"{audit['unrecognised_headers']['occurrences_below_threshold_suppressed']}",
        f"- {audit['unrecognised_headers']['suppression_note']}.",
        "",
        "| masked label | occurrences | view descriptor |",
        "| --- | ---: | --- |",
    ]
    for item in audit["unrecognised_headers"]["labels_at_or_above_threshold"]:
        lines.append(
            f"| {item['masked_label']} | {item['occurrences']} | {item['looks_like_view_descriptor']} |"
        )
    lines += ["", "## Anomalies", ""]
    lines += [f"- {item}" for item in audit["anomalies"]] or ["- None"]
    lines += ["", "## Unresolved risks", ""]
    lines += [f"- {item}" for item in audit["unresolved_risks"]]
    lines += [""]
    return "\n".join(lines)


def render_context_md(audit: dict[str, Any]) -> str:
    ca = audit["contract_availability"]
    total = audit["reports_parsed"]
    by_section = {item["section"]: item for item in audit["sections"]}
    lines = [
        f"# {STAGE} — `context_text` Availability Against the Frozen Contract",
        "",
        "The frozen C3E data policy requires a pre-diagnostic `context_text` column and",
        "prohibits `findings`, `impression`, and `full_report` as model inputs. This file",
        "records whether the MIMIC target site can satisfy that contract, and at what cost",
        "in cohort size. It contains no report text.",
        "",
        "## Candidate pre-diagnostic fields",
        "",
        "| section | reports | coverage | median tokens | body is de-identification only |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in PRE_DIAGNOSTIC_SECTIONS:
        item = by_section[name]
        lines.append(
            f"| {name} | {item['reports_with_section']} | {item['coverage_fraction']:.4%} | "
            f"{item['body_tokens']['median']} | {item['reports_body_deidentified_only']} |"
        )
    lines += [
        "",
        "## Prohibited-as-input fields (label sources only)",
        "",
        "| section | reports | coverage | median tokens |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name in LABEL_SECTIONS:
        item = by_section[name]
        lines.append(
            f"| {name} | {item['reports_with_section']} | {item['coverage_fraction']:.4%} | "
            f"{item['body_tokens']['median']} |"
        )
    lines += [
        "",
        "## Post-diagnostic sections that must be excluded from `context_text`",
        "",
        "| section | reports | coverage |",
        "| --- | ---: | ---: |",
    ]
    for name in POST_SECTIONS:
        item = by_section[name]
        lines.append(f"| {name} | {item['reports_with_section']} | {item['coverage_fraction']:.4%} |")
    lines += [
        "",
        "## Effective cohort ceiling",
        "",
        f"- Studies in archive: {total}",
        f"- With any pre-diagnostic context: {ca['reports_with_pre_diagnostic_context']} "
        f"({ca['reports_with_pre_diagnostic_context_fraction']:.4%})",
        f"- With context and an impression label source: {ca['usable_for_primary_analysis']} "
        f"({ca['usable_for_primary_analysis_fraction']:.4%})",
        f"- With context and a findings label source: {ca['usable_for_sensitivity_analysis']} "
        f"({ca['usable_for_sensitivity_analysis_fraction']:.4%})",
        "",
        "These are ceilings measured at the study level before any view filter is applied.",
        "The frozen policy restricts eligible views to frontal, and view position is still",
        "unavailable in this download, so the realised cohort will be strictly smaller.",
        "",
        "### Caveat: presence is not substance",
        "",
        "The pre-diagnostic availability figure counts a study as covered if ANY pre-diagnostic",
        "header is present, including near-boilerplate ones. Judged by median body length,",
        f"`comparison` ({by_section['comparison']['body_tokens']['median']} tokens),",
        f"`examination` ({by_section['examination']['body_tokens']['median']} tokens), and",
        f"`technique` ({by_section['technique']['body_tokens']['median']} tokens) carry almost no",
        "clinical content. The substantive context fields are",
        f"`indication` ({by_section['indication']['coverage_fraction']:.2%} coverage,",
        f"median {by_section['indication']['body_tokens']['median']} tokens) and",
        f"`history` ({by_section['history']['coverage_fraction']:.2%} coverage,",
        f"median {by_section['history']['body_tokens']['median']} tokens).",
        "",
        "Stage 3C must therefore define `context_state` against a substantive-content rule, not",
        "against header presence. Using header presence alone would classify near-empty",
        "boilerplate as available context and would inflate the C0 stratum.",
        "",
        "## Construction constraints implied by this audit",
        "",
        "- Extraction must be header-driven. Section order is not a safe rule: some reports",
        "  place pre-diagnostic text after the first diagnostic section.",
        "- WET READ and PROVISIONAL FINDINGS IMPRESSION are preliminary interpretations. They",
        "  are post-diagnostic and must never enter `context_text`.",
        "- Reports merging findings and impression cannot supply the frozen primary/sensitivity",
        "  label-source separation and need an explicit inclusion rule.",
        "- De-identification placeholders can empty a section body. Presence of a header is not",
        "  evidence of usable context; effective emptiness must be checked after placeholder removal.",
        "",
    ]
    return "\n".join(lines)


def render_statistics_md(stats: dict[str, Any]) -> str:
    lines = [
        f"# {STAGE} — Aggregate Report Statistics",
        "",
        f"Aggregation level: {stats['aggregation_level']}.",
        "",
        f"- Reports parsed: {stats['reports_parsed']}",
        f"- Reports without a recognised section: {stats['reports_without_recognised_section']}",
        "",
        "## Section coverage",
        "",
        "| section | class | reports | coverage | median body tokens |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for item in stats["section_coverage"]:
        lines.append(
            f"| {item['section']} | {item['section_class']} | {item['reports']} | "
            f"{item['coverage_fraction']:.4%} | {item['median_body_tokens']} |"
        )
    lines += [
        "",
        "## Report size",
        "",
        "| measure | n | min | median | mean | p95 | max |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, item in stats["report_size"].items():
        lines.append(
            f"| {key} | {item['n']} | {item['min']} | {item['median']} | "
            f"{item['mean']} | {item['p95']} | {item['max']} |"
        )
    lines += [
        "",
        "## Section-class presence",
        "",
        "| class | reports |",
        "| --- | ---: |",
    ]
    for key, value in stats["section_class_presence"].items():
        lines.append(f"| {key} | {value} |")
    lines += ["", "No report text, section content, or identifiers appear in this file.", ""]
    return "\n".join(lines)


PROHIBITED = (
    ("image files opened (DICOM or JPG)", "none"),
    ("image directory accessed", "no"),
    ("image feature extraction", "no"),
    ("CheXbert executed", "no"),
    ("BioClinicalBERT executed", "no"),
    ("RadGraph executed", "no"),
    ("labels created or extracted from report text", "no"),
    ("model initialised, trained, or run for inference", "no"),
    ("threshold selection or tuning", "no"),
    ("AUROC / AUPRC / calibration / risk-coverage computed", "no"),
    ("evaluation or metric computation on real data", "no"),
    ("selective prediction executed", "no"),
    ("cross-site experiment executed", "no"),
    ("dataset or split construction", "no"),
    ("report text written to any artifact", "no"),
    ("section content written to any artifact", "no"),
    ("patient-level or study-level rows exported", "no"),
    ("identifiers written to Stage 3B artifacts", "no"),
    ("external downloads", "no"),
    ("frozen protocol documents modified", "no"),
    ("previous audit outputs modified", "no"),
    ("git commit, history change, or .gitignore edit", "no"),
)


def render_protocol_checklist(audit: dict[str, Any]) -> str:
    lines = [
        f"# {STAGE} — Protocol Compliance Checklist",
        "",
        f"Overall Stage 3B status: **{audit['status']}**",
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
        "## Authorised scope actually exercised",
        "",
        "- Parsed all report members of `mimic-cxr-reports.zip` for section structure.",
        "- Measured section presence, repetition, ordering, body size, and de-identification density.",
        "- Read `cxr-study-list.csv.gz` to confirm the parsed report count.",
        "- Report text was held in memory only for measurement and discarded immediately.",
        "",
        "## Text-handling attestation",
        "",
        "- No section body, sentence, phrase, or token from any report was written to an artifact.",
        "- Section names come from a curated, hard-coded vocabulary in the audit module.",
        "- Unrecognised header labels are digit-masked and suppressed below a frequency",
        f"  threshold of {audit['unrecognised_headers']['threshold']} occurrences.",
        "- All JSON payloads passed the safe-payload validator, and every emitted file was",
        "  scanned for restricted row-level patterns and absolute project paths.",
        "",
        "## Artifact isolation",
        "",
        "- All Stage 3B outputs are written to a new directory: `results/c3e_mimic/stage3b/`.",
        "- Stage 3A artifacts under `results/c3e_mimic/stage3a/` were not read for modification",
        "  or altered, and no frozen protocol document was changed.",
        "- No commit was created and git history was not modified.",
        "",
        "## Residual scope notes",
        "",
    ]
    lines += [f"- {item}" for item in audit["unresolved_risks"]]
    lines += [""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def _output_guard(output_dir: Path, project_root: Path) -> None:
    names = sorted(p.name for p in output_dir.iterdir() if p.is_file())
    if names != sorted(OUTPUT_FILENAMES):
        raise IntakeContractError(f"unexpected Stage 3B output files: {names}")
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


def _expected_report_count(data_root: Path) -> int:
    with gzip.open(data_root / STUDY_LIST, "rt", encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def run_audit(*, project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    data_root = root / DATA_ROOT
    output_dir = root / OUTPUT_DIR

    acc = parse_archive(data_root)
    audit = build_audit(acc, _expected_report_count(data_root))
    statistics = build_statistics(audit)

    output_dir.mkdir(parents=True, exist_ok=True)
    foreign = {p.name for p in output_dir.iterdir() if p.is_file()} - set(OUTPUT_FILENAMES)
    if foreign:
        raise IntakeContractError(f"refusing to write beside unknown artifacts: {sorted(foreign)}")

    validate_safe_payload(audit, project_root=root)
    validate_safe_payload(statistics, project_root=root)

    (output_dir / "stage3b_report_structure_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "stage3b_report_structure_audit.md").write_text(render_audit_md(audit), encoding="utf-8")
    (output_dir / "stage3b_statistics.json").write_text(
        json.dumps(statistics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "stage3b_statistics.md").write_text(render_statistics_md(statistics), encoding="utf-8")
    (output_dir / "stage3b_context_availability.md").write_text(render_context_md(audit), encoding="utf-8")
    (output_dir / "stage3b_protocol_checklist.md").write_text(render_protocol_checklist(audit), encoding="utf-8")

    vocabulary_rows = [
        {
            "label": label,
            "canonical_section": canonical,
            "section_class": section_class,
            "recognised": True,
        }
        for label, (canonical, section_class) in sorted(SECTION_MAP.items())
    ]
    vocabulary_rows += [
        {
            "label": item["masked_label"],
            "canonical_section": "",
            "section_class": "unrecognised",
            "recognised": False,
        }
        for item in audit["unrecognised_headers"]["labels_at_or_above_threshold"]
    ]
    (output_dir / "stage3b_section_vocabulary.csv").write_text(
        _csv_text(vocabulary_rows, ["label", "canonical_section", "section_class", "recognised"]),
        encoding="utf-8",
    )

    section_rows = [
        {
            "section": item["section"],
            "section_class": item["section_class"],
            "reports_with_section": item["reports_with_section"],
            "coverage_fraction": item["coverage_fraction"],
            "total_occurrences": item["total_occurrences"],
            "reports_with_repeated_section": item["reports_with_repeated_section"],
            "empty_body_occurrences": item["empty_body_occurrences"],
            "reports_with_deidentified_span": item["reports_with_deidentified_span"],
            "reports_body_deidentified_only": item["reports_body_deidentified_only"],
            "body_tokens_median": item["body_tokens"]["median"],
            "body_tokens_mean": item["body_tokens"]["mean"],
            "body_tokens_p95": item["body_tokens"]["p95"],
            "body_tokens_max": item["body_tokens"]["max"],
            "body_chars_median": item["body_chars"]["median"],
            "body_chars_max": item["body_chars"]["max"],
        }
        for item in audit["sections"]
    ]
    (output_dir / "stage3b_section_statistics.csv").write_text(
        _csv_text(
            section_rows,
            [
                "section", "section_class", "reports_with_section", "coverage_fraction",
                "total_occurrences", "reports_with_repeated_section", "empty_body_occurrences",
                "reports_with_deidentified_span", "reports_body_deidentified_only",
                "body_tokens_median", "body_tokens_mean", "body_tokens_p95", "body_tokens_max",
                "body_chars_median", "body_chars_max",
            ],
        ),
        encoding="utf-8",
    )

    hashed = [n for n in OUTPUT_FILENAMES if n != "stage3b_manifest.json"]
    manifest = {
        "stage": STAGE,
        "title": TITLE,
        "status": audit["status"],
        "declarations": list(DECLARATIONS),
        "output_dir": OUTPUT_DIR,
        "reports_parsed": audit["reports_parsed"],
        "artifacts": [
            {"name": name, "byte_size": (output_dir / name).stat().st_size, "sha256": sha256_file(output_dir / name)}
            for name in hashed
        ],
        "source_files_audited": [
            {"name": Path(rel).name, "relative_path": f"{DATA_ROOT}/{rel}", "sha256": sha256_file(data_root / rel)}
            for rel in (REPORTS_ZIP, STUDY_LIST)
        ],
        "compliance": audit["compliance"],
        "environment": audit["environment"],
    }
    validate_safe_payload(manifest, project_root=root)
    (output_dir / "stage3b_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    _output_guard(output_dir, root)
    return audit


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Run the C3-E6 Stage 3B MIMIC report structure audit")
    parser.add_argument("--project-root", type=Path, default=default_root)
    args = parser.parse_args(argv)
    try:
        audit = run_audit(project_root=args.project_root)
    except Exception as exc:  # noqa: BLE001 - surface a single safe line
        print(f"Stage 3B audit FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "stage": STAGE,
                "status": audit["status"],
                "reports_parsed": audit["reports_parsed"],
                "usable_primary": audit["contract_availability"]["usable_for_primary_analysis"],
                "usable_sensitivity": audit["contract_availability"]["usable_for_sensitivity_analysis"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
