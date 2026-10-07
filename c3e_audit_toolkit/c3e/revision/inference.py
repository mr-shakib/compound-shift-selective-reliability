"""Revision inference: study-keyed prediction caches for post hoc analyses.

Reuses the frozen dataset classes, model classes, ``predict`` and the study
aggregation of Stages 7, 8 and 9b, unchanged. What differs is only what is
recorded: these caches carry the study key alongside the patient, so later
analyses never have to reconstruct row identity.

Uses, all post hoc (Revision R1):

* calibration tier, primary and replicate models -- read under
  ``purpose="calibration"`` exactly as Stage 7 did; used to (a) verify that the
  frozen Stage 7 thresholds reproduce, (b) fit exploratory comparator
  selective scores on the source calibration tier only;
* additional C2 donor permutations (seeds other than the frozen 20260718) at
  either site, for M2, M3 and M4 -- exploratory robustness of C2;
* M2 and M3 under a replicate training seed, once an M2 replicate exists.

No threshold, cutoff or score is fitted on external data anywhere here.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from ..analysis.cache import checkpoint_digest
from ..calibration.policy import TARGETS
from ..calibration.runner import predict
from ..evaluation.interventions import apply_c1, apply_c2, natural_state
from ..external.dataset import IMAGE_DIR as EXT_IMAGE_DIR, CheXpertPlusDataset, build_external_index
from ..training.dataset import C3EStudyImageDataset, build_index
from ..training.models import M1ImageOnly, M2TextOnly, M3LateFusion, M4FeatureFusion
from ..training.runner import (CKPT_DIR, IMAGE_DIR, SEED, _seed_everything, checkpoint_name,
                               load_frozen_settings)

REV_CACHE = "data/revision/predictions"


def rev_cache_path(root: Path, *, site: str, tier: str, model: str, cond: str,
                   train_seed: int | None, c2_seed: int | None, label_source: str = "impression",
                   threshold: int = 3) -> Path:
    tag = f"{site}__{tier}__{model}__{cond}__{label_source}__T{threshold}"
    tag += f"__train{train_seed or SEED}"
    if cond == "C2":
        tag += f"__c2seed{c2_seed}"
    return Path(root) / REV_CACHE / f"{tag}.npz"


def _aggregate(frame: pd.DataFrame, site: str, probs, labels, masks):
    """Mean probability within study; first observed label (as Stages 7-9b).

    Row order reproduces the stage caches: the source grouped by
    (subject_id, study_id), the external site by study key.
    """
    agg = pd.DataFrame({"patient": frame["subject_id"].astype(str).to_numpy(),
                        "study": frame["study_id"].astype(str).to_numpy(),
                        "_s": frame["subject_id"].to_numpy(),
                        "_t": frame["study_id"].to_numpy()})
    for j, t in enumerate(TARGETS):
        agg[t] = probs[:, j]
        agg[t + "__y"] = np.where(masks[:, j] > 0, labels[:, j], np.nan)
    cols = {t: "mean" for t in TARGETS}
    cols.update({t + "__y": "first" for t in TARGETS})
    cols.update({"patient": "first", "study": "first"})
    keys = ["_s", "_t"] if site == "source" else ["study"]
    if site != "source":
        cols.pop("study")
    s = agg.groupby(keys, as_index=False, sort=True).agg(cols)
    sy = s[[t + "__y" for t in TARGETS]].to_numpy()
    return (s[TARGETS].to_numpy(), np.nan_to_num(sy), (~np.isnan(sy)).astype(float),
            s["patient"].to_numpy().astype(str), s["study"].to_numpy().astype(str))


def _models(root: Path, wanted: list[str], train_seed: int | None, device):
    ckpt = Path(root) / CKPT_DIR

    def load(cls, mid):
        blob = torch.load(ckpt / checkpoint_name(mid, train_seed), map_location=device,
                          weights_only=False)
        m = cls()
        m.load_state_dict(blob["state_dict"])
        return m.to(device).eval()

    out, shas = {}, {}
    need1 = any(m in ("M1", "M3") for m in wanted)
    need2 = any(m in ("M2", "M3") for m in wanted)
    m1 = load(M1ImageOnly, "M1") if need1 else None
    m2 = load(M2TextOnly, "M2") if need2 else None
    if m1 is not None:
        shas["M1"] = checkpoint_digest(ckpt / checkpoint_name("M1", train_seed))
    if m2 is not None:
        shas["M2"] = checkpoint_digest(ckpt / checkpoint_name("M2", train_seed))
    for mid in wanted:
        if mid == "M1":
            out[mid] = (m1, False)
        elif mid == "M2":
            out[mid] = (m2, True)
        elif mid == "M3":
            out[mid] = (M3LateFusion(m1, m2).to(device), True)
            shas["M3"] = "+".join([shas["M1"], shas["M2"]])
        elif mid == "M4":
            out[mid] = (load(M4FeatureFusion, "M4"), True)
            shas["M4"] = checkpoint_digest(ckpt / checkpoint_name("M4", train_seed))
    return out, shas


def frames(root: Path, site: str, tier: str, *, threshold: int = 3, c2_seed: int = 20260718,
           conditions=("C0", "C1", "C2"), label_source: str = "impression"):
    """Image-level frames per condition, built exactly as the stages built them."""
    root = Path(root)
    if site == "source":
        purpose = "calibration" if tier == "threshold_calibration" else "confirmatory_evaluation"
        idx = build_index(root, tier=tier, purpose=purpose, label_source=label_source)
        if tier != "threshold_calibration":
            idx["natural_state"] = idx["context"].map(lambda t: natural_state(t, threshold))
            idx = idx[idx["natural_state"] == "N1"].reset_index(drop=True)
        base = idx
    else:
        idx = build_external_index(root, label_source=label_source, threshold=threshold)
        idx = idx[idx["_present"]].drop(columns=["_present"]).reset_index(drop=True)
        base = idx[idx["natural_state"] == "N1"].reset_index(drop=True)
        base = base.rename(columns={"deid_patient_id": "subject_id", "study_key": "study_id"})
    out = {}
    for c in conditions:
        if c == "C0":
            out[c] = base
        elif c == "C1":
            out[c] = apply_c1(base)
        elif c == "C2":
            out[c] = apply_c2(base, seed=c2_seed)
    return out


def run(root: Path, *, site: str, tier: str, models: list[str], conditions: list[str],
        train_seed: int | None = None, c2_seed: int = 20260718, threshold: int = 3,
        num_workers: int = 3) -> list[str]:
    root = Path(root).resolve()
    settings = load_frozen_settings(root)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _seed_everything(SEED)
    torch.backends.cudnn.benchmark = bool(settings["optimization"].get("cudnn_benchmark", False))
    from transformers import BertTokenizer
    tok = BertTokenizer.from_pretrained(settings["text"]["pretraining"])
    max_len = settings["text"]["max_sequence_length"]
    bs = settings["optimization"]["batch_size"]

    todo = []
    for c in conditions:
        for m in models:
            p = rev_cache_path(root, site=site, tier=tier, model=m, cond=c, train_seed=train_seed,
                               c2_seed=c2_seed if c == "C2" else None, threshold=threshold)
            if not p.exists():
                todo.append((c, m, p))
    if not todo:
        print(f"[rev-infer] {site}/{tier}: all cached", file=sys.stderr)
        return []
    fr = frames(root, site, tier, threshold=threshold, c2_seed=c2_seed,
                conditions=tuple(sorted({c for c, _, _ in todo})))
    built, shas = _models(root, sorted({m for _, m, _ in todo}), train_seed, device)
    written = []
    for c, m, p in todo:
        frame = fr[c]
        model, needs_text = built[m]
        if site == "source":
            ds = C3EStudyImageDataset(frame, root / IMAGE_DIR, tok, max_len)
        else:
            f = frame.rename(columns={"subject_id": "deid_patient_id", "study_id": "study_key"})
            ds = CheXpertPlusDataset(f, root / EXT_IMAGE_DIR, tok, max_len)
        loader = DataLoader(ds, batch_size=bs, shuffle=False, num_workers=num_workers,
                            pin_memory=True, persistent_workers=False)
        t0 = time.time()
        print(f"[rev-infer] {site}/{tier} {c} {m} seed={train_seed or SEED} "
              f"c2seed={c2_seed if c == 'C2' else '-'}: {len(frame):,} images ...",
              file=sys.stderr, flush=True)
        probs, labels, masks = predict(model, loader, device, needs_text)
        sp, sy, sm, pats, studies = _aggregate(frame, site, probs, labels, masks)
        p.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(p, probabilities=sp, labels=sy, mask=sm, patients=pats, studies=studies,
                            meta=np.array([json.dumps({
                                "site": site, "tier": tier, "model": m, "condition": c,
                                "train_seed": train_seed or SEED,
                                "c2_seed": c2_seed if c == "C2" else None,
                                "threshold": threshold, "checkpoint": shas[m],
                                "studies": int(len(sp)), "revision": "R1-2026-10-06"})]))
        written.append(str(p.relative_to(root)))
        print(f"[rev-infer]   done in {time.time() - t0:.0f}s -> {len(sp):,} studies",
              file=sys.stderr, flush=True)
        torch.cuda.empty_cache()
    return written


def main(argv=None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Revision R1 study-keyed inference")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--site", choices=["source", "external"], required=True)
    ap.add_argument("--tier", default="prespecified_eval",
                    choices=["threshold_calibration", "prespecified_eval", "external"])
    ap.add_argument("--models", default="M1,M2,M3,M4")
    ap.add_argument("--conditions", default="C0,C1,C2")
    ap.add_argument("--train-seed", type=int, default=None)
    ap.add_argument("--c2-seed", type=int, default=20260718)
    ap.add_argument("--threshold", type=int, default=3)
    ap.add_argument("--num-workers", type=int, default=3)
    a = ap.parse_args(argv)
    if a.tier == "threshold_calibration" and a.conditions != "C0":
        print("calibration tier is scored under C0 only, as Stage 7 did", file=sys.stderr)
        return 2
    w = run(a.project_root, site=a.site, tier=a.tier, models=a.models.split(","),
            conditions=a.conditions.split(","), train_seed=a.train_seed, c2_seed=a.c2_seed,
            threshold=a.threshold, num_workers=a.num_workers)
    print(json.dumps({"written": w}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
