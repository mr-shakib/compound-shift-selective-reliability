"""C3-E9b: external-site evaluation under the frozen policy.

Scores M1 through M4 on CheXpert Plus under C0, C1 and C2, applying the Stage 7
thresholds and abstention cutoffs unchanged. That transfer is the study's
central claim: a policy calibrated at one hospital, carried to another without
refitting.

Nothing here is selected, tuned, or fitted. The runner refuses to start without
the Stage 7 artifact, and records its digest, so a threshold cannot be quietly
re-derived against external data.

Point estimates only. Intervals and the confirmatory decision belong to Stage 10.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
from typing import Any

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from ..calibration.policy import (TARGETS, hamming_error, selective_risk,
                                  study_confidence)
from ..calibration.runner import predict
from ..evaluation.interventions import apply_c1, apply_c2, check_invariants
from ..training.models import M1ImageOnly, M2TextOnly, M3LateFusion, M4FeatureFusion
from ..training.runner import (CKPT_DIR, SEED, _available_ram_gb,
                               _seed_everything, load_frozen_settings)
from ..analysis.cache import checkpoint_digest, load as cache_load, save as cache_save
from .dataset import IMAGE_DIR, CheXpertPlusDataset, build_external_index

STAGE = "C3-E9b"
TITLE = "EXTERNAL-SITE EVALUATION UNDER THE FROZEN POLICY"
OUTPUT_DIR = "results/c3e_chexpert_plus/stage9b_evaluation"
OUTPUT_DIR_S1 = "results/c3e_chexpert_plus/stage9b_evaluation_findings"
STAGE7 = "results/c3e_mimic/stage7_thresholds/stage7_thresholds.json"
STAGE7_S1 = "results/c3e_mimic/stage7_thresholds_findings/stage7_thresholds.json"

DECLARATIONS = (
    "STAGE 9b ONLY",
    "EXTERNAL-SITE EVALUATION",
    "THRESHOLDS CONSUMED FROZEN FROM STAGE 7",
    "NO THRESHOLD SELECTED OR REVISED HERE",
    "NO EXTERNAL-SITE TUNING",
    "NO MODEL TRAINING",
    "INFORMATIVENESS RULE TRANSFERRED WITHOUT REFITTING",
    "POINT ESTIMATES ONLY, NO INTERVALS OR TESTS",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _load(model, path: Path, device):
    blob = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(blob["state_dict"])
    return model.to(device)


def _aggregate(frame: pd.DataFrame, probs: np.ndarray, labels: np.ndarray,
               masks: np.ndarray) -> tuple[np.ndarray, ...]:
    """Mean probability within study; the decision unit is the study."""
    agg = pd.DataFrame({"patient": frame["deid_patient_id"].to_numpy(),
                        "study": frame["study_key"].to_numpy()})
    for j, t in enumerate(TARGETS):
        agg[t] = probs[:, j]
        agg[t + "__y"] = np.where(masks[:, j] > 0, labels[:, j], np.nan)
    cols = {t: "mean" for t in TARGETS}
    cols.update({t + "__y": "first" for t in TARGETS})
    cols["patient"] = "first"
    s = agg.groupby("study", as_index=False).agg(cols)
    sp = s[TARGETS].to_numpy()
    sy = s[[t + "__y" for t in TARGETS]].to_numpy()
    sm = (~np.isnan(sy)).astype(float)
    return sp, np.nan_to_num(sy), sm, s["patient"].to_numpy()


def run(*, project_root: str | Path, num_workers: int = 3,
        label_source: str = "impression",
        threshold: int = 3) -> dict[str, Any]:
    root = Path(project_root).resolve()
    settings = load_frozen_settings(root)
    stage7_path = root / (STAGE7 if label_source == "impression" else STAGE7_S1)
    if not stage7_path.exists():
        raise RuntimeError(
            f"missing {STAGE7}; the external evaluation consumes frozen "
            "thresholds and must not derive them from external data")
    stage7 = json.loads(stage7_path.read_text())
    coverages = sorted({c["target_coverage"] for c in stage7["coverage_table"]},
                       reverse=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _seed_everything(SEED)
    torch.backends.cudnn.benchmark = bool(settings["optimization"].get("cudnn_benchmark", False))

    print(f"{STAGE} — {TITLE}", file=sys.stderr)
    print(f"  thresholds from Stage 7 (sha256 {sha256_file(stage7_path)[:16]}…)",
          file=sys.stderr, flush=True)

    index = build_external_index(root, label_source=label_source,
                                 threshold=threshold)
    excluded = int((~index["_present"]).sum())
    index = index[index["_present"]].drop(columns=["_present"]).reset_index(drop=True)
    states = index.groupby("natural_state")["study_key"].nunique().to_dict()
    print(f"  external cohort: {len(index):,} images, "
          f"{index['study_key'].nunique():,} studies, "
          f"{index['deid_patient_id'].nunique():,} patients "
          f"({excluded} excluded as corrupt at source)", file=sys.stderr)
    print(f"  natural states by study: { {k: int(v) for k, v in states.items()} }",
          file=sys.stderr, flush=True)

    c0 = index[index["natural_state"] == "N1"].reset_index(drop=True)
    c0 = c0.rename(columns={"deid_patient_id": "subject_id", "study_key": "study_id"})
    c1, c2 = apply_c1(c0), apply_c2(c0)
    invariants = check_invariants(c0, c1, c2)
    print(f"  N1 eligible: {len(c0):,} images, {c0['study_id'].nunique():,} studies; "
          f"C2 self-assignments {invariants['c2_studies_retaining_own_context']}",
          file=sys.stderr, flush=True)

    from transformers import BertTokenizer
    tokenizer = BertTokenizer.from_pretrained(settings["text"]["pretraining"])
    max_len = settings["text"]["max_sequence_length"]
    bs = settings["optimization"]["batch_size"]
    pin = _available_ram_gb() >= 6.0

    ckpt = root / CKPT_DIR
    shas = {mid: checkpoint_digest(ckpt / f"{mid.lower()}_best.pt")
            for mid in ("M1", "M2", "M4")}
    # M3 has no weights of its own; its identity is that of its two components.
    shas["M3"] = hashlib.sha256((shas["M1"] + shas["M2"]).encode()).hexdigest()[:16]
    m1 = _load(M1ImageOnly(), ckpt / "m1_best.pt", device)
    m2 = _load(M2TextOnly(), ckpt / "m2_best.pt", device)
    m3 = M3LateFusion(m1, m2).to(device)
    m4 = _load(M4FeatureFusion(), ckpt / "m4_best.pt", device)
    specs = (("M1", m1, False), ("M2", m2, True), ("M3", m3, True), ("M4", m4, True))

    rows: list[dict[str, Any]] = []
    m1_probs: dict[str, np.ndarray] = {}

    for cond, frame in (("C0", c0), ("C1", c1), ("C2", c2)):
        f = frame.rename(columns={"subject_id": "deid_patient_id", "study_id": "study_key"})
        ds = CheXpertPlusDataset(f, root / IMAGE_DIR, tokenizer, max_len)
        loader = DataLoader(ds, batch_size=bs, shuffle=False, num_workers=num_workers,
                            pin_memory=pin, persistent_workers=num_workers > 0)
        for mid, model, needs_text in specs:
            hit = cache_load(root, "external", mid, cond,
                             checkpoint_sha=shas[mid], label_source=label_source,
                             threshold=threshold)
            if hit is not None:
                print(f"  {cond} · {mid} (cached)", file=sys.stderr, flush=True)
                sp, sy, sm = hit["probabilities"], hit["labels"], hit["mask"]
                if mid == "M1":
                    m1_probs[cond] = sp
            else:
                print(f"  {cond} · {mid} ...", file=sys.stderr, flush=True)
                probs, labels, masks = predict(model, loader, device, needs_text)
                sp, sy, sm, pats = _aggregate(f, probs, labels, masks)
                cache_save(root, "external", mid, cond, probabilities=sp,
                           labels=sy, mask=sm, patients=pats,
                           checkpoint_sha=shas[mid], label_source=label_source,
                           threshold=threshold)
                if mid == "M1":
                    m1_probs[cond] = sp

            thr = np.array([stage7["models"][mid]["classification_thresholds"][t]
                            for t in TARGETS])
            errors = hamming_error((sp >= thr[None, :]).astype(float), sy, sm)
            conf = study_confidence(sp, "minimum")

            for cov in coverages:
                cutoff = stage7["models"][mid]["abstention_thresholds"][f"{cov:.2f}"]["abstention_threshold"]
                r = selective_risk(errors, conf, cutoff)
                rows.append({
                    "site": "external", "model": mid, "condition": cond,
                    "target_coverage": cov, "frozen_abstention_threshold": cutoff,
                    "realised_coverage": round(r["coverage"], 6),
                    "coverage_drift": round(r["coverage"] - cov, 6),
                    "accepted_studies": r["accepted_studies"],
                    "total_studies": r["total_studies"],
                    "selective_hamming_error": round(r["selective_hamming_error"], 6),
                    "full_coverage_hamming_error": round(r["full_coverage_hamming_error"], 6),
                })

    drift = max(float(np.abs(m1_probs["C0"] - m1_probs[c]).max()) for c in ("C1", "C2"))
    if drift > 1e-5:
        raise RuntimeError(
            f"M1 predictions differ across context conditions by {drift:.2e}; an "
            "image-only model must be invariant to a text intervention")
    print(f"  M1 invariance ok (max drift {drift:.2e})", file=sys.stderr, flush=True)

    return {
        "stage": STAGE, "title": TITLE, "status": "PASS",
        "declarations": list(DECLARATIONS),
        "protocol_version": settings["protocol_version"],
        "label_source": label_source,
        "informativeness_threshold": threshold,
        "cohort": {
            "images": int(len(index)), "studies": int(index["study_key"].nunique()),
            "patients": int(index["deid_patient_id"].nunique()),
            "excluded_corrupt_at_source": excluded,
            "natural_states_by_study": {k: int(v) for k, v in states.items()},
            "n1_images": int(len(c0)), "n1_studies": int(c0["study_id"].nunique()),
            "n1_patients": int(c0["subject_id"].nunique()),
        },
        "invariants": invariants,
        "m1_max_prediction_drift_across_conditions": drift,
        "threshold_source": {"path": STAGE7, "sha256": sha256_file(stage7_path)},
        "results": rows,
        "compliance": {
            "model_training": False, "threshold_selection": False,
            "external_site_tuning": False, "intervals_or_tests_computed": False,
            "identifiers_emitted_to_results": False,
        },
        "environment": {"python": platform.python_version(),
                        "platform": f"{platform.system()}-{platform.machine()}",
                        "torch": torch.__version__},
    }


def _render_md(r: dict[str, Any]) -> str:
    c = r["cohort"]
    md = [f"# {STAGE} — External-Site Evaluation", "",
          f"Status: **{r['status']}**  ·  protocol v{r['protocol_version']}  ·  "
          f"labels `{r['label_source']}`", ""]
    md += [f"- **{d}**" for d in DECLARATIONS]
    md += ["", "## Cohort", "",
           f"{c['images']:,} images · {c['studies']:,} studies · {c['patients']:,} patients "
           f"({c['excluded_corrupt_at_source']} excluded as corrupt at source).", "",
           "Natural context states by study: "
           + ", ".join(f"**{k}** {v:,}" for k, v in sorted(c["natural_states_by_study"].items())),
           "",
           f"Interventions apply to the {c['n1_studies']:,} N1 studies. Unlike the source",
           "site, where every cohort study was N1 by construction, the natural-state",
           "distribution is informative here.", "",
           "## Selective Hamming error under the frozen policy", ""]
    for cov in sorted({row["target_coverage"] for row in r["results"]}, reverse=True):
        md += [f"### Target coverage {cov:.0%}", "",
               "| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |",
               "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for mid in ("M1", "M2", "M3", "M4"):
            g = {row["condition"]: row["selective_hamming_error"] for row in r["results"]
                 if row["model"] == mid and row["target_coverage"] == cov}
            md.append(f"| {mid} | {g['C0']:.4f} | {g['C1']:.4f} | {g['C2']:.4f} | "
                      f"{g['C1'] - g['C0']:+.4f} | {g['C2'] - g['C0']:+.4f} |")
        md += ["", "| model | realised coverage C0 | C1 | C2 |",
               "| --- | ---: | ---: | ---: |"]
        for mid in ("M1", "M2", "M3", "M4"):
            g = {row["condition"]: row["realised_coverage"] for row in r["results"]
                 if row["model"] == mid and row["target_coverage"] == cov}
            md.append(f"| {mid} | {g['C0']:.1%} | {g['C1']:.1%} | {g['C2']:.1%} |")
        md.append("")
    md += ["Thresholds and cutoffs are Stage 7 values applied unchanged; none was",
           "selected or revised against external data.", "",
           "Point estimates only. Intervals and the confirmatory decision belong to",
           "the analysis stage.", ""]
    return "\n".join(md)


def write_outputs(root: Path, report: dict[str, Any]) -> None:
    base = (OUTPUT_DIR if report.get("label_source", "impression") == "impression"
            else OUTPUT_DIR_S1)
    t = report.get("informativeness_threshold", 3)
    out = root / (base if t == 3 else f"{base}_T{t}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage9b_evaluation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "stage9b_evaluation.md").write_text(_render_md(report), encoding="utf-8")

    fields = ["site", "model", "condition", "target_coverage",
              "frozen_abstention_threshold", "realised_coverage", "coverage_drift",
              "accepted_studies", "total_studies", "selective_hamming_error",
              "full_coverage_hamming_error"]
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for row in report["results"]:
        w.writerow(row)
    (out / "stage9b_results.csv").write_text(buf.getvalue(), encoding="utf-8")

    names = ["stage9b_evaluation.json", "stage9b_evaluation.md", "stage9b_results.csv"]
    (out / "stage9b_manifest.json").write_text(json.dumps({
        "stage": STAGE, "title": TITLE, "status": report["status"],
        "declarations": list(DECLARATIONS), "output_dir": str(out.relative_to(root)),
        "artifacts": [{"name": n, "byte_size": (out / n).stat().st_size,
                       "sha256": sha256_file(out / n)} for n in names],
        "compliance": report["compliance"], "environment": report["environment"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    restricted = re.compile(
        r"(?:patient|subject|study|image)\d{3,}|(?:^|[/\\])[ps]\d{5,}", re.IGNORECASE)
    root_text = str(root.resolve())
    for path in sorted(out.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if root_text in text:
            raise RuntimeError(f"absolute project path leaked into {path.name}")
        if restricted.search(text):
            raise RuntimeError(f"restricted row-level value detected in {path.name}")


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Run C3-E9b external-site evaluation")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--num-workers", type=int, default=3)
    ap.add_argument("--label-source", default="impression",
                    choices=["impression", "findings"])
    ap.add_argument("--threshold", type=int, default=3,
                    help="informativeness threshold; 3 is the preregistered primary")
    args = ap.parse_args(argv)
    try:
        report = run(project_root=args.project_root, num_workers=args.num_workers,
                     label_source=args.label_source, threshold=args.threshold)
        write_outputs(Path(args.project_root).resolve(), report)
    except Exception as exc:  # noqa: BLE001
        print(f"{STAGE} FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    primary = [r for r in report["results"] if r["target_coverage"] == 0.8]
    print(json.dumps({"stage": STAGE, "status": report["status"],
                      "cohort": report["cohort"], "primary_coverage": primary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
