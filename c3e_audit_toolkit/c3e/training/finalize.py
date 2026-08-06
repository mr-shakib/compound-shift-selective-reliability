"""C3-E6 Stage 6b: assemble M3 and write the Stage 6 audit artifact.

M3 is the probability average of a trained M1 and M2. It has no parameters of
its own, so it is assembled here rather than trained. That is the point of it:
any gain M4 shows over M3 is attributable to the learned fusion rather than to
having two modalities, because M3 already has both.

All four models are scored on the same patient-disjoint internal validation
split carved from the model-train tier. These are development numbers, not
confirmatory ones. The calibration and evaluation tiers are untouched, no
threshold is selected, and no external-site inference happens here.

Checkpoints are restricted data. Only aggregate scores, curves, and provenance
reach results/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
from typing import Any

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
import torch
from torch.utils.data import DataLoader

from .dataset import C3EStudyImageDataset, TARGETS, build_index, split_internal_validation
from .models import M1ImageOnly, M2TextOnly, M3LateFusion, M4FeatureFusion
from .runner import (CKPT_DIR, IMAGE_DIR, OUTPUT_DIR, SEED, _available_ram_gb,
                     _seed_everything, evaluate, load_frozen_settings)

STAGE = "C3-E6 Stage 6b"
TITLE = "M3 ASSEMBLY AND STAGE 6 AUDIT"

DECLARATIONS = (
    "STAGE 6b ONLY",
    "M3 ASSEMBLED FROM TRAINED M1 AND M2, NOT TRAINED",
    "SCORED ON INTERNAL VALIDATION CARVED FROM MODEL TRAIN",
    "NO CALIBRATION-TIER READ",
    "NO PRESPECIFIED-EVAL-TIER READ",
    "NO PREDICTION THRESHOLD SELECTION",
    "NO EXTERNAL-SITE INFERENCE",
    "NO CROSS-SITE CLAIM",
    "DEVELOPMENT NUMBERS, NOT CONFIRMATORY RESULTS",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)

EPOCH_RE = re.compile(
    r"\[(M\d)\] epoch (\d+): train_loss ([\d.]+)\s+val_loss ([\d.]+)\s+val_auroc ([\d.]+)")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_curves(log_paths: list[Path]) -> dict[str, list[dict[str, float]]]:
    """Best-effort recovery of per-epoch curves from the training logs.

    The checkpoint evaluation below is authoritative; these curves are recorded
    for the record and are simply omitted if the logs are unavailable.
    """
    curves: dict[str, list[dict[str, float]]] = {}
    for p in log_paths:
        if not p.exists():
            continue
        for line in p.read_text(errors="replace").replace("\r", "\n").splitlines():
            m = EPOCH_RE.search(line)
            if not m:
                continue
            mid, ep, tr, vl, va = m.groups()
            curves.setdefault(mid, []).append({
                "epoch": int(ep), "train_loss": float(tr),
                "val_loss": float(vl), "val_auroc_macro": float(va)})
    for mid in curves:
        seen, out = set(), []
        for row in curves[mid]:
            if row["epoch"] not in seen:
                seen.add(row["epoch"])
                out.append(row)
        curves[mid] = sorted(out, key=lambda r: r["epoch"])
    return curves


def load_checkpoint(model: torch.nn.Module, path: Path, device) -> dict[str, Any]:
    blob = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(blob["state_dict"])
    return {"epoch": blob.get("epoch"), "val_auroc_macro": blob.get("val_auroc_macro")}


def run(*, project_root: str | Path, num_workers: int = 3) -> dict[str, Any]:
    root = Path(project_root).resolve()
    settings = load_frozen_settings(root)
    opt_cfg = settings["optimization"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt_dir = root / CKPT_DIR

    _seed_everything(SEED)
    torch.backends.cudnn.benchmark = bool(opt_cfg.get("cudnn_benchmark", False))

    print(f"{STAGE} — {TITLE}", file=sys.stderr)
    print(f"  protocol v{settings['protocol_version']}", file=sys.stderr, flush=True)

    print("  building internal validation split ...", file=sys.stderr, flush=True)
    index = build_index(root, tier="model_train")
    _, val_idx = split_internal_validation(index)
    del index
    print(f"  internal-val images {len(val_idx):,}  "
          f"patients {val_idx['subject_id'].nunique():,}", file=sys.stderr, flush=True)

    from transformers import BertTokenizer
    tokenizer = BertTokenizer.from_pretrained(settings["text"]["pretraining"])
    max_len = settings["text"]["max_sequence_length"]
    bs = opt_cfg["batch_size"]
    pin = _available_ram_gb() >= 6.0

    keep = ["image_path", "subject_id", "context", *TARGETS]
    ds = C3EStudyImageDataset(val_idx[keep], root / IMAGE_DIR, tokenizer, max_len)
    loader = DataLoader(ds, batch_size=bs, shuffle=False, num_workers=num_workers,
                        pin_memory=pin, persistent_workers=num_workers > 0)

    scores: dict[str, dict[str, Any]] = {}
    ckpts: dict[str, dict[str, Any]] = {}

    # M1 and M2 are needed both in their own right and to build M3.
    m1, m2 = M1ImageOnly().to(device), M2TextOnly().to(device)
    ckpts["M1"] = load_checkpoint(m1, ckpt_dir / "m1_best.pt", device)
    ckpts["M2"] = load_checkpoint(m2, ckpt_dir / "m2_best.pt", device)

    for mid, model, needs_text in (("M1", m1, False), ("M2", m2, True)):
        print(f"  scoring {mid} ...", file=sys.stderr, flush=True)
        loss, auroc = evaluate(model, loader, device, needs_text,
                               amp=opt_cfg["mixed_precision"])
        scores[mid] = {"val_loss": round(loss, 6), "val_auroc_macro": round(auroc, 6)}

    print("  assembling and scoring M3 (no training) ...", file=sys.stderr, flush=True)
    m3 = M3LateFusion(m1, m2).to(device)
    loss, auroc = evaluate(m3, loader, device, True, amp=opt_cfg["mixed_precision"])
    scores["M3"] = {"val_loss": round(loss, 6), "val_auroc_macro": round(auroc, 6)}
    trainable_m3 = sum(p.numel() for p in m3.parameters() if p.requires_grad)
    del m1, m2, m3
    torch.cuda.empty_cache()

    print("  scoring M4 ...", file=sys.stderr, flush=True)
    m4 = M4FeatureFusion().to(device)
    ckpts["M4"] = load_checkpoint(m4, ckpt_dir / "m4_best.pt", device)
    loss, auroc = evaluate(m4, loader, device, True, amp=opt_cfg["mixed_precision"])
    scores["M4"] = {"val_loss": round(loss, 6), "val_auroc_macro": round(auroc, 6)}
    del m4
    torch.cuda.empty_cache()

    curves = parse_curves([root / "logs/stage6_training.log",
                           root / "logs/stage6_training_m2m4.log"])

    checkpoint_records = []
    for mid, fname in (("M1", "m1_best.pt"), ("M2", "m2_best.pt"), ("M4", "m4_best.pt")):
        p = ckpt_dir / fname
        checkpoint_records.append({
            "model_id": mid,
            "relative_path": f"{CKPT_DIR}/{fname}",
            "byte_size": p.stat().st_size,
            "sha256": sha256_file(p),
            "selected_epoch": ckpts[mid]["epoch"],
            "selection_val_auroc_macro": ckpts[mid]["val_auroc_macro"],
        })

    return {
        "stage": STAGE, "title": TITLE, "status": "PASS",
        "declarations": list(DECLARATIONS),
        "protocol_version": settings["protocol_version"],
        "internal_validation": {
            "images": int(len(val_idx)),
            "patients": int(val_idx["subject_id"].nunique()),
            "source_tier": "model_train",
            "note": "patient-disjoint split carved from model train; the "
                    "calibration and evaluation tiers were not read",
        },
        "scores": scores,
        "m3": {"trained": False, "trainable_parameters": int(trainable_m3),
               "construction": "probability average of M1 and M2"},
        "training_curves": curves,
        "checkpoints": checkpoint_records,
        "compliance": {
            "model_training": False,
            "calibration_tier_read": False,
            "evaluation_tier_read": False,
            "threshold_selection": False,
            "external_site_inference": False,
            "cross_site_claim": False,
            "identifiers_emitted_to_results": False,
        },
        "environment": {"python": platform.python_version(),
                        "platform": f"{platform.system()}-{platform.machine()}",
                        "torch": torch.__version__},
    }


def _render_md(r: dict[str, Any]) -> str:
    md = [f"# {STAGE} — M3 Assembly and Stage 6 Audit", "",
          f"Status: **{r['status']}**  ·  protocol v{r['protocol_version']}", ""]
    md += [f"- **{d}**" for d in DECLARATIONS]
    iv = r["internal_validation"]
    md += ["", "## Internal validation set", "",
           f"{iv['images']:,} images from {iv['patients']:,} patients, "
           f"carved patient-disjoint from the `{iv['source_tier']}` tier.",
           "", "These are development numbers used for model selection. They are not",
           "confirmatory results and are not comparable to the prespecified evaluation.",
           "", "## Scores", "",
           "| model | role | val loss | val macro AUROC |",
           "| --- | --- | ---: | ---: |"]
    roles = {"M1": "image-only control", "M2": "text-only / shortcut control",
             "M3": "probability late fusion (untrained)",
             "M4": "feature-concatenation fusion"}
    for mid in ("M1", "M2", "M3", "M4"):
        s = r["scores"][mid]
        md.append(f"| {mid} | {roles[mid]} | {s['val_loss']:.4f} | "
                  f"**{s['val_auroc_macro']:.4f}** |")
    md += ["", f"M3 holds {r['m3']['trainable_parameters']} trainable parameters by "
           "construction; it averages M1 and M2 probabilities.", ""]
    if r["training_curves"]:
        md += ["## Training curves", "",
               "| model | epoch | train loss | val loss | val macro AUROC |",
               "| --- | ---: | ---: | ---: | ---: |"]
        for mid in sorted(r["training_curves"]):
            for e in r["training_curves"][mid]:
                md.append(f"| {mid} | {e['epoch']} | {e['train_loss']:.4f} | "
                          f"{e['val_loss']:.4f} | {e['val_auroc_macro']:.4f} |")
        md.append("")
    md += ["## Checkpoints", "",
           "| model | selected epoch | selection AUROC | bytes | sha256 |",
           "| --- | ---: | ---: | ---: | --- |"]
    for c in r["checkpoints"]:
        md.append(f"| {c['model_id']} | {c['selected_epoch']} | "
                  f"{c['selection_val_auroc_macro']:.4f} | {c['byte_size']:,} | "
                  f"`{c['sha256'][:16]}…` |")
    md += ["", "Checkpoints are restricted data and live in the gitignored tree.", ""]
    return "\n".join(md)


def write_outputs(root: Path, report: dict[str, Any]) -> None:
    out = root / OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage6b_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "stage6b_audit.md").write_text(_render_md(report), encoding="utf-8")

    import csv, io
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["model", "val_loss", "val_auroc_macro"])
    for mid in ("M1", "M2", "M3", "M4"):
        s = report["scores"][mid]
        w.writerow([mid, s["val_loss"], s["val_auroc_macro"]])
    (out / "stage6b_scores.csv").write_text(buf.getvalue(), encoding="utf-8")

    names = ["stage6b_audit.json", "stage6b_audit.md", "stage6b_scores.csv"]
    manifest = {
        "stage": STAGE, "title": TITLE, "status": report["status"],
        "declarations": list(DECLARATIONS), "output_dir": OUTPUT_DIR,
        "artifacts": [{"name": n, "byte_size": (out / n).stat().st_size,
                       "sha256": sha256_file(out / n)} for n in names],
        "compliance": report["compliance"], "environment": report["environment"],
    }
    (out / "stage6b_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Nothing leaves this stage carrying an identifier or a local path.
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
    ap = argparse.ArgumentParser(description="Run C3-E6 Stage 6b: assemble M3 and audit")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--num-workers", type=int, default=3)
    args = ap.parse_args(argv)

    try:
        report = run(project_root=args.project_root, num_workers=args.num_workers)
        write_outputs(Path(args.project_root).resolve(), report)
    except Exception as exc:  # noqa: BLE001
        print(f"Stage 6b FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"stage": STAGE, "status": report["status"],
                      "scores": report["scores"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
