"""Revision R1 runner: regenerate every revision artifact from verified inputs.

    python -m c3e.revision.runner            # all CPU analyses
    python -m c3e.revision.runner --only hypotheses,label_source

Inputs: the Stage 8/9b prediction caches (verified row-by-row against a
reconstruction of the cohorts), the frozen Stage 7 thresholds, the Stage 10
artifacts (reproduced exactly as a precondition), and the revision caches
written by ``c3e.revision.inference``. Outputs are aggregate-only and go to
``results/c3e_revision/``; a manifest records every artifact digest and an
identifier scan refuses to finish if a row-level value leaks.

Nothing here selects or revises a frozen threshold, and nothing is fitted on
external data. Every analysis here is post hoc (written 2026-10-06, after the
external results of 2026-08-07 were inspected) and is labelled as such.
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
import time
from typing import Any

import numpy as np
import pandas as pd

from .engine import frozen_policy, load_site

OUT = "results/c3e_revision"
STAGE = "C3-E6 Revision R1"
DECLARATIONS = (
    "REVISION R1 (2026-10-06): POST HOC, AFTER EXTERNAL RESULTS WERE INSPECTED",
    "FROZEN STAGE 7 THRESHOLDS CONSUMED UNCHANGED",
    "NO THRESHOLD, CUTOFF OR SCORE FITTED ON EXTERNAL DATA",
    "COMPARATOR SCORES FITTED ON THE SOURCE CALIBRATION TIER ONLY",
    "PATIENT-CLUSTERED BOOTSTRAP, 2000 REPLICATES, SEED 20260718, STAGE 10 DRAW ORDER",
    "ORIGINAL ESTIMATES RETAINED BESIDE CORRECTED ONES",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)
STAGE10 = {
    "primary": "results/c3e_cross_site/stage10_analysis/stage10_hypotheses.csv",
    "findings_S1": "results/c3e_cross_site/stage10_analysis_findings/stage10_hypotheses.csv",
    "T5": "results/c3e_cross_site/stage10_analysis_T5/stage10_hypotheses.csv",
    "T10": "results/c3e_cross_site/stage10_analysis_T10/stage10_hypotheses.csv",
    "seed20260719": "results/c3e_cross_site/stage10_analysis_seed20260719/stage10_hypotheses.csv",
}
RESTRICTED = re.compile(r"(?:patient|subject|study|image)\d{3,}|(?:^|[/\\])[ps]\d{5,}", re.IGNORECASE)


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: (f"{v:.10f}" if isinstance(v, float) and np.isfinite(v) else
                        (json.dumps(v) if isinstance(v, (list, dict)) else v)) for k, v in r.items()})
    path.write_text(buf.getvalue(), encoding="utf-8")


def _write_json(path: Path, obj: Any) -> None:
    def conv(o):
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, default=conv) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- analyses

def a_alignment(root: Path) -> dict[str, Any]:
    from .align import build_and_verify
    checks = []
    for site, ls, T, suf in [("source", "impression", 3, ""), ("source", "findings", 3, ""),
                             ("external", "impression", 3, ""), ("external", "findings", 3, ""),
                             ("source", "impression", 5, "__T5"), ("source", "impression", 10, "__T10"),
                             ("external", "impression", 5, "__T5"), ("external", "impression", 10, "__T10"),
                             ("source", "impression", 3, "__seed20260719"),
                             ("external", "impression", 3, "__seed20260719")]:
        _, chk = build_and_verify(root, site=site, label_source=ls, threshold=T, suffix=suf)
        chk["cache_suffix"] = suf
        checks.append(chk)
    return {"alignment_checks": checks}


def _family(root: Path, analysis: str, **kw):
    from .hypotheses import run_family
    if analysis == "seed20260719":
        src = load_site(root, "source", seed=20260719, models=("M1", "M4"))
        ext = load_site(root, "external", seed=20260719, models=("M1", "M4"))
        pol = frozen_policy(root, "impression", 20260719)
        return run_family(src, ext, pol, models=("M1", "M4"), multimodal=("M4",), **kw)
    if analysis == "findings_S1":
        src, ext = load_site(root, "source", label_source="findings"), \
            load_site(root, "external", label_source="findings")
        return run_family(src, ext, frozen_policy(root, "findings"), **kw)
    if analysis in ("T5", "T10"):
        T = int(analysis[1:])
        return run_family(load_site(root, "source", threshold=T), load_site(root, "external", threshold=T),
                          frozen_policy(root), **kw)
    cov = {"primary": 0.8, "coverage70": 0.7, "coverage90": 0.9}[analysis]
    return run_family(load_site(root, "source"), load_site(root, "external"),
                      frozen_policy(root, coverage=cov), **kw)


def a_hypotheses(root: Path) -> dict[str, Any]:
    rows, levels, covgap, repro = [], [], [], []
    plan = [("primary", v) for v in ("primary", "unmentioned_negative",
                                     "uncertain_positive", "uncertain_negative")]
    plan += [(a, "primary") for a in ("coverage70", "coverage90", "T5", "T10",
                                      "seed20260719", "findings_S1")]
    for analysis, variant in plan:
        t = time.time()
        fam = _family(root, analysis, variant=variant)
        for r in fam["contrasts"]:
            rows.append({"analysis": analysis, "label_variant": variant, **r})
        for r in fam["levels"]:
            levels.append({"analysis": analysis, "label_variant": variant, **r})
        for r in fam["coverage_gap"]:
            covgap.append({"analysis": analysis, "label_variant": variant, **r})
        print(f"  {analysis}/{variant}: {time.time() - t:.0f}s", file=sys.stderr, flush=True)
        if variant == "primary" and analysis in STAGE10:
            art = list(csv.DictReader(open(root / STAGE10[analysis])))
            mine = {}
            for r in fam["contrasts"]:
                if r["estimator"] != "original":
                    continue
                c = r["contrast"]
                if r["hypothesis"] == "H2":
                    c = f"interaction: (ext {c[-2:]}-C0) - (src {c[-2:]}-C0)"
                mine[(r["hypothesis"], r["model"], r["site"], c)] = r
            worst = 0.0
            for a in art:
                r = mine[(a["hypothesis"], a["model"], a["site"], a["contrast"])]
                for f in ("point_estimate", "ci_low", "ci_high"):
                    worst = max(worst, abs(round(r[f], 6) - float(a[f])))
            repro.append({"analysis": analysis, "stage10_rows": len(art),
                          "max_abs_difference": worst, "reproduced": worst <= 1.5e-6})
    if not all(r["reproduced"] for r in repro):
        raise RuntimeError(f"Stage 10 not reproduced: {repro}")
    return {"hypotheses": rows, "levels": levels, "coverage_gap": covgap, "stage10_reproduction": repro}


def a_pathology(root: Path) -> dict[str, Any]:
    """Pathology-specific contrasts (SAP: every metric is pathology-specific),
    with Holm across the five pathologies within each contrast family (the
    SAP's registered multiplicity rule). Selective risk per pathology is the
    error rate over labelled cells of that pathology among accepted studies;
    acceptance is still the frozen study-level policy."""
    from ..calibration.policy import TARGETS
    from ..analysis.bootstrap import holm_adjust
    est = tuple(f"pathology_{j}" for j in range(5))
    rows = []
    for analysis, variant in (("primary", "primary"), ("primary", "unmentioned_negative"),
                              ("findings_S1", "primary")):
        fam = _family(root, analysis, variant=variant, estimators=est)
        for r in fam["contrasts"]:
            j = int(r["estimator"].split("_")[1])
            rows.append({"analysis": analysis, "label_variant": variant, **r,
                         "pathology": TARGETS[j]})
    df = pd.DataFrame(rows)
    df["holm_p_across_pathologies"] = np.nan
    for _, g in df.groupby(["analysis", "label_variant", "hypothesis", "model", "site", "contrast"]):
        adj = holm_adjust({str(i): float(p) for i, p in zip(g.index, g["p_two_sided_bootstrap"])})
        for i, v in adj.items():
            df.loc[int(i), "holm_p_across_pathologies"] = v
    return {"pathology_contrasts": df.to_dict("records")}


def a_label_source(root: Path) -> dict[str, Any]:
    from . import label_source
    r = label_source.run(root)
    rows = []
    for name, c in r["configs"].items():
        for x in c["contrasts"]:
            rows.append({"config": name, "policy": c["policy"],
                         "source_cohort_studies": c["source_cohort_studies"],
                         "external_cohort_studies": c["external_cohort_studies"],
                         **{f"src_{k}": v for k, v in c["source_labels"].items()},
                         **{f"ext_{k}": v for k, v in c["external_labels"].items()},
                         "c2_realisation": c["c2_realisation"], **x})
    return {"label_source_contrasts": rows,
            "label_source_levels": [dict(config=n, **x) for n, c in r["configs"].items() for x in c["levels"]],
            "label_source_meta": {k: r[k] for k in ("factors", "external_decision_identity", "thresholds")}}


def a_label_audit(root: Path) -> dict[str, Any]:
    from .label_audit import audit
    r = audit(root)
    return {"label_audit_by_pathology": r["by_pathology"], "label_audit_by_study": r["by_study"],
            "label_agreement": r["agreement"]}


def a_selective(root: Path) -> dict[str, Any]:
    from . import selective as S
    src, ext, pol = load_site(root, "source"), load_site(root, "external"), frozen_policy(root)
    oc = []
    for v in ("primary", "unmentioned_negative"):
        oc += S.operating_characteristics(src, pol, variant=v) + S.operating_characteristics(ext, pol, variant=v)
    return {"failure_detection": S.failure_detection(src, pol) + S.failure_detection(ext, pol),
            "operating_characteristics": oc,
            "threshold_free": S.threshold_free(src, ext, pol) +
            S.threshold_free(src, ext, pol, score="threshold_margin"),
            "rc_curves": S.curves(src, pol) + S.curves(ext, pol)}


def a_context(root: Path) -> dict[str, Any]:
    from .context import decompose
    pol = frozen_policy(root)
    return {"context_decomposition": decompose(load_site(root, "source"), pol) +
            decompose(load_site(root, "external"), pol)}


def a_c2(root: Path) -> dict[str, Any]:
    from .c2_audit import audit
    from .inference import frames
    from .align import missing_external_images
    from ..external.dataset import build_external_index
    src = frames(root, "source", "prespecified_eval", conditions=("C0",))["C0"]
    out = [audit(src, site="source")]
    idx = build_external_index(root, label_source="impression", threshold=3)
    for cand in [None] + missing_external_images(root):
        i2 = idx.copy()
        if cand is not None:
            i2.loc[i2["path_to_image"] == cand, "_present"] = True
        i2 = i2[i2["_present"]].drop(columns=["_present"])
        b = i2[i2["natural_state"] == "N1"].reset_index(drop=True).rename(
            columns={"deid_patient_id": "subject_id", "study_key": "study_id"})
        if b["study_id"].nunique() == 132923:
            out.append(audit(b, site="external"))
            break
    return {"c2_audit": out}


def a_subgroups(root: Path) -> dict[str, Any]:
    from . import subgroups as G
    src, ext, pol = load_site(root, "source"), load_site(root, "external"), frozen_policy(root)
    d = G.demographic_analysis(ext, pol)
    return {"view_strata": G.view_analysis(src, ext, pol) +
            G.view_analysis(src, ext, pol, estimator="original"),
            "external_demographics": d["rows"], "external_demographic_disparity": d["disparity"]}


def a_comparators(root: Path) -> dict[str, Any]:
    from .comparators import evaluate
    from .stage7_check import check
    s7 = [check(root, m) for m in ("M1", "M2", "M3", "M4")]
    s7 += [check(root, m, 20260719, "results/c3e_mimic/stage7_thresholds_seed20260719/stage7_thresholds.json")
           for m in ("M1", "M4")]
    r = evaluate(root, load_site(root, "source"), load_site(root, "external"), frozen_policy(root))
    return {"stage7_reproduction": s7, "comparators": r["rows"],
            "comparator_ranking": r["ranking"], "comparator_fits": r["fits"]}


def a_calibration_uncertainty(root: Path) -> dict[str, Any]:
    from .calibration_uncertainty import run
    return {"calibration_uncertainty": run(root, load_site(root, "source"),
                                           load_site(root, "external"), replicates=200)}


def a_context_scan(root: Path) -> dict[str, Any]:
    from .context_scan import scan
    return {"context_scan": scan(root)}


def a_followup(root: Path) -> dict[str, Any]:
    from .followup import c2_permutations, m2m3_replicate
    rep = m2m3_replicate(root)
    out = {"followup_c2_permutations": c2_permutations(root),
           "followup_m2m3_status": [{"status": rep["status"],
                                     "missing_inputs": len(rep.get("missing", []))}]}
    if rep["status"] == "done":
        out["followup_m2m3_contrasts"] = rep["contrasts"]
        out["followup_m2m3_levels"] = rep["levels"]
        out["followup_m2m3_coverage_gap"] = rep["coverage_gap"]
        out["followup_m2m3_selection"] = rep["selection"]
    return out


def a_stage6_curves(root: Path) -> dict[str, Any]:
    """Training curves recovered per run; the committed Stage 6b curve for M2
    splices epochs 1-4 of the discarded empty-context run onto epochs 5-6 of
    the valid run, because its parser kept the first occurrence of each epoch."""
    from ..training.finalize import EPOCH_RE
    runs: dict[str, list[list[dict]]] = {}
    for log in ("logs/stage6_training.log", "logs/stage6_training_m2m4.log", "logs/stage6_seed2.log",
                "logs/revision_gpu_queue.log"):
        p = root / log
        if not p.exists():
            continue
        for line in p.read_text(errors="replace").replace("\r", "\n").splitlines():
            m = EPOCH_RE.search(line)
            if not m:
                continue
            mid, ep, tr, vl, va = m.groups()
            key = f"{mid}|{log}"
            lst = runs.setdefault(key, [])
            if not lst or int(ep) <= lst[-1][-1]["epoch"]:
                lst.append([])
            lst[-1].append({"epoch": int(ep), "train_loss": float(tr), "val_loss": float(vl),
                            "val_auroc_macro": float(va)})
    out = []
    for key, rs in runs.items():
        mid, log = key.split("|")
        for i, r in enumerate(rs):
            best = max(r, key=lambda e: e["val_auroc_macro"])
            out.append({"model": mid, "log": log, "run_index": i, "epochs": len(r),
                        "best_epoch": best["epoch"], "best_val_auroc_macro": best["val_auroc_macro"],
                        "curve": r})
    return {"stage6_runs_from_logs": out}


ANALYSES = {
    "alignment": a_alignment, "hypotheses": a_hypotheses, "pathology": a_pathology, "label_source": a_label_source,
    "label_audit": a_label_audit, "selective": a_selective, "context": a_context, "c2": a_c2,
    "subgroups": a_subgroups, "comparators": a_comparators, "stage6_curves": a_stage6_curves,
    "calibration_uncertainty": a_calibration_uncertainty, "followup": a_followup, "context_scan": a_context_scan,
}


def write(root: Path, results: dict[str, Any]) -> None:
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    json_only = {"comparator_fits", "label_source_meta", "stage6_runs_from_logs",
                 "followup_m2m3_selection"}
    for name, obj in results.items():
        if name not in json_only and isinstance(obj, list) and obj and isinstance(obj[0], dict) and not any(
                isinstance(v, list) and v and isinstance(v[0], dict) for v in obj[0].values()):
            _write_csv(out / f"{name}.csv", obj)
        else:
            _write_json(out / f"{name}.json", obj)
    root_text = str(root.resolve())
    for p in sorted(out.iterdir()):
        if p.is_file() and p.suffix in (".csv", ".json", ".md"):
            text = p.read_text(encoding="utf-8", errors="replace")
            if root_text in text:
                raise RuntimeError(f"absolute project path leaked into {p.name}")
            if RESTRICTED.search(text):
                raise RuntimeError(f"restricted row-level value detected in {p.name}")
    arts = [{"name": p.name, "byte_size": p.stat().st_size, "sha256": _sha(p)}
            for p in sorted(out.iterdir()) if p.is_file() and p.name != "manifest.json"]
    _write_json(out / "manifest.json", {
        "stage": STAGE, "declarations": list(DECLARATIONS), "artifacts": arts,
        "environment": {"python": platform.python_version(),
                        "platform": f"{platform.system()}-{platform.machine()}",
                        "numpy": np.__version__, "pandas": pd.__version__}})


def main(argv=None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description=STAGE)
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--only", default=",".join(ANALYSES))
    a = ap.parse_args(argv)
    root = a.project_root.resolve()
    results: dict[str, Any] = {}
    for name in a.only.split(","):
        t = time.time()
        print(f"[{STAGE}] {name} ...", file=sys.stderr, flush=True)
        results.update(ANALYSES[name](root))
        print(f"[{STAGE}] {name} done in {time.time() - t:.0f}s", file=sys.stderr, flush=True)
    write(root, results)
    print(json.dumps({"stage": STAGE, "written": sorted(results)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
