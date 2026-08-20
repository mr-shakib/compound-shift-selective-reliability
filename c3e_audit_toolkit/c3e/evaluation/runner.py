"""C3-E6 Stage 8: controlled context interventions on the confirmatory tier.

This is the first stage permitted to read the prespecified-eval tier. It scores
M1 through M4 under C0, C1 and C2, applies the Stage 7 thresholds unchanged, and
reports selective risk at the frozen coverages.

Nothing is selected here. Thresholds and abstention cutoffs are consumed from
the Stage 7 artifact, and the runner refuses to start if that artifact is
missing, because re-deriving them against this tier would convert a frozen
transfer into a refit.

Point estimates only. Intervals come from the patient-clustered bootstrap in the
confirmatory analysis; nothing here is a hypothesis test.
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

from ..calibration.policy import (TARGETS, aggregate_images_to_studies,
                                  hamming_error, selective_risk, study_confidence)
from ..calibration.runner import predict
from ..training.dataset import C3EStudyImageDataset, build_index
from ..training.models import M1ImageOnly, M2TextOnly, M3LateFusion, M4FeatureFusion
from ..calibration.runner import stage7_path as resolve_stage7
from ..training.runner import (CKPT_DIR, checkpoint_name, IMAGE_DIR, SEED, _available_ram_gb,
                               _seed_everything, load_frozen_settings,
                               scored_models, weighted_models)
from ..analysis.cache import checkpoint_digest, load as cache_load, save as cache_save
from .interventions import apply_c1, apply_c2, check_invariants, natural_state

STAGE = "C3-E6 Stage 8"
TITLE = "CONTEXT INTERVENTIONS ON THE CONFIRMATORY TIER"
OUTPUT_DIR = "results/c3e_mimic/stage8_interventions"
OUTPUT_DIR_S1 = "results/c3e_mimic/stage8_interventions_findings"
STAGE7 = "results/c3e_mimic/stage7_thresholds/stage7_thresholds.json"
STAGE7_S1 = "results/c3e_mimic/stage7_thresholds_findings/stage7_thresholds.json"

DECLARATIONS = (
    "STAGE 8 ONLY",
    "SOURCE-SITE CONFIRMATORY TIER",
    "THRESHOLDS CONSUMED FROZEN FROM STAGE 7",
    "NO THRESHOLD SELECTED OR REVISED HERE",
    "NO MODEL TRAINING",
    "NO EXTERNAL-SITE INFERENCE",
    "NO CROSS-SITE CLAIM",
    "POINT ESTIMATES ONLY, NO INTERVALS OR TESTS",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(model, path: Path, device):
    blob = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(blob["state_dict"])
    return model.to(device)


def run(*, project_root: str | Path, num_workers: int = 3,
        tier: str = "prespecified_eval",
        label_source: str = "impression",
        threshold: int = 3,
        seed: int | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    settings = load_frozen_settings(root)

    stage7_path = resolve_stage7(root, label_source, seed)
    if not stage7_path.exists():
        raise RuntimeError(
            f"missing {stage7_path}. Stage 8 consumes frozen thresholds and "
            "must not derive them against the confirmatory tier.")
    stage7 = json.loads(stage7_path.read_text())
    coverages = [c["target_coverage"] for c in stage7["coverage_table"]
                 if c["model"] == "M1"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _seed_everything(SEED)
    torch.backends.cudnn.benchmark = bool(settings["optimization"].get("cudnn_benchmark", False))

    print(f"{STAGE} — {TITLE}", file=sys.stderr)
    print(f"  protocol v{settings['protocol_version']}  thresholds from Stage 7 "
          f"(sha256 {sha256_file(stage7_path)[:16]}…)", file=sys.stderr, flush=True)

    print(f"  reading {tier} tier ...", file=sys.stderr, flush=True)
    index = build_index(root, tier=tier, purpose="confirmatory_evaluation",
                        label_source=label_source)

    # Interventions apply to N1 studies only: removing context that was never
    # present, or misaligning context that was already absent, tests nothing.
    index["natural_state"] = index["context"].map(
        lambda t: natural_state(t, threshold))
    states = index.groupby("natural_state")["study_id"].nunique().to_dict()
    c0 = index[index["natural_state"] == "N1"].reset_index(drop=True)
    print(f"  {tier}: {len(index):,} images, natural states "
          f"{ {k: int(v) for k, v in states.items()} }", file=sys.stderr)
    print(f"  N1 eligible for intervention: {len(c0):,} images, "
          f"{c0['study_id'].nunique():,} studies", file=sys.stderr, flush=True)

    c1, c2 = apply_c1(c0), apply_c2(c0)
    invariants = check_invariants(c0, c1, c2)
    print(f"  invariants ok; C2 self-assignments "
          f"{invariants['c2_studies_retaining_own_context']}", file=sys.stderr, flush=True)

    from transformers import BertTokenizer
    tokenizer = BertTokenizer.from_pretrained(settings["text"]["pretraining"])
    max_len = settings["text"]["max_sequence_length"]
    bs = settings["optimization"]["batch_size"]
    pin = _available_ram_gb() >= 6.0

    ckpt = root / CKPT_DIR
    scored = scored_models(seed)
    if seed is not None:
        print(f"  seed {seed}: scoring {', '.join(scored)} only; "
              "M3 needs an M2 replicate", file=sys.stderr, flush=True)
    shas = {mid: checkpoint_digest(ckpt / checkpoint_name(mid, seed))
            for mid in weighted_models(seed)}
    m1 = _load(M1ImageOnly(), ckpt / checkpoint_name("M1", seed), device)
    m4 = _load(M4FeatureFusion(), ckpt / checkpoint_name("M4", seed), device)
    built = {"M1": (m1, False), "M4": (m4, True)}
    if "M2" in scored:
        m2 = _load(M2TextOnly(), ckpt / checkpoint_name("M2", seed), device)
        # M3 has no weights of its own; its identity is that of its two components.
        shas["M3"] = hashlib.sha256((shas["M1"] + shas["M2"]).encode()).hexdigest()[:16]
        built["M2"] = (m2, True)
        built["M3"] = (M3LateFusion(m1, m2).to(device), True)
    specs = tuple((mid, *built[mid]) for mid in scored)

    rows: list[dict[str, Any]] = []
    image_only_check: dict[str, np.ndarray] = {}

    for cond, frame in (("C0", c0), ("C1", c1), ("C2", c2)):
        ds = C3EStudyImageDataset(frame, root / IMAGE_DIR, tokenizer, max_len)
        loader = DataLoader(ds, batch_size=bs, shuffle=False, num_workers=num_workers,
                            pin_memory=pin, persistent_workers=num_workers > 0)
        for mid, model, needs_text in specs:
            hit = cache_load(root, "source", mid, cond, checkpoint_sha=shas[mid],
                             label_source=label_source, threshold=threshold, seed=seed)
            if hit is not None:
                print(f"  {cond} · {mid} (cached)", file=sys.stderr, flush=True)
                sp, sy, sm = hit["probabilities"], hit["labels"], hit["mask"]
                if mid == "M1":
                    image_only_check[cond] = sp
            else:
                print(f"  {cond} · {mid} ...", file=sys.stderr, flush=True)
                probs, labels, masks = predict(model, loader, device, needs_text)

                agg = pd.DataFrame({"subject_id": frame["subject_id"].to_numpy(),
                                    "study_id": frame["study_id"].to_numpy()})
                for j, t in enumerate(TARGETS):
                    agg[t] = probs[:, j]
                    agg[t + "__label"] = np.where(masks[:, j] > 0, labels[:, j], np.nan)
                studies = aggregate_images_to_studies(agg)

                sp = studies[TARGETS].to_numpy()
                sy = studies[[t + "__label" for t in TARGETS]].to_numpy()
                sm = (~np.isnan(sy)).astype(float)
                sy = np.nan_to_num(sy)

                cache_save(root, "source", mid, cond, probabilities=sp, labels=sy,
                           mask=sm, patients=studies["subject_id"].to_numpy(),
                           checkpoint_sha=shas[mid], label_source=label_source,
                           threshold=threshold, seed=seed)
                if mid == "M1":
                    image_only_check[cond] = sp

            thr = np.array([stage7["models"][mid]["classification_thresholds"][t]
                            for t in TARGETS])
            errors = hamming_error((sp >= thr[None, :]).astype(float), sy, sm)
            conf = study_confidence(sp, "minimum")

            for cov in coverages:
                cutoff = stage7["models"][mid]["abstention_thresholds"][f"{cov:.2f}"]["abstention_threshold"]
                r = selective_risk(errors, conf, cutoff)
                rows.append({
                    "model": mid, "condition": cond, "target_coverage": cov,
                    "frozen_abstention_threshold": cutoff,
                    "realised_coverage": round(r["coverage"], 6),
                    "accepted_studies": r["accepted_studies"],
                    "total_studies": r["total_studies"],
                    "selective_hamming_error": round(r["selective_hamming_error"], 6),
                    "full_coverage_hamming_error": round(r["full_coverage_hamming_error"], 6),
                })

    # Registry invariant: image-only predictions cannot move across conditions.
    max_drift = max(float(np.abs(image_only_check["C0"] - image_only_check[c]).max())
                    for c in ("C1", "C2"))
    if max_drift > 1e-5:
        raise RuntimeError(
            f"M1 predictions differ across context conditions by {max_drift:.2e}; "
            "an image-only model must be invariant to the text intervention")
    print(f"  M1 invariance across conditions ok (max drift {max_drift:.2e})",
          file=sys.stderr, flush=True)

    return {
        "stage": STAGE, "title": TITLE, "status": "PASS",
        "declarations": list(DECLARATIONS),
        "protocol_version": settings["protocol_version"],
        "tier": tier, "label_source": label_source,
        "informativeness_threshold": threshold, "seed": seed,
        "cohort": {
            "images_in_tier": int(len(index)),
            "studies_in_tier": int(index["study_id"].nunique()),
            "patients_in_tier": int(index["subject_id"].nunique()),
            "natural_states_by_study": {k: int(v) for k, v in states.items()},
            "n1_images": int(len(c0)),
            "n1_studies": int(c0["study_id"].nunique()),
            "n1_patients": int(c0["subject_id"].nunique()),
        },
        "invariants": invariants,
        "m1_max_prediction_drift_across_conditions": max_drift,
        "threshold_source": {"path": str(stage7_path.relative_to(root)),
                             "sha256": sha256_file(stage7_path)},
        "results": rows,
        "compliance": {
            "model_training": False,
            "threshold_selection": False,
            "external_site_inference": False,
            "cross_site_claim": False,
            "intervals_or_tests_computed": False,
            "identifiers_emitted_to_results": False,
        },
        "environment": {"python": platform.python_version(),
                        "platform": f"{platform.system()}-{platform.machine()}",
                        "torch": torch.__version__},
    }


def _render_md(r: dict[str, Any]) -> str:
    c = r["cohort"]
    md = [f"# {STAGE} — Context Interventions", "",
          f"Status: **{r['status']}**  ·  protocol v{r['protocol_version']}  ·  tier `{r['tier']}`", ""]
    md += [f"- **{d}**" for d in DECLARATIONS]
    md += ["", "## Cohort", "",
           f"{c['images_in_tier']:,} images · {c['studies_in_tier']:,} studies · "
           f"{c['patients_in_tier']:,} patients.", "",
           f"Interventions apply to the {c['n1_studies']:,} N1 studies "
           f"({c['n1_images']:,} images, {c['n1_patients']:,} patients) whose context",
           "passes the frozen informativeness rule. Removing context that was never",
           "there would test nothing.", "",
           "## Selective Hamming error by condition", "",
           "Thresholds and abstention cutoffs are Stage 7 values, applied unchanged.", ""]
    for cov in sorted({row["target_coverage"] for row in r["results"]}, reverse=True):
        md += [f"### Target coverage {cov:.0%}", "",
               "| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |",
               "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for mid in scored_models(r.get("seed")):
            got = {row["condition"]: row["selective_hamming_error"]
                   for row in r["results"]
                   if row["model"] == mid and row["target_coverage"] == cov}
            md.append(f"| {mid} | {got['C0']:.4f} | {got['C1']:.4f} | {got['C2']:.4f} | "
                      f"{got['C1'] - got['C0']:+.4f} | {got['C2'] - got['C0']:+.4f} |")
        md.append("")
    md += ["## Invariants", "",
           f"- C2 studies retaining their own context: "
           f"**{r['invariants']['c2_studies_retaining_own_context']}**",
           f"- M1 maximum prediction drift across conditions: "
           f"**{r['m1_max_prediction_drift_across_conditions']:.2e}** "
           "(an image-only model must be invariant to a text intervention)",
           "- No forbidden report section entered any payload", "",
           "Point estimates only. Intervals and hypothesis tests belong to the",
           "confirmatory analysis and are not computed here.", ""]
    return "\n".join(md)


def write_outputs(root: Path, report: dict[str, Any]) -> None:
    base = (OUTPUT_DIR if report.get("label_source", "impression") == "impression"
            else OUTPUT_DIR_S1)
    t = report.get("informativeness_threshold", 3)
    sd = report.get("seed")
    out = root / (base if t == 3 else f"{base}_T{t}")
    if sd is not None:
        out = Path(str(out) + f"_seed{sd}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage8_interventions.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "stage8_interventions.md").write_text(_render_md(report), encoding="utf-8")

    fields = ["model", "condition", "target_coverage", "frozen_abstention_threshold",
              "realised_coverage", "accepted_studies", "total_studies",
              "selective_hamming_error", "full_coverage_hamming_error"]
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for row in report["results"]:
        w.writerow(row)
    (out / "stage8_results.csv").write_text(buf.getvalue(), encoding="utf-8")

    names = ["stage8_interventions.json", "stage8_interventions.md", "stage8_results.csv"]
    (out / "stage8_manifest.json").write_text(json.dumps({
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
    ap = argparse.ArgumentParser(description="Run C3-E6 Stage 8 context interventions")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--num-workers", type=int, default=3)
    ap.add_argument("--tier", default="prespecified_eval")
    ap.add_argument("--label-source", default="impression",
                    choices=["impression", "findings"])
    ap.add_argument("--threshold", type=int, default=3,
                    help="informativeness threshold; 3 is the preregistered primary")
    ap.add_argument("--seed", type=int, default=None,
                    help="replicate seed; omit for the primary models")
    args = ap.parse_args(argv)
    try:
        report = run(project_root=args.project_root, num_workers=args.num_workers,
                     tier=args.tier, label_source=args.label_source,
                     threshold=args.threshold, seed=args.seed)
        write_outputs(Path(args.project_root).resolve(), report)
    except Exception as exc:  # noqa: BLE001
        print(f"Stage 8 FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    primary = [r for r in report["results"] if r["target_coverage"] == 0.8]
    print(json.dumps({"stage": STAGE, "status": report["status"],
                      "cohort": report["cohort"], "primary_coverage": primary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
