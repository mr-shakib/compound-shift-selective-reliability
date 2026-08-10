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
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

# Must precede the first CUDA allocation. M4 keeps two backbones resident on a
# 6 GB card, where fragmentation alone is enough to fail an allocation.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

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


def _available_ram_gb() -> float:
    """Available RAM in GB, from MemAvailable rather than free memory."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1048576
    except OSError:
        pass
    return float("inf")


def _seed_everything(seed: int) -> None:
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _macro_auroc(scores: np.ndarray, targets: np.ndarray, mask: np.ndarray) -> float:
    """Macro AUROC over supervised cells; pathologies without both classes are skipped.

    Non-finite scores are treated as a failed epoch rather than silently dropped.
    A NaN reaching this point means the forward pass diverged, and scoring the
    survivors would report a metric on a subset chosen by numerical accident.
    """
    from sklearn.metrics import roc_auc_score

    if not np.isfinite(scores).all():
        bad = int((~np.isfinite(scores)).sum())
        raise ValueError(
            f"{bad} non-finite score(s) from the forward pass; refusing to compute "
            "AUROC on a numerically invalid epoch"
        )
    aucs = []
    for j in range(targets.shape[1]):
        sel = mask[:, j] > 0
        y = targets[sel, j]
        if sel.sum() < 2 or len(np.unique(y)) < 2:
            continue
        aucs.append(roc_auc_score(y, scores[sel, j]))
    return float(np.mean(aucs)) if aucs else float("nan")


@torch.no_grad()
def evaluate(model, loader, device, needs_text: bool, *, amp: bool) -> tuple[float, float]:
    """Evaluate under the same numerical precision the model was trained in.

    Precision must match training. Evaluating an fp32-trained DenseNet under
    fp16 autocast overflows in the dense blocks and yields NaN scores.
    """
    model.eval()
    torch.cuda.empty_cache()
    losses, S, T, M = [], [], [], []
    for batch in loader:
        image = batch["image"].to(device, non_blocking=True)
        target = batch["target"].to(device, non_blocking=True)
        mask = batch["mask"].to(device, non_blocking=True)
        kw = {}
        if needs_text:
            kw["input_ids"] = batch["input_ids"].to(device, non_blocking=True)
            kw["attention_mask"] = batch["attention_mask"].to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.float16,
                            enabled=amp and device.type == "cuda"):
            logits = model(image=image, **kw)
            loss = masked_bce_with_logits(logits.float(), target, mask)
        losses.append(loss.item())
        S.append(torch.sigmoid(logits.float()).cpu().numpy())
        T.append(target.cpu().numpy())
        M.append(mask.cpu().numpy())
    torch.cuda.empty_cache()
    return float(np.mean(losses)), _macro_auroc(np.concatenate(S), np.concatenate(T),
                                                np.concatenate(M))


def train_one(model_id: str, *, project_root: Path, settings: dict[str, Any],
              num_workers: int = 6, limit: int | None = None,
              seed: int = SEED) -> dict[str, Any]:
    root = Path(project_root).resolve()
    opt_cfg = settings["optimization"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    needs_text = model_id in ("M2", "M4")

    _seed_everything(seed)
    # Frozen in v0.4.1. Input shapes are constant, so cuDNN's autotuner pays for
    # itself once per shape rather than per step.
    torch.backends.cudnn.benchmark = bool(opt_cfg.get("cudnn_benchmark", False))

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

    # Every worker inherits a copy of the index, and refcounting alone is enough
    # to defeat copy-on-write for Python objects. Carry only the columns the
    # dataset reads, and drop the context strings entirely for image-only models.
    keep = ["image_path", "subject_id", *TARGETS] + (["context"] if needs_text else [])
    train_idx = train_idx[keep]
    val_idx = val_idx[keep]

    ds_tr = C3EStudyImageDataset(train_idx, image_root, tokenizer, max_len, train=True)
    ds_va = C3EStudyImageDataset(val_idx, image_root, tokenizer, max_len, train=False)

    # Pinned memory is page-locked and cannot be swapped. On a memory-constrained
    # host that turns pressure into a freeze rather than a slowdown, so it is
    # enabled only when there is real headroom.
    avail_gb = _available_ram_gb()
    pin = avail_gb >= 6.0
    if not pin:
        print(f"  [{model_id}] {avail_gb:.1f} GB RAM available; disabling pinned memory",
              file=sys.stderr, flush=True)

    bs = opt_cfg["batch_size"]
    dl_tr = DataLoader(ds_tr, batch_size=bs, shuffle=True, num_workers=num_workers,
                       pin_memory=pin, drop_last=True,
                       persistent_workers=num_workers > 0,
                       prefetch_factor=2 if num_workers > 0 else None)
    dl_va = DataLoader(ds_va, batch_size=bs, shuffle=False, num_workers=num_workers,
                       pin_memory=pin, persistent_workers=num_workers > 0,
                       prefetch_factor=2 if num_workers > 0 else None)

    model = MODEL_REGISTRY[model_id]().to(device)

    # Separate rates for the two backbones, per v0.4.2. A pretrained transformer
    # fine-tuned at the convolutional rate does not converge usefully.
    lr_img = float(opt_cfg["learning_rate_image"])
    lr_txt = float(opt_cfg["learning_rate_text"])
    text_params, other_params = [], []
    for name, param in model.named_parameters():
        (text_params if "text_backbone" in name or model_id == "M2"
         else other_params).append(param)
    groups = [g for g in ({"params": other_params, "lr": lr_img},
                          {"params": text_params, "lr": lr_txt}) if g["params"]]
    optimizer = torch.optim.AdamW(groups, weight_decay=float(opt_cfg["weight_decay"]))
    print(f"  [{model_id}] lr image {lr_img:g} ({len(other_params)} tensors)  "
          f"lr text {lr_txt:g} ({len(text_params)} tensors)", file=sys.stderr, flush=True)
    scaler = torch.amp.GradScaler("cuda", enabled=opt_cfg["mixed_precision"]
                                  and device.type == "cuda")

    ckpt_dir = root / CKPT_DIR
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    # A replicate seed must not overwrite the primary checkpoint.
    suffix = "" if seed == SEED else f"_seed{seed}"
    ckpt_path = ckpt_dir / f"{model_id.lower()}_best{suffix}.pt"

    # Resume state. Training is long enough that an interruption costs a day,
    # and a run that restarts from epoch 1 is not the same run: its best epoch
    # may lie beyond where the interrupted one stopped. Optimiser and scheduler
    # state are saved with the epoch counter so a resumed run continues the same
    # trajectory rather than beginning a new one.
    resume_path = ckpt_dir / f"{model_id.lower()}{suffix}_resume.pt"
    best = -float("inf")
    best_epoch = -1
    patience = opt_cfg["early_stopping_patience"]
    since_improved = 0
    history: list[dict[str, Any]] = []
    start_epoch = 1

    if resume_path.exists():
        state = torch.load(resume_path, map_location=device, weights_only=False)
        if state.get("model_id") == model_id and state.get("seed") == seed:
            model.load_state_dict(state["model_state"])
            optimizer.load_state_dict(state["optimizer_state"])
            scaler.load_state_dict(state["scaler_state"])
            best = state["best"]
            best_epoch = state["best_epoch"]
            since_improved = state["since_improved"]
            history = state["history"]
            start_epoch = state["epoch"] + 1
            print(f"  [{model_id}] resuming at epoch {start_epoch}; best so far "
                  f"{best:.4f} at epoch {best_epoch}", file=sys.stderr, flush=True)
        else:
            print(f"  [{model_id}] ignoring resume state from a different run",
                  file=sys.stderr, flush=True)

    started = time.time()

    for epoch in range(start_epoch, opt_cfg["max_epochs"] + 1):
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

        # Release the last step's activations and gradients before evaluating.
        # cuDNN autotuning reserves workspace of its own, and on a 6 GB card the
        # two together are enough to OOM at the epoch boundary.
        optimizer.zero_grad(set_to_none=True)
        del image, target, mask, logits, loss, kw

        val_loss, val_auroc = evaluate(model, dl_va, device, needs_text,
                                       amp=opt_cfg["mixed_precision"])
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
                        "seed": seed, "state_dict": model.state_dict()}, ckpt_path)
        else:
            since_improved += 1

        # Written every epoch, improvement or not, so an interruption resumes
        # from the last completed epoch rather than the last improvement.
        torch.save({"model_id": model_id, "seed": seed, "epoch": epoch,
                    "best": best, "best_epoch": best_epoch,
                    "since_improved": since_improved, "history": history,
                    "model_state": model.state_dict(),
                    "optimizer_state": optimizer.state_dict(),
                    "scaler_state": scaler.state_dict()}, resume_path)

        if since_improved >= patience:
            print(f"  [{model_id}] early stop: no improvement in {patience} epochs",
                  file=sys.stderr, flush=True)
            break

    # The run completed on its own terms, so the resume state is no longer
    # meaningful and would otherwise make a later rerun a no-op.
    resume_path.unlink(missing_ok=True)

    digest = hashlib.sha256(ckpt_path.read_bytes()).hexdigest() if ckpt_path.exists() else None
    return {
        "model_id": model_id,
        "train_images": int(len(train_idx)),
        "internal_val_images": int(len(val_idx)),
        "train_patients": int(train_idx["subject_id"].nunique()),
        "internal_val_patients": int(val_idx["subject_id"].nunique()),
        "epochs_run": len(history),
        "completed_normally": True,
        "best_epoch": best_epoch,
        "best_val_auroc_macro": round(best, 6) if best > -float("inf") else None,
        "early_stopped": len(history) < opt_cfg["max_epochs"],
        "history": history,
        "elapsed_seconds": round(time.time() - started, 1),
        "seed": seed,
        "checkpoint": {"relative_path": f"{CKPT_DIR}/{ckpt_path.name}", "sha256": digest},
    }


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Run C3-E6 Stage 6 source-site training")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--models", default="M1,M2,M4")
    # Conservative by default. Each worker is a full Python and torch runtime,
    # and this host has been observed swapping before training even starts.
    ap.add_argument("--num-workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed", type=int, default=SEED,
                    help="replicate seed; the frozen default is the preregistered one")
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
                                  num_workers=args.num_workers, limit=args.limit,
                                  seed=args.seed))
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
