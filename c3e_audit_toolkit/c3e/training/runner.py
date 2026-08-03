"""C3-E6 Stage 6: source-site training runner for M1, M2, and M4.

M3 needs no training — it averages the probabilities of a trained M1 and M2 —
so it is assembled at evaluation time rather than here.

Everything that could otherwise be tuned against a result is fixed by protocol
v0.4.0: batch size, epoch ceiling, early-stopping metric, patience, and the
mixed-precision setting. The runner reads them rather than accepting them as
arguments, so a later run cannot quietly differ from the preregistered one.

Training reads the model-train tier only. Early stopping uses a patient-disjoint
internal validation split carved from that same tier, because the protocol
reserves the calibration and evaluation tiers for later stages.

Checkpoints are restricted data and stay in the gitignored data tree. Only
training curves, provenance, and manifests reach results/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader
import yaml

from .dataset import C3EStudyImageDataset, TARGETS, build_index, split_internal_validation
from .models import MODEL_REGISTRY, masked_bce_with_logits

STAGE = "C3-E6 Stage 6"
TITLE = "SOURCE-SITE MODEL TRAINING"

DECLARATIONS = (
    "STAGE 6 ONLY",
    "SOURCE-SITE TRAINING ON THE MODEL-TRAIN TIER ONLY",
    "NO CALIBRATION-TIER READ",
    "NO PRESPECIFIED-EVAL-TIER READ",
    "NO PREDICTION THRESHOLD SELECTION",
    "NO EXTERNAL-SITE INFERENCE",
    "NO CROSS-SITE CLAIM",
    "CHECKPOINTS CONFINED TO THE PROTECTED DATA TREE",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)

REGISTRY = "protocols/C3E6_stage2/config/experiment_registry.yaml"
IMAGE_DIR = "data/mimic/images_224"
CKPT_DIR = "data/models/c3e"
OUTPUT_DIR = "results/c3e_mimic/stage6_training"
SEED = 20260718


def load_frozen_settings(root: Path) -> dict[str, Any]:
    """Read the frozen optimisation block. These are not runner arguments."""
    reg = yaml.safe_load((root / REGISTRY).read_text())
    backbones = reg["models"]["exact_backbones"]
    if backbones.get("status") != "RESOLVED":
        raise RuntimeError(
            "models.exact_backbones is not RESOLVED in the protocol registry. "
            "Training before the backbone amendment would make the choice post-hoc."
        )
    return {
        "protocol_version": reg["protocol_version"],
        "optimization": backbones["optimization"],
        "image": backbones["image"],
        "text": backbones["text"],
    }


def _seed_everything(seed: int) -> None:
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _macro_auroc(scores: np.ndarray, targets: np.ndarray, mask: np.ndarray) -> float:
    """Macro AUROC over supervised cells; pathologies without both classes are skipped."""
    from sklearn.metrics import roc_auc_score

    aucs = []
    for j in range(targets.shape[1]):
        sel = mask[:, j] > 0
        y = targets[sel, j]
        if sel.sum() < 2 or len(np.unique(y)) < 2:
            continue
        aucs.append(roc_auc_score(y, scores[sel, j]))
    return float(np.mean(aucs)) if aucs else float("nan")


@torch.no_grad()
def evaluate(model, loader, device, needs_text: bool) -> tuple[float, float]:
    model.eval()
    losses, S, T, M = [], [], [], []
    for batch in loader:
        image = batch["image"].to(device, non_blocking=True)
        target = batch["target"].to(device, non_blocking=True)
        mask = batch["mask"].to(device, non_blocking=True)
        kw = {}
        if needs_text:
            kw["input_ids"] = batch["input_ids"].to(device, non_blocking=True)
            kw["attention_mask"] = batch["attention_mask"].to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            logits = model(image=image, **kw)
            loss = masked_bce_with_logits(logits.float(), target, mask)
        losses.append(loss.item())
        S.append(torch.sigmoid(logits.float()).cpu().numpy())
        T.append(target.cpu().numpy())
        M.append(mask.cpu().numpy())
    return float(np.mean(losses)), _macro_auroc(np.concatenate(S), np.concatenate(T),
                                                np.concatenate(M))


def train_one(model_id: str, *, project_root: Path, settings: dict[str, Any],
              num_workers: int = 6, limit: int | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    opt_cfg = settings["optimization"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    needs_text = model_id in ("M2", "M4")

    _seed_everything(SEED)

    print(f"[{model_id}] building index (model_train tier only) ...", file=sys.stderr, flush=True)
    index = build_index(root, tier="model_train")
    if limit:
        index = index.head(limit)
    train_idx, val_idx = split_internal_validation(index)
    print(f"[{model_id}] train images {len(train_idx):,}  internal-val images {len(val_idx):,}",
          file=sys.stderr, flush=True)

    tokenizer = None
    if needs_text:
        from transformers import BertTokenizer
        tokenizer = BertTokenizer.from_pretrained(settings["text"]["pretraining"])

    max_len = settings["text"]["max_sequence_length"]
    image_root = root / IMAGE_DIR
    ds_tr = C3EStudyImageDataset(train_idx, image_root, tokenizer, max_len, train=True)
    ds_va = C3EStudyImageDataset(val_idx, image_root, tokenizer, max_len, train=False)

    bs = opt_cfg["batch_size"]
    dl_tr = DataLoader(ds_tr, batch_size=bs, shuffle=True, num_workers=num_workers,
                       pin_memory=True, drop_last=True, persistent_workers=num_workers > 0)
    dl_va = DataLoader(ds_va, batch_size=bs, shuffle=False, num_workers=num_workers,
                       pin_memory=True, persistent_workers=num_workers > 0)

    model = MODEL_REGISTRY[model_id]().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=opt_cfg["mixed_precision"]
                                  and device.type == "cuda")

    ckpt_dir = root / CKPT_DIR
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / f"{model_id.lower()}_best.pt"

    best = -float("inf")
    best_epoch = -1
    patience = opt_cfg["early_stopping_patience"]
    since_improved = 0
    history: list[dict[str, Any]] = []
    started = time.time()

    for epoch in range(1, opt_cfg["max_epochs"] + 1):
        model.train()
        running, seen, t0, last = 0.0, 0, time.time(), 0.0
        for step, batch in enumerate(dl_tr, 1):
            image = batch["image"].to(device, non_blocking=True)
            target = batch["target"].to(device, non_blocking=True)
            mask = batch["mask"].to(device, non_blocking=True)
            kw = {}
            if needs_text:
                kw["input_ids"] = batch["input_ids"].to(device, non_blocking=True)
                kw["attention_mask"] = batch["attention_mask"].to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16,
                                enabled=opt_cfg["mixed_precision"] and device.type == "cuda"):
                logits = model(image=image, **kw)
                loss = masked_bce_with_logits(logits.float(), target, mask)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running += loss.item() * image.size(0)
            seen += image.size(0)
            now = time.time()
            if now - last >= 3.0:
                last = now
                el = now - t0
                rate = seen / el if el else 0.0
                eta = (len(ds_tr) - seen) / rate if rate > 0 else 0.0
                print(f"\r  [{model_id}] epoch {epoch}/{opt_cfg['max_epochs']}  "
                      f"{seen:,}/{len(ds_tr):,} ({seen / len(ds_tr):5.1%})  "
                      f"loss {running / max(seen, 1):.4f}  {rate:5.0f} img/s  "
                      f"eta {int(eta // 60)}m{int(eta % 60):02d}s    ",
                      end="", file=sys.stderr, flush=True)

        val_loss, val_auroc = evaluate(model, dl_va, device, needs_text)
        epoch_time = time.time() - t0
        improved = val_auroc > best
        print(f"\r  [{model_id}] epoch {epoch}: train_loss {running / max(seen, 1):.4f}  "
              f"val_loss {val_loss:.4f}  val_auroc {val_auroc:.4f}  "
              f"{epoch_time / 60:.1f} min{'  *best' if improved else ''}          ",
              file=sys.stderr, flush=True)

        history.append({"epoch": epoch, "train_loss": round(running / max(seen, 1), 6),
                        "val_loss": round(val_loss, 6), "val_auroc_macro": round(val_auroc, 6),
                        "seconds": round(epoch_time, 1)})

        if improved:
            best, best_epoch, since_improved = val_auroc, epoch, 0
            torch.save({"model_id": model_id, "epoch": epoch, "val_auroc_macro": val_auroc,
                        "state_dict": model.state_dict()}, ckpt_path)
        else:
            since_improved += 1
            if since_improved >= patience:
                print(f"  [{model_id}] early stop: no improvement in {patience} epochs",
                      file=sys.stderr, flush=True)
                break

    digest = hashlib.sha256(ckpt_path.read_bytes()).hexdigest() if ckpt_path.exists() else None
    return {
        "model_id": model_id,
        "train_images": int(len(train_idx)),
        "internal_val_images": int(len(val_idx)),
        "train_patients": int(train_idx["subject_id"].nunique()),
        "internal_val_patients": int(val_idx["subject_id"].nunique()),
        "epochs_run": len(history),
        "best_epoch": best_epoch,
        "best_val_auroc_macro": round(best, 6) if best > -float("inf") else None,
        "early_stopped": len(history) < opt_cfg["max_epochs"],
        "history": history,
        "elapsed_seconds": round(time.time() - started, 1),
        "checkpoint": {"relative_path": f"{CKPT_DIR}/{ckpt_path.name}", "sha256": digest},
    }


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Run C3-E6 Stage 6 source-site training")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--models", default="M1,M2,M4")
    ap.add_argument("--num-workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)

    root = Path(args.project_root).resolve()
    try:
        settings = load_frozen_settings(root)
    except Exception as exc:  # noqa: BLE001
        print(f"Stage 6 FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(f"{STAGE} — {TITLE}", file=sys.stderr)
    print(f"  protocol   : v{settings['protocol_version']} (frozen settings)", file=sys.stderr)
    print(f"  batch_size {settings['optimization']['batch_size']}  "
          f"max_epochs {settings['optimization']['max_epochs']}  "
          f"patience {settings['optimization']['early_stopping_patience']}", file=sys.stderr)

    runs = []
    for model_id in [m.strip() for m in args.models.split(",") if m.strip()]:
        if model_id not in MODEL_REGISTRY:
            print(f"Stage 6 FAIL: unknown model '{model_id}'. M3 is assembled at "
                  "evaluation from trained M1 and M2 and is not trained here.",
                  file=sys.stderr)
            return 2
        try:
            runs.append(train_one(model_id, project_root=root, settings=settings,
                                  num_workers=args.num_workers, limit=args.limit))
        except Exception as exc:  # noqa: BLE001
            print(f"Stage 6 FAIL on {model_id}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2

    print(json.dumps({"stage": STAGE, "status": "PASS",
                      "models": [{k: r[k] for k in
                                  ("model_id", "epochs_run", "best_epoch",
                                   "best_val_auroc_macro", "elapsed_seconds")} for r in runs]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
