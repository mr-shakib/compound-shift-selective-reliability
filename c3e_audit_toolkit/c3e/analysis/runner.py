"""C3-E6 Stage 10: the confirmatory analysis.

Reads the cached per-study predictions from both sites, computes the
preregistered contrasts, and applies the frozen decision rule. Nothing is
inferred that was not specified in the hypothesis registry before any of these
numbers existed.

The four hypotheses:

  H1  selective policy transport failure
      external C0 minus source C0, unpaired across sites.
  H2  compound context interaction
      (external C1 minus C0) minus (source C1 minus C0); paired within each
      site, unpaired between them.
  H3  multimodal vulnerability versus image-only
      the transfer gap of a multimodal model minus that of the image-only
      control.
  H4  context conflict not better than absence
      C2 minus C1 within site, paired.

Materiality is 0.02 absolute and a hypothesis is confirmed only when its
interval excludes zero *and* the point estimate reaches it. Per-pathology
secondaries carry Holm correction; the aggregate primary does not.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys
from typing import Any

import numpy as np

from ..calibration.policy import TARGETS, hamming_error, study_confidence
from .bootstrap import (BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED, CI_LEVEL,
                        MATERIALITY, bootstrap_pvalue, coverage_drift, decide,
                        holm_adjust, independent_bootstrap, paired_bootstrap,
                        percentile_ci, selective_error)
from ..training.runner import checkpoint_name
from .cache import cache_path, checkpoint_digest, load as cache_load

STAGE = "C3-E6 Stage 10"
TITLE = "CONFIRMATORY ANALYSIS"
OUTPUT_DIR = "results/c3e_cross_site/stage10_analysis"
OUTPUT_DIR_S1 = "results/c3e_cross_site/stage10_analysis_findings"
STAGE7_SEED = "results/c3e_mimic/stage7_thresholds_seed{seed}/stage7_thresholds.json"
STAGE7 = "results/c3e_mimic/stage7_thresholds/stage7_thresholds.json"
STAGE7_S1 = "results/c3e_mimic/stage7_thresholds_findings/stage7_thresholds.json"
CKPT_DIR = "data/models/c3e"

DECLARATIONS = (
    "STAGE 10 ONLY",
    "CONFIRMATORY ANALYSIS",
    "CONTRASTS AND DECISION RULE PRESPECIFIED BEFORE THESE NUMBERS EXISTED",
    "THRESHOLDS CONSUMED FROZEN FROM STAGE 7",
    "NO MODEL TRAINING",
    "NO THRESHOLD SELECTION OR REVISION",
    "PATIENT-CLUSTERED BOOTSTRAP, 2000 REPLICATES, SEED 20260718",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)

MULTIMODAL = ("M3", "M4")
IMAGE_ONLY = "M1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_all(root: Path, stage7: dict[str, Any],
             label_source: str = "impression",
             threshold: int = 3,
             seed: int | None = None) -> dict[tuple[str, str, str], dict]:
    """Load every cached pass and derive per-study error and confidence."""
    ckpt = root / CKPT_DIR
    shas = {m: checkpoint_digest(ckpt / checkpoint_name(m, seed))
            for m in ("M1", "M2", "M4")}
    shas["M3"] = hashlib.sha256((shas["M1"] + shas["M2"]).encode()).hexdigest()[:16]

    models = ("M1", "M2", "M3", "M4") if seed is None else ("M1", "M4")
    if seed is not None:
        # M3 averages M1 and M2, and no M2 replicate exists. Building it from a
        # replicate M1 and the primary M2 would mix seeds inside one model.
        print(f"  seed {seed}: scoring M1 and M4 only; M3 needs an M2 replicate",
              file=sys.stderr, flush=True)

    out: dict[tuple[str, str, str], dict] = {}
    for site in ("source", "external"):
        for mid in models:
            thr = np.array([stage7["models"][mid]["classification_thresholds"][t]
                            for t in TARGETS])
            for cond in ("C0", "C1", "C2"):
                hit = cache_load(root, site, mid, cond, checkpoint_sha=shas[mid],
                                 label_source=label_source, threshold=threshold,
                                 seed=seed)
                if hit is None:
                    raise RuntimeError(
                        f"missing cached predictions for {site}/{mid}/{cond}. "
                        "Run the evaluation stages first; the analysis must not "
                        "re-run inference to produce an interval.")
                sp = hit["probabilities"]
                pred = (sp >= thr[None, :]).astype(float)
                out[(site, mid, cond)] = {
                    "errors": hamming_error(pred, hit["labels"], hit["mask"]),
                    "confidence": study_confidence(sp, "minimum"),
                    "patients": hit["patients"],
                    "probabilities": sp,
                    "labels": hit["labels"],
                    "mask": hit["mask"],
                }
    return out


def _cut(stage7: dict, mid: str, cov: float) -> float:
    return stage7["models"][mid]["abstention_thresholds"][f"{cov:.2f}"]["abstention_threshold"]


def analyse(root: Path, *, replicates: int = BOOTSTRAP_REPLICATES,
            coverage: float = 0.8,
            label_source: str = "impression",
            threshold: int = 3,
            seed: int | None = None) -> dict[str, Any]:
    stage7_path = root / (STAGE7_SEED.format(seed=seed) if seed is not None
                          else (STAGE7 if label_source == "impression" else STAGE7_S1))
    stage7 = json.loads(stage7_path.read_text())
    data = load_all(root, stage7, label_source, threshold, seed)

    results: list[dict[str, Any]] = []
    per_pathology_p: dict[str, float] = {}

    def site_arrays(site: str, mid: str) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        pats = data[(site, mid, "C0")]["patients"]
        vals = {}
        for cond in ("C0", "C1", "C2"):
            vals[f"e_{cond}"] = data[(site, mid, cond)]["errors"]
            vals[f"c_{cond}"] = data[(site, mid, cond)]["confidence"]
        return pats, vals

    # ---- H1: external C0 minus source C0, unpaired across sites --------------
    h1_models = MULTIMODAL + (IMAGE_ONLY, "M2") if seed is None else ("M4", IMAGE_ONLY)
    for mid in h1_models:
        cut = _cut(stage7, mid, coverage)
        ps, vs = site_arrays("source", mid)
        pe, ve = site_arrays("external", mid)
        stat = lambda a, b: (selective_error(b["e_C0"], b["c_C0"], cut)
                             - selective_error(a["e_C0"], a["c_C0"], cut))
        draws = independent_bootstrap(ps, vs, pe, ve, stat, replicates=replicates)
        point = stat(vs, ve)
        lo, hi = percentile_ci(draws)
        d = decide(point, lo, hi)
        d.update({"hypothesis": "H1", "model": mid,
                  "contrast": "external C0 - source C0",
                  "confirmatory": mid in MULTIMODAL})
        results.append(d)

    # ---- H2: interaction, paired within site, unpaired between ---------------
    for mid in (MULTIMODAL if seed is None else ("M4",)):
        cut = _cut(stage7, mid, coverage)
        ps, vs = site_arrays("source", mid)
        pe, ve = site_arrays("external", mid)
        for cond in ("C1", "C2"):
            def stat(a, b, cond=cond):
                src = (selective_error(a[f"e_{cond}"], a[f"c_{cond}"], cut)
                       - selective_error(a["e_C0"], a["c_C0"], cut))
                ext = (selective_error(b[f"e_{cond}"], b[f"c_{cond}"], cut)
                       - selective_error(b["e_C0"], b["c_C0"], cut))
                return ext - src
            draws = independent_bootstrap(ps, vs, pe, ve, stat, replicates=replicates)
            point = stat(vs, ve)
            lo, hi = percentile_ci(draws)
            d = decide(point, lo, hi)
            d.update({"hypothesis": "H2", "model": mid,
                      "contrast": f"interaction: (ext {cond}-C0) - (src {cond}-C0)",
                      "confirmatory": True})
            results.append(d)

    # ---- H3: multimodal transfer gap minus image-only transfer gap -----------
    for mid in (MULTIMODAL if seed is None else ("M4",)):
        cut_mm, cut_im = _cut(stage7, mid, coverage), _cut(stage7, IMAGE_ONLY, coverage)
        ps_mm, vs_mm = site_arrays("source", mid)
        pe_mm, ve_mm = site_arrays("external", mid)
        ps_im, vs_im = site_arrays("source", IMAGE_ONLY)
        pe_im, ve_im = site_arrays("external", IMAGE_ONLY)

        # Patients are shared within a site across models, so the two models are
        # resampled together: the contrast is between models on the same draw.
        def stat(a, b):
            gap_mm = (selective_error(b["e_C0_mm"], b["c_C0_mm"], cut_mm)
                      - selective_error(a["e_C0_mm"], a["c_C0_mm"], cut_mm))
            gap_im = (selective_error(b["e_C0_im"], b["c_C0_im"], cut_im)
                      - selective_error(a["e_C0_im"], a["c_C0_im"], cut_im))
            return gap_mm - gap_im
        vs = {"e_C0_mm": vs_mm["e_C0"], "c_C0_mm": vs_mm["c_C0"],
              "e_C0_im": vs_im["e_C0"], "c_C0_im": vs_im["c_C0"]}
        ve = {"e_C0_mm": ve_mm["e_C0"], "c_C0_mm": ve_mm["c_C0"],
              "e_C0_im": ve_im["e_C0"], "c_C0_im": ve_im["c_C0"]}
        draws = independent_bootstrap(ps_mm, vs, pe_mm, ve, stat, replicates=replicates)
        point = stat(vs, ve)
        lo, hi = percentile_ci(draws)
        d = decide(point, lo, hi)
        d.update({"hypothesis": "H3", "model": mid,
                  "contrast": f"transfer gap {mid} - transfer gap {IMAGE_ONLY}",
                  "confirmatory": True})
        results.append(d)

    # ---- H4: C2 minus C1 within site, paired --------------------------------
    for site in ("source", "external"):
        for mid in (MULTIMODAL if seed is None else ("M4",)):
            cut = _cut(stage7, mid, coverage)
            pats, vals = site_arrays(site, mid)
            stat = lambda v: (selective_error(v["e_C2"], v["c_C2"], cut)
                              - selective_error(v["e_C1"], v["c_C1"], cut))
            draws = paired_bootstrap(pats, vals, stat, replicates=replicates)
            point = stat(vals)
            lo, hi = percentile_ci(draws)
            d = decide(point, lo, hi, direction="greater_than_or_equal_zero")
            d.update({"hypothesis": "H4", "model": mid, "site": site,
                      "contrast": "C2 - C1", "confirmatory": False})
            results.append(d)
            per_pathology_p[f"H4_{site}_{mid}"] = bootstrap_pvalue(draws)

    # ---- coverage drift ------------------------------------------------------
    drift_rows = []
    for site in ("source", "external"):
        for mid in ("M1", "M2", "M3", "M4"):
            cut = _cut(stage7, mid, coverage)
            for cond in ("C0", "C1", "C2"):
                conf = data[(site, mid, cond)]["confidence"]
                realised = float((conf >= cut).mean())
                row = coverage_drift(realised, coverage)
                row.update({"site": site, "model": mid, "condition": cond})
                drift_rows.append(row)

    return {
        "stage": STAGE, "title": TITLE, "status": "PASS",
        "declarations": list(DECLARATIONS),
        "label_source": label_source,
        "informativeness_threshold": threshold, "seed": seed,
        "settings": {"replicates": replicates, "seed": BOOTSTRAP_SEED,
                     "ci_level": CI_LEVEL, "materiality": MATERIALITY,
                     "coverage": coverage, "resampling_unit": "patient"},
        "threshold_source": {"path": STAGE7, "sha256": sha256_file(stage7_path)},
        "hypotheses": results,
        "holm_adjusted_secondary": holm_adjust(per_pathology_p),
        "coverage_drift": drift_rows,
        "compliance": {"model_training": False, "threshold_selection": False,
                       "inference_rerun_for_intervals": False,
                       "identifiers_emitted_to_results": False},
        "environment": {"python": platform.python_version(),
                        "platform": f"{platform.system()}-{platform.machine()}"},
    }


def _render_md(r: dict[str, Any]) -> str:
    s = r["settings"]
    md = [f"# {STAGE} — Confirmatory Analysis", "",
          f"Status: **{r['status']}**", ""]
    md += [f"- **{d}**" for d in DECLARATIONS]
    md += ["", f"Patient-clustered bootstrap, {s['replicates']:,} replicates, seed "
           f"{s['seed']}, {s['ci_level']:.0%} percentile intervals, coverage "
           f"{s['coverage']:.0%}. A hypothesis is confirmed only when its interval "
           f"excludes zero **and** the point estimate reaches {s['materiality']}.", "",
           "| H | model | contrast | estimate | 95% CI | excl. 0 | supports dir. | material | verdict |",
           "| --- | --- | --- | ---: | :---: | :---: | :---: | :---: | :---: |"]
    for h in r["hypotheses"]:
        site = f" [{h['site']}]" if "site" in h else ""
        md.append(
            f"| {h['hypothesis']} | {h['model']}{site} | {h['contrast']} | "
            f"{h['point_estimate']:+.4f} | "
            f"({h['ci_low']:+.4f}, {h['ci_high']:+.4f}) | "
            f"{'yes' if h['ci_excludes_zero'] else 'no'} | "
            f"{'yes' if h['ci_supports_direction'] else 'no'} | "
            f"{'yes' if h['reaches_materiality'] else 'no'} | "
            f"**{'CONFIRMED' if h['confirmed'] else ('REVERSED' if h.get('reversed_at_materiality') else 'not confirmed')}** |")
    md += ["", "## Coverage drift", "",
           f"A drift of {r['coverage_drift'][0]['threshold']} from target is "
           "prespecified as material.", "",
           "| site | model | condition | realised | drift | material |",
           "| --- | --- | --- | ---: | ---: | :---: |"]
    for d in r["coverage_drift"]:
        md.append(f"| {d['site']} | {d['model']} | {d['condition']} | "
                  f"{d['realised_coverage']:.1%} | {d['drift']:+.4f} | "
                  f"{'**yes**' if d['material'] else 'no'} |")
    md.append("")
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
    (out / "stage10_analysis.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "stage10_analysis.md").write_text(_render_md(report), encoding="utf-8")

    buf = io.StringIO(newline="")
    fields = ["hypothesis", "model", "site", "contrast", "point_estimate",
              "ci_low", "ci_high", "ci_excludes_zero", "ci_supports_direction",
              "reaches_materiality", "confirmed", "reversed_at_materiality",
              "confirmatory"]
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for h in report["hypotheses"]:
        w.writerow(h)
    (out / "stage10_hypotheses.csv").write_text(buf.getvalue(), encoding="utf-8")

    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=["site", "model", "condition",
                                        "target_coverage", "realised_coverage",
                                        "drift", "material"],
                       lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for d in report["coverage_drift"]:
        w.writerow(d)
    (out / "stage10_coverage_drift.csv").write_text(buf.getvalue(), encoding="utf-8")

    names = ["stage10_analysis.json", "stage10_analysis.md",
             "stage10_hypotheses.csv", "stage10_coverage_drift.csv"]
    (out / "stage10_manifest.json").write_text(json.dumps({
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
    ap = argparse.ArgumentParser(description="Run C3-E6 Stage 10 confirmatory analysis")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--replicates", type=int, default=BOOTSTRAP_REPLICATES)
    ap.add_argument("--coverage", type=float, default=0.8)
    ap.add_argument("--label-source", default="impression",
                    choices=["impression", "findings"])
    ap.add_argument("--threshold", type=int, default=3,
                    help="informativeness threshold; 3 is the preregistered primary")
    ap.add_argument("--seed", type=int, default=None,
                    help="replicate seed; omit for the primary models")
    args = ap.parse_args(argv)
    try:
        print(f"{STAGE} — {TITLE}", file=sys.stderr)
        print(f"  {args.replicates:,} replicates, seed {BOOTSTRAP_SEED}, "
              f"coverage {args.coverage:.0%}", file=sys.stderr, flush=True)
        report = analyse(Path(args.project_root).resolve(),
                         replicates=args.replicates, coverage=args.coverage,
                         label_source=args.label_source, threshold=args.threshold, seed=args.seed)
        write_outputs(Path(args.project_root).resolve(), report)
    except Exception as exc:  # noqa: BLE001
        print(f"{STAGE} FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"stage": STAGE, "status": report["status"],
                      "hypotheses": report["hypotheses"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
