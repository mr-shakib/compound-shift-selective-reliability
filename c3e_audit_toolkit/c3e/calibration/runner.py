"""C3-E6 Stage 7: threshold selection on the calibration tier.

Runs M1 through M4 over the threshold-calibration tier, selects per-pathology
classification thresholds by balanced accuracy, and selects the abstention
cutoffs that deliver the prespecified coverages. Everything selected here is
then frozen and carried unchanged to the external site.

This stage reads the calibration tier and nothing else. The prespecified-eval
tier stays sealed for the confirmatory analysis, and no external-site data is
touched. Selection uses calibration labels only; no evaluation number computed
here is a confirmatory result.
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
import yaml

from ..training.dataset import C3EStudyImageDataset, build_index
from ..training.models import M1ImageOnly, M2TextOnly, M3LateFusion, M4FeatureFusion
from ..training.runner import (CKPT_DIR, IMAGE_DIR, REGISTRY, SEED, checkpoint_name,
                               scored_models,
                               _available_ram_gb, _seed_everything,
                               load_frozen_settings)
from .policy import (TARGETS, abstention_threshold_for_coverage,
                     aggregate_images_to_studies, balanced_accuracy_threshold,
                     hamming_error, selective_risk, study_confidence)

STAGE = "C3-E6 Stage 7"
TITLE = "THRESHOLD SELECTION ON THE CALIBRATION TIER"
OUTPUT_DIR = "results/c3e_mimic/stage7_thresholds"
OUTPUT_DIR_S1 = "results/c3e_mimic/stage7_thresholds_findings"
OUTPUT_DIR_SEED = "results/c3e_mimic/stage7_thresholds_seed{seed}"


def stage7_path(root: Path, label_source: str = "impression",
                seed: int | None = None) -> Path:
    """Locate the frozen thresholds a downstream stage must consume.

    Every stage after this one applies thresholds it did not choose, so every
    stage has to agree on which file holds them. They did not: Stages 8 and 9b
    hardcoded the primary path and ignored the seed, so a replicate run scored
    replicate predictions against the primary model's abstention cutoff and
    reported the result as a seed replicate. The predictions were unaffected
    -- only the cutoff applied to them was wrong -- which is what made the
    mismatch survive a reading of the output.

    Resolution lives here, in the stage that writes these files, so a consumer
    cannot hold an opinion about the path.
    """
    if seed is not None and seed != SEED:
        if label_source != "impression":
            raise RuntimeError(
                f"no Stage 7 exists for seed {seed} with label source "
                f"{label_source!r}; the replicate was run on the primary "
                "endpoint only")
        return Path(root) / OUTPUT_DIR_SEED.format(seed=seed) / "stage7_thresholds.json"
    return Path(root) / (OUTPUT_DIR if label_source == "impression"
                         else OUTPUT_DIR_S1) / "stage7_thresholds.json"

DECLARATIONS = (
    "STAGE 7 ONLY",
    "THRESHOLD SELECTION ON THE CALIBRATION TIER",
    "NO MODEL TRAINING",
    "NO PRESPECIFIED-EVAL-TIER READ",
    "NO EXTERNAL-SITE INFERENCE",
    "NO CROSS-SITE CLAIM",
    "THRESHOLDS FROZEN FOR TRANSFER",
    "SELECTION NUMBERS ARE NOT CONFIRMATORY RESULTS",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@torch.no_grad()
def predict(model, loader, device, needs_text: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    P, Y, M = [], [], []
    for batch in loader:
        kw = {}
        if needs_text:
            kw["input_ids"] = batch["input_ids"].to(device, non_blocking=True)
            kw["attention_mask"] = batch["attention_mask"].to(device, non_blocking=True)
        logits = model(image=batch["image"].to(device, non_blocking=True), **kw)
        P.append(torch.sigmoid(logits.float()).cpu().numpy())
        Y.append(batch["target"].numpy())
        M.append(batch["mask"].numpy())
    return np.concatenate(P), np.concatenate(Y), np.concatenate(M)


def _load(model, path: Path, device):
    blob = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(blob["state_dict"])
    return model


def run(*, project_root: str | Path, num_workers: int = 3,
        label_source: str = "impression",
        seed: int | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    settings = load_frozen_settings(root)
    registry = yaml.safe_load((root / REGISTRY).read_text())
    cls_cfg = registry["classification_policy"]
    sel_cfg = registry["selective_policy"]
    units = registry["analysis_units"]

    if cls_cfg["criterion"] != "balanced_accuracy":
        raise RuntimeError(f"unexpected threshold criterion {cls_cfg['criterion']!r}")
    coverages = [sel_cfg["primary_source_coverage"], *sel_cfg["sensitivity_source_coverages"]]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _seed_everything(SEED)
    torch.backends.cudnn.benchmark = bool(settings["optimization"].get("cudnn_benchmark", False))

    print(f"{STAGE} — {TITLE}", file=sys.stderr)
    print(f"  protocol v{settings['protocol_version']}  criterion "
          f"{cls_cfg['criterion']}  coverages {coverages}", file=sys.stderr, flush=True)

    print("  reading calibration tier ...", file=sys.stderr, flush=True)
    index = build_index(root, tier="threshold_calibration", purpose="calibration",
                        label_source=label_source)
    print(f"  calibration images {len(index):,}  studies "
          f"{index['study_id'].nunique():,}  patients "
          f"{index['subject_id'].nunique():,}", file=sys.stderr, flush=True)

    from transformers import BertTokenizer
    tokenizer = BertTokenizer.from_pretrained(settings["text"]["pretraining"])
    ds = C3EStudyImageDataset(index, root / IMAGE_DIR, tokenizer,
                              settings["text"]["max_sequence_length"])
    loader = DataLoader(ds, batch_size=settings["optimization"]["batch_size"],
                        shuffle=False, num_workers=num_workers,
                        pin_memory=_available_ram_gb() >= 6.0,
                        persistent_workers=num_workers > 0)

    ckpt = root / CKPT_DIR
    scored = scored_models(seed)
    if seed is not None:
        print(f"  seed {seed}: calibrating {', '.join(scored)} only; "
              "M3 needs an M2 replicate", file=sys.stderr, flush=True)

    preds: dict[str, np.ndarray] = {}
    m1 = _load(M1ImageOnly(), ckpt / checkpoint_name("M1", seed), device).to(device)
    print("  scoring M1 ...", file=sys.stderr, flush=True)
    preds["M1"], labels, masks = predict(m1, loader, device, False)
    if "M2" in scored:
        m2 = _load(M2TextOnly(), ckpt / checkpoint_name("M2", seed), device).to(device)
        print("  scoring M2 ...", file=sys.stderr, flush=True)
        preds["M2"], _, _ = predict(m2, loader, device, True)
        print("  scoring M3 ...", file=sys.stderr, flush=True)
        preds["M3"], _, _ = predict(M3LateFusion(m1, m2).to(device), loader, device, True)
        del m2
    del m1
    torch.cuda.empty_cache()
    print("  scoring M4 ...", file=sys.stderr, flush=True)
    m4 = _load(M4FeatureFusion(), ckpt / checkpoint_name("M4", seed), device).to(device)
    preds["M4"], _, _ = predict(m4, loader, device, True)
    del m4
    torch.cuda.empty_cache()

    models: dict[str, Any] = {}
    threshold_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []

    for mid in scored:
        # Aggregate images to studies before any decision is made.
        frame = pd.DataFrame({"subject_id": index["subject_id"].to_numpy(),
                              "study_id": index["study_id"].to_numpy()})
        for j, t in enumerate(TARGETS):
            frame[t] = preds[mid][:, j]
            frame[t + "__label"] = np.where(masks[:, j] > 0, labels[:, j], np.nan)
        studies = aggregate_images_to_studies(frame)

        sp = studies[TARGETS].to_numpy()
        sy = studies[[t + "__label" for t in TARGETS]].to_numpy()
        sm = (~np.isnan(sy)).astype(float)
        sy = np.nan_to_num(sy)

        thresholds, baccs = [], []
        for j, t in enumerate(TARGETS):
            thr, bacc = balanced_accuracy_threshold(sp[:, j], sy[:, j], sm[:, j])
            thresholds.append(thr)
            baccs.append(bacc)
            threshold_rows.append({"model": mid, "pathology": t,
                                   "threshold": round(thr, 6),
                                   "balanced_accuracy": round(bacc, 6),
                                   "supervised_studies": int(sm[:, j].sum())})

        pred_bin = (sp >= np.array(thresholds)[None, :]).astype(float)
        errors = hamming_error(pred_bin, sy, sm)
        conf = study_confidence(sp, sel_cfg["primary_study_confidence"].split("_")[0])

        cov_results = {}
        for cov in coverages:
            cutoff = abstention_threshold_for_coverage(conf, cov)
            r = selective_risk(errors, conf, cutoff)
            r["target_coverage"] = cov
            r["abstention_threshold"] = round(cutoff, 6)
            cov_results[f"{cov:.2f}"] = {k: (round(v, 6) if isinstance(v, float) else v)
                                         for k, v in r.items()}
            coverage_rows.append({"model": mid, "target_coverage": cov,
                                  "abstention_threshold": round(cutoff, 6),
                                  "realised_coverage": round(r["coverage"], 6),
                                  "selective_hamming_error": round(r["selective_hamming_error"], 6),
                                  "full_coverage_hamming_error": round(r["full_coverage_hamming_error"], 6)})

        models[mid] = {
            "classification_thresholds": {t: round(v, 6) for t, v in zip(TARGETS, thresholds)},
            "threshold_balanced_accuracy": {t: round(v, 6) for t, v in zip(TARGETS, baccs)},
            "abstention_thresholds": cov_results,
        }
        print(f"  {mid}: primary cutoff "
              f"{cov_results[f'{coverages[0]:.2f}']['abstention_threshold']:.4f}  "
              f"selective error "
              f"{cov_results[f'{coverages[0]:.2f}']['selective_hamming_error']:.4f}",
              file=sys.stderr, flush=True)

    return {
        "stage": STAGE, "title": TITLE, "status": "PASS",
        "declarations": list(DECLARATIONS),
        "protocol_version": settings["protocol_version"],
        "label_source": label_source, "seed": seed,
        "policy": {"classification": cls_cfg, "selective": sel_cfg, "analysis_units": units},
        "calibration_tier": {
            "images": int(len(index)),
            "studies": int(index["study_id"].nunique()),
            "patients": int(index["subject_id"].nunique()),
        },
        "models": models,
        "threshold_table": threshold_rows,
        "coverage_table": coverage_rows,
        "frozen": True,
        "freeze_note": ("these thresholds transfer unchanged to the external site; "
                        "revising them after inspecting external results would "
                        "answer a different question than the one preregistered"),
        "compliance": {
            "model_training": False,
            "evaluation_tier_read": False,
            "external_site_inference": False,
            "cross_site_claim": False,
            "confirmatory_result_produced": False,
            "identifiers_emitted_to_results": False,
        },
        "environment": {"python": platform.python_version(),
                        "platform": f"{platform.system()}-{platform.machine()}",
                        "torch": torch.__version__},
    }


def _render_md(r: dict[str, Any]) -> str:
    c = r["calibration_tier"]
    md = [f"# {STAGE} — Threshold Selection", "",
          f"Status: **{r['status']}**  ·  protocol v{r['protocol_version']}", ""]
    md += [f"- **{d}**" for d in DECLARATIONS]
    md += ["", "## Calibration tier", "",
           f"{c['images']:,} images · {c['studies']:,} studies · {c['patients']:,} patients.",
           "", "This tier was read for the first time in this stage. Selection uses it",
           "alone; the prespecified-eval tier remains sealed.", "",
           "## Per-pathology classification thresholds", "",
           "Selected by balanced accuracy on study-level mean probabilities.", "",
           "| model | " + " | ".join(TARGETS) + " |",
           "| --- | " + " | ".join("---:" for _ in TARGETS) + " |"]
    for mid in scored_models(r.get("seed")):
        t = r["models"][mid]["classification_thresholds"]
        md.append(f"| {mid} | " + " | ".join(f"{t[p]:.3f}" for p in TARGETS) + " |")
    md += ["", "## Selective policy", "",
           "Confidence is |2p − 1| per pathology, minimised across the five, so a",
           "study is only as trustworthy as its least certain finding. Coverage is",
           "held fixed and error allowed to vary, so source and external sites are",
           "compared at the same burden on the human reader.", "",
           "| model | target coverage | abstention cutoff | realised coverage | selective Hamming | full-coverage Hamming |",
           "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in r["coverage_table"]:
        md.append(f"| {row['model']} | {row['target_coverage']:.0%} | "
                  f"{row['abstention_threshold']:.4f} | {row['realised_coverage']:.1%} | "
                  f"{row['selective_hamming_error']:.4f} | "
                  f"{row['full_coverage_hamming_error']:.4f} |")
    md += ["", "**These thresholds are now frozen.** " + r["freeze_note"] + ".", "",
           "Selection numbers are development quantities. They are not confirmatory",
           "results and must not be reported as such.", ""]
    return "\n".join(md)


def write_outputs(root: Path, report: dict[str, Any]) -> None:
    sd = report.get("seed")
    if sd is not None:
        out = root / OUTPUT_DIR_SEED.format(seed=sd)
    else:
        out = root / (OUTPUT_DIR if report.get("label_source", "impression") == "impression"
                      else OUTPUT_DIR_S1)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage7_thresholds.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "stage7_thresholds.md").write_text(_render_md(report), encoding="utf-8")

    for name, rows, fields in (
        ("stage7_threshold_table.csv", report["threshold_table"],
         ["model", "pathology", "threshold", "balanced_accuracy", "supervised_studies"]),
        ("stage7_coverage_table.csv", report["coverage_table"],
         ["model", "target_coverage", "abstention_threshold", "realised_coverage",
          "selective_hamming_error", "full_coverage_hamming_error"])):
        buf = io.StringIO(newline="")
        w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)
        (out / name).write_text(buf.getvalue(), encoding="utf-8")

    names = ["stage7_thresholds.json", "stage7_thresholds.md",
             "stage7_threshold_table.csv", "stage7_coverage_table.csv"]
    (out / "stage7_manifest.json").write_text(json.dumps({
        "stage": STAGE, "title": TITLE, "status": report["status"],
        "declarations": list(DECLARATIONS), "output_dir": str(out.relative_to(root)),
        "frozen": True,
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
    ap = argparse.ArgumentParser(description="Run C3-E6 Stage 7 threshold selection")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--num-workers", type=int, default=3)
    ap.add_argument("--label-source", default="impression",
                    choices=["impression", "findings"])
    ap.add_argument("--seed", type=int, default=None,
                    help="replicate seed; omit for the primary models")
    args = ap.parse_args(argv)
    try:
        report = run(project_root=args.project_root, num_workers=args.num_workers,
                     label_source=args.label_source, seed=args.seed)
        write_outputs(Path(args.project_root).resolve(), report)
    except Exception as exc:  # noqa: BLE001
        print(f"Stage 7 FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"stage": STAGE, "status": report["status"],
                      "calibration_tier": report["calibration_tier"],
                      "primary_coverage": [r for r in report["coverage_table"]
                                           if r["target_coverage"] == 0.8]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
