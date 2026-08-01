"""C3-E6 Stage 3B-2: context substantiveness threshold sweep.

Stage 3B established that pre-diagnostic header presence overstates context
availability. The frozen context registry (C3E6-CONTEXT-001) defines three
natural states -- N1 informative, N2 low_information, N3 absent -- and admits
only N1 studies into the confirmatory C0/C1/C2 interventions. The N1/N2
boundary therefore fixes the confirmatory sample size.

This module quantifies that boundary. For each candidate permitted-context
set it measures effective token counts after de-identification placeholders
are removed, sweeps a substantiveness threshold, and reports the resulting
N1/N2/N3 populations crossed with label-source availability. It also tests
whether the frozen C2 pairing constraints can be satisfied inside each
context-length bin.

No labels, no images, no models, no thresholds for prediction, no evaluation.
Report text is measured and discarded; no content reaches any artifact.
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

from .contracts import IntakeContractError
from .safety import validate_safe_payload
from .stage3b_reports import DEID_RE, HEADER_RE, SECTION_MAP, sha256_file

STAGE = "C3-E6 Stage 3B-2"
TITLE = "CONTEXT SUBSTANTIVENESS THRESHOLD SWEEP"

DECLARATIONS = (
    "STAGE 3B-2 ONLY",
    "CONTEXT AVAILABILITY MEASUREMENT",
    "NO MEDICAL IMAGES OPENED",
    "NO REPORT TEXT EXPORTED",
    "NO LABEL EXTRACTION",
    "NO CHEXBERT EXECUTION",
    "NO MODEL TRAINING OR INFERENCE",
    "NO PREDICTION THRESHOLD SELECTION",
    "NO EVALUATION OR METRIC COMPUTATION",
    "NO EXTERNAL DOWNLOADS",
    "NO PROTOCOL MODIFICATION",
)

OUTPUT_FILENAMES = (
    "stage3b2_context_threshold_sweep.json",
    "stage3b2_context_threshold_sweep.md",
    "stage3b2_threshold_curve.csv",
    "stage3b2_candidate_context_sets.csv",
    "stage3b2_c2_pairing_feasibility.md",
    "stage3b2_manifest.json",
)

DATA_ROOT = "data/mimic"
OUTPUT_DIR = "results/c3e_mimic/stage3b2"
REPORTS_ZIP = "reports/mimic-cxr-reports.zip"
STUDY_LIST = "metadata/cxr-study-list.csv.gz"

# Candidate permitted-context sets. The registry's N3 wording ("Neither
# permitted section contains usable text") implies a two-section set; the
# narrow candidates are evaluated alongside wider ones so the choice is made
# from measured cohort cost rather than assumption.
CANDIDATE_SETS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("indication_only", ("indication",), "single-section baseline"),
    ("history_only", ("history",), "single-section baseline"),
    (
        "indication_history",
        ("indication", "history"),
        "two-section set consistent with the registry's 'neither permitted section' wording",
    ),
    (
        "indication_history_examination",
        ("indication", "history", "examination"),
        "adds examination type",
    ),
    (
        "indication_history_comparison",
        ("indication", "history", "comparison"),
        "adds prior-study reference; comparison may quote prior conclusions",
    ),
    (
        "all_pre_diagnostic",
        ("indication", "history", "examination", "technique", "comparison"),
        "widest pre-diagnostic set; upper bound on availability",
    ),
)

THRESHOLDS = (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30)

# Context-length bins used by the frozen C2 constraint same_context_length_bin.
LENGTH_BINS: tuple[tuple[str, int, int], ...] = (
    ("01-05", 1, 5),
    ("06-10", 6, 10),
    ("11-20", 11, 20),
    ("21-40", 21, 40),
    ("41-80", 41, 80),
    ("81+", 81, 10**9),
)

LABEL_SECTION_NAMES = ("impression", "findings", "findings_impression_combined")


def effective_token_count(body: str) -> int:
    """Tokens remaining after de-identification placeholders are removed.

    Pure-punctuation tokens are dropped, so separators such as '//' do not
    inflate an otherwise empty context.
    """
    cleaned = DEID_RE.sub(" ", body)
    return sum(1 for token in cleaned.split() if any(ch.isalnum() for ch in token))


def bin_for(count: int) -> str:
    for name, low, high in LENGTH_BINS:
        if low <= count <= high:
            return name
    return "00"


def parse_report(text: str) -> tuple[dict[str, int], set[str]]:
    """Return effective token counts per canonical section, and label sections present."""
    counts: dict[str, int] = collections.defaultdict(int)
    labels: set[str] = set()
    matches = list(HEADER_RE.finditer(text))
    for position, match in enumerate(matches):
        raw_label = re.sub(r"\s+", " ", match.group(1)).strip()
        mapped = SECTION_MAP.get(raw_label)
        if mapped is None:
            continue
        canonical, _ = mapped
        body_end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        body = text[match.end():body_end].strip()
        if canonical in LABEL_SECTION_NAMES:
            if effective_token_count(body) > 0:
                labels.add(canonical)
            continue
        counts[canonical] += effective_token_count(body)
    return counts, labels


def _load_patient_by_report(data_root: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with gzip.open(data_root / STUDY_LIST, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            mapping[row["path"]] = row["subject_id"]
    return mapping


class Sweep:
    def __init__(self) -> None:
        self.reports = 0
        # per candidate set: list of effective token counts is too large to keep,
        # so counts are bucketed directly.
        self.token_hist: dict[str, collections.Counter[int]] = {
            name: collections.Counter() for name, _, _ in CANDIDATE_SETS
        }
        self.token_hist_with_impression: dict[str, collections.Counter[int]] = {
            name: collections.Counter() for name, _, _ in CANDIDATE_SETS
        }
        self.token_hist_with_findings: dict[str, collections.Counter[int]] = {
            name: collections.Counter() for name, _, _ in CANDIDATE_SETS
        }
        # C2 feasibility is assessed on the primary candidate set only.
        self.bin_studies: collections.Counter[str] = collections.Counter()
        self.bin_patient_counts: dict[str, collections.Counter[str]] = collections.defaultdict(
            collections.Counter
        )
        self.reports_with_impression = 0
        self.reports_with_findings = 0

    def add(self, counts: dict[str, int], labels: set[str], patient: str) -> None:
        self.reports += 1
        has_impression = "impression" in labels or "findings_impression_combined" in labels
        has_findings = "findings" in labels or "findings_impression_combined" in labels
        self.reports_with_impression += int(has_impression)
        self.reports_with_findings += int(has_findings)

        for name, sections, _ in CANDIDATE_SETS:
            total = sum(counts.get(section, 0) for section in sections)
            self.token_hist[name][total] += 1
            if has_impression:
                self.token_hist_with_impression[name][total] += 1
            if has_findings:
                self.token_hist_with_findings[name][total] += 1

        primary = sum(counts.get(s, 0) for s in ("indication", "history"))
        if primary > 0:
            label = bin_for(primary)
            self.bin_studies[label] += 1
            self.bin_patient_counts[label][patient] += 1


def _cumulative_at_least(hist: collections.Counter[int], threshold: int) -> int:
    return sum(count for value, count in hist.items() if value >= threshold)


def build_report(sweep: Sweep) -> dict[str, Any]:
    total = sweep.reports

    def frac(n: int) -> float:
        return round(n / total, 6) if total else 0.0

    candidate_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    for name, sections, note in CANDIDATE_SETS:
        hist = sweep.token_hist[name]
        absent = hist.get(0, 0)
        present = total - absent
        values = sorted(hist)
        cumulative = 0
        median = 0
        for value in values:
            cumulative += hist[value]
            if cumulative >= total / 2:
                median = value
                break
        candidate_rows.append(
            {
                "candidate_set": name,
                "sections": "|".join(sections),
                "note": note,
                "n3_absent": absent,
                "n3_absent_fraction": frac(absent),
                "context_present": present,
                "context_present_fraction": frac(present),
                "median_effective_tokens": median,
                "max_effective_tokens": max(values) if values else 0,
            }
        )
        for threshold in THRESHOLDS:
            n1 = _cumulative_at_least(hist, threshold)
            n2 = present - n1
            n1_impression = _cumulative_at_least(sweep.token_hist_with_impression[name], threshold)
            n1_findings = _cumulative_at_least(sweep.token_hist_with_findings[name], threshold)
            curve_rows.append(
                {
                    "candidate_set": name,
                    "threshold_effective_tokens": threshold,
                    "n1_informative": n1,
                    "n1_fraction": frac(n1),
                    "n2_low_information": n2,
                    "n2_fraction": frac(n2),
                    "n3_absent": absent,
                    "n3_fraction": frac(absent),
                    "n1_with_impression": n1_impression,
                    "n1_with_impression_fraction": frac(n1_impression),
                    "n1_with_findings": n1_findings,
                    "n1_with_findings_fraction": frac(n1_findings),
                }
            )

    bins = []
    for label, _, _ in LENGTH_BINS:
        studies = sweep.bin_studies.get(label, 0)
        patients = sweep.bin_patient_counts.get(label, collections.Counter())
        distinct = len(patients)
        largest = max(patients.values()) if patients else 0
        bins.append(
            {
                "length_bin": label,
                "studies": studies,
                "distinct_patients": distinct,
                "largest_single_patient_studies": largest,
                "largest_patient_share": round(largest / studies, 6) if studies else 0.0,
                "different_patient_pairing_feasible": distinct >= 2 and largest <= studies - largest,
            }
        )

    infeasible = [b["length_bin"] for b in bins if b["studies"] and not b["different_patient_pairing_feasible"]]
    empty_bins = [b["length_bin"] for b in bins if not b["studies"]]

    findings: list[str] = []
    primary_curve = [r for r in curve_rows if r["candidate_set"] == "indication_history"]
    at_1 = next(r for r in primary_curve if r["threshold_effective_tokens"] == 1)
    at_5 = next(r for r in primary_curve if r["threshold_effective_tokens"] == 5)
    at_10 = next(r for r in primary_curve if r["threshold_effective_tokens"] == 10)
    findings.append(
        f"Under the two-section permitted set, raising the substantiveness threshold from 1 to 5 "
        f"effective tokens moves {at_1['n1_informative'] - at_5['n1_informative']} studies from N1 to N2 "
        f"({at_1['n1_fraction']:.2%} -> {at_5['n1_fraction']:.2%} of the corpus)."
    )
    findings.append(
        f"At a threshold of 10 effective tokens the confirmatory N1 cohort with an impression label "
        f"source is {at_10['n1_with_impression']} studies ({at_10['n1_with_impression_fraction']:.2%})."
    )
    if infeasible:
        findings.append(
            f"C2 different-patient pairing is not satisfiable inside length bins {infeasible} "
            "because a single patient holds at least half the bin."
        )
    else:
        findings.append(
            "Every populated context-length bin admits C2 different-patient pairing at corpus level: "
            "each has at least two distinct patients and no patient holds half the bin."
        )

    unresolved = [
        "C2 pairing must hold within institution AND split. No official split file is present, so "
        "bin feasibility is verified at corpus level only and may fail inside individual splits.",
        "The N1/N2 threshold is not set by this audit. It is a protocol decision; this sweep supplies "
        "the cohort cost of each candidate value.",
        "Effective token count is a proxy for the registry's 'boilerplate, vague, or clinically "
        "insufficient' wording. It detects emptiness and brevity, not vagueness.",
        "eligible_view is frozen to frontal and view position remains unavailable, so every cohort "
        "figure here is an upper bound.",
        "Admitting comparison into the permitted set raises availability but risks importing prior "
        "diagnostic conclusions; the measured gain is reported so the tradeoff can be priced.",
    ]

    return {
        "stage": STAGE,
        "title": TITLE,
        "status": "PASS",
        "declarations": list(DECLARATIONS),
        "reports_parsed": total,
        "reports_with_impression_label_source": sweep.reports_with_impression,
        "reports_with_findings_label_source": sweep.reports_with_findings,
        "registry_reference": "C3E6-CONTEXT-001 natural_context_states N1/N2/N3",
        "threshold_definition": (
            "effective tokens = whitespace tokens containing at least one alphanumeric character, "
            "counted after de-identification placeholder runs are removed"
        ),
        "state_rule": {
            "n3_absent": "effective tokens == 0 across the permitted set",
            "n2_low_information": "0 < effective tokens < threshold",
            "n1_informative": "effective tokens >= threshold",
        },
        "candidate_sets": candidate_rows,
        "threshold_curve": curve_rows,
        "c2_pairing": {
            "assessed_on": "indication_history",
            "bins": bins,
            "infeasible_bins": infeasible,
            "empty_bins": empty_bins,
            "constraint_reference": "same_institution, same_split, different_patient, same_context_length_bin",
        },
        "key_findings": findings,
        "unresolved_risks": unresolved,
        "compliance": {
            "images_accessed": False,
            "report_text_exported": False,
            "labels_created": False,
            "chexbert_executed": False,
            "model_training": False,
            "model_inference": False,
            "prediction_threshold_selected": False,
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


def _csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return stream.getvalue()


def render_md(report: dict[str, Any]) -> str:
    lines = [
        f"# {STAGE} — Context Substantiveness Threshold Sweep",
        "",
        f"Status: **{report['status']}**",
        "",
    ]
    lines += [f"- **{d}**" for d in report["declarations"]]
    lines += [
        "",
        "## Purpose",
        "",
        f"The frozen context registry ({report['registry_reference']}) admits only N1 studies into",
        "the confirmatory C0/C1/C2 interventions. The N1/N2 boundary therefore fixes the",
        "confirmatory sample size. This sweep prices each candidate boundary.",
        "",
        f"- Reports parsed: {report['reports_parsed']}",
        f"- Threshold definition: {report['threshold_definition']}.",
        "",
        "## State rule",
        "",
        f"- N3 absent: {report['state_rule']['n3_absent']}",
        f"- N2 low information: {report['state_rule']['n2_low_information']}",
        f"- N1 informative: {report['state_rule']['n1_informative']}",
        "",
        "## Candidate permitted-context sets",
        "",
        "| candidate set | sections | N3 absent | context present | median tokens | note |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report["candidate_sets"]:
        lines.append(
            f"| {row['candidate_set']} | {row['sections']} | {row['n3_absent']} "
            f"({row['n3_absent_fraction']:.2%}) | {row['context_present']} "
            f"({row['context_present_fraction']:.2%}) | {row['median_effective_tokens']} | {row['note']} |"
        )
    lines += [
        "",
        "## Threshold curve",
        "",
        "N1 is the confirmatory cohort. `N1 + impression` is the cohort that also carries a",
        "primary label source.",
        "",
        "| candidate set | threshold | N1 | N1 % | N2 | N3 | N1 + impression | N1 + findings |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["threshold_curve"]:
        lines.append(
            f"| {row['candidate_set']} | {row['threshold_effective_tokens']} | {row['n1_informative']} | "
            f"{row['n1_fraction']:.2%} | {row['n2_low_information']} | {row['n3_absent']} | "
            f"{row['n1_with_impression']} | {row['n1_with_findings']} |"
        )
    lines += ["", "## Key findings", ""]
    lines += [f"- {item}" for item in report["key_findings"]]
    lines += ["", "## Unresolved risks", ""]
    lines += [f"- {item}" for item in report["unresolved_risks"]]
    lines += [""]
    return "\n".join(lines)


def render_c2_md(report: dict[str, Any]) -> str:
    c2 = report["c2_pairing"]
    lines = [
        f"# {STAGE} — C2 Pairing Feasibility by Context-Length Bin",
        "",
        "The frozen C2 intervention applies a deterministic permutation under the constraints",
        f"`{c2['constraint_reference']}`. Pairing can only succeed if each context-length bin",
        "contains at least two distinct patients and no single patient holds half or more of the",
        "bin, otherwise some study cannot receive text from a different patient.",
        "",
        f"Assessed on the `{c2['assessed_on']}` permitted set, across studies with non-empty context.",
        "",
        "| length bin (effective tokens) | studies | distinct patients | largest patient | share | pairing feasible |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in c2["bins"]:
        lines.append(
            f"| {item['length_bin']} | {item['studies']} | {item['distinct_patients']} | "
            f"{item['largest_single_patient_studies']} | {item['largest_patient_share']:.4%} | "
            f"{item['different_patient_pairing_feasible']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
    ]
    if c2["infeasible_bins"]:
        lines.append(f"- Infeasible bins at corpus level: {c2['infeasible_bins']}.")
    else:
        lines.append("- All populated bins are feasible at corpus level.")
    if c2["empty_bins"]:
        lines.append(f"- Empty bins (no studies): {c2['empty_bins']}.")
    lines += [
        "- Corpus-level feasibility is necessary but not sufficient. The frozen constraint also",
        "  requires pairing within split. No official split file is present, so split-level",
        "  feasibility cannot be verified and must be re-checked once splits exist.",
        "- Bin edges here are provisional. They are not a frozen decision and can be changed by",
        "  the protocol amendment that fixes the N1 threshold.",
        "",
    ]
    return "\n".join(lines)


def _output_guard(output_dir: Path, project_root: Path) -> None:
    names = sorted(p.name for p in output_dir.iterdir() if p.is_file())
    if names != sorted(OUTPUT_FILENAMES):
        raise IntakeContractError(f"unexpected Stage 3B-2 output files: {names}")
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


def run_sweep(*, project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    data_root = root / DATA_ROOT
    output_dir = root / OUTPUT_DIR

    patient_by_report = _load_patient_by_report(data_root)
    sweep = Sweep()
    with zipfile.ZipFile(data_root / REPORTS_ZIP) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            text = zf.read(info).decode("utf-8", errors="replace")
            counts, labels = parse_report(text)
            sweep.add(counts, labels, patient_by_report.get(info.filename, ""))
            del text

    report = build_report(sweep)

    output_dir.mkdir(parents=True, exist_ok=True)
    foreign = {p.name for p in output_dir.iterdir() if p.is_file()} - set(OUTPUT_FILENAMES)
    if foreign:
        raise IntakeContractError(f"refusing to write beside unknown artifacts: {sorted(foreign)}")

    validate_safe_payload(report, project_root=root)

    (output_dir / "stage3b2_context_threshold_sweep.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "stage3b2_context_threshold_sweep.md").write_text(render_md(report), encoding="utf-8")
    (output_dir / "stage3b2_c2_pairing_feasibility.md").write_text(render_c2_md(report), encoding="utf-8")
    (output_dir / "stage3b2_threshold_curve.csv").write_text(
        _csv_text(
            report["threshold_curve"],
            [
                "candidate_set", "threshold_effective_tokens", "n1_informative", "n1_fraction",
                "n2_low_information", "n2_fraction", "n3_absent", "n3_fraction",
                "n1_with_impression", "n1_with_impression_fraction",
                "n1_with_findings", "n1_with_findings_fraction",
            ],
        ),
        encoding="utf-8",
    )
    (output_dir / "stage3b2_candidate_context_sets.csv").write_text(
        _csv_text(
            report["candidate_sets"],
            [
                "candidate_set", "sections", "note", "n3_absent", "n3_absent_fraction",
                "context_present", "context_present_fraction", "median_effective_tokens",
                "max_effective_tokens",
            ],
        ),
        encoding="utf-8",
    )

    hashed = [n for n in OUTPUT_FILENAMES if n != "stage3b2_manifest.json"]
    manifest = {
        "stage": STAGE,
        "title": TITLE,
        "status": report["status"],
        "declarations": list(DECLARATIONS),
        "output_dir": OUTPUT_DIR,
        "reports_parsed": report["reports_parsed"],
        "artifacts": [
            {"name": name, "byte_size": (output_dir / name).stat().st_size, "sha256": sha256_file(output_dir / name)}
            for name in hashed
        ],
        "source_files_audited": [
            {"name": Path(rel).name, "relative_path": f"{DATA_ROOT}/{rel}", "sha256": sha256_file(data_root / rel)}
            for rel in (REPORTS_ZIP, STUDY_LIST)
        ],
        "compliance": report["compliance"],
        "environment": report["environment"],
    }
    validate_safe_payload(manifest, project_root=root)
    (output_dir / "stage3b2_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    _output_guard(output_dir, root)
    return report


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Run the C3-E6 Stage 3B-2 context threshold sweep")
    parser.add_argument("--project-root", type=Path, default=default_root)
    args = parser.parse_args(argv)
    try:
        report = run_sweep(project_root=args.project_root)
    except Exception as exc:  # noqa: BLE001 - surface a single safe line
        print(f"Stage 3B-2 FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"stage": STAGE, "status": report["status"], "reports_parsed": report["reports_parsed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
