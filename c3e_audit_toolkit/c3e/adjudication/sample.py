"""Stratified sample for the blinded expert adjudication.

Frames are the primary cohorts (source evaluation tier; external N1 cohort,
C0). Per site, studies fall into eight strata: at least one labelled target
or none (primary report labels) x accepted or deferred by M4 at the frozen
policy x M4 calls any target positive or none. The protocol allocates the
per-site sample as 50% accepted-labelled, 25% accepted-label-less and 25%
deferred; within each group, strata receive shares proportional to their
frame sizes. Sampling is without replacement within strata (seed 20261006),
and each study carries its inclusion probability for Horvitz-Thompson
weighting.

Two further item sets are drawn and analysed separately, never weighted into
the estimates: all CheXpert validation studies (three-radiologist consensus
labels, a hidden check on reader accuracy), and practice studies from the
model-train tier for the calibration session.

    python -m c3e.adjudication.sample --dry-run   # stratum sizes only
    python -m c3e.adjudication.sample             # writes the sample (restricted)
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sys
from typing import Any

import numpy as np
import pandas as pd

from ..external.dataset import build_external_index
from ..revision.engine import frozen_policy, labels_from_raw, load_site
from ..revision.estimators import decisions
from ..training.dataset import build_index

SEED = 20261006
PER_SITE = 600
SHARES = {"accepted_labelled": 0.50, "accepted_label_less": 0.25, "deferred": 0.25}
PRACTICE = 30
MODEL = "M4"
OUT_DATA = "data/adjudication"
OUT_RESULTS = "results/c3e_adjudication"


def strata(labelled: np.ndarray, accepted: np.ndarray, positive: np.ndarray) -> np.ndarray:
    return np.array([f"L{int(l)}A{int(a)}P{int(p)}" for l, a, p in zip(labelled, accepted, positive)])


def group_of(stratum: str) -> str:
    if stratum[3] == "0":
        return "deferred"
    return "accepted_labelled" if stratum[1] == "1" else "accepted_label_less"


def proportional(target: int, sizes: dict[str, int]) -> dict[str, int]:
    """Split ``target`` across strata in proportion to their sizes.

    Largest-remainder rounding keeps the total exact. A stratum never receives
    more than it holds; its excess goes to the others in the same proportion.
    """
    alloc = {s: 0 for s in sizes}
    open_ = {s for s, n in sizes.items() if n > 0}
    remaining = min(target, sum(sizes.values()))
    while remaining > 0 and open_:
        tot = sum(sizes[s] for s in open_)
        raw = {s: remaining * sizes[s] / tot for s in open_}
        add = {s: int(np.floor(raw[s])) for s in open_}
        extra = remaining - sum(add.values())
        for s in sorted(open_, key=lambda s: (raw[s] - add[s], sizes[s], s), reverse=True)[:extra]:
            add[s] += 1
        for s in sorted(open_):
            take = min(add[s], sizes[s] - alloc[s])
            alloc[s] += take
            remaining -= take
            if alloc[s] >= sizes[s]:
                open_.discard(s)
    return alloc


def allocate(sizes: dict[str, int], per_site: int = PER_SITE, shares=SHARES) -> dict[str, int]:
    """Per-stratum sample sizes: the protocol's group shares, then proportional within group."""
    out = {s: 0 for s in sizes}
    for g, share in shares.items():
        members = {s: n for s, n in sizes.items() if group_of(s) == g}
        out.update(proportional(int(round(per_site * share)), members))
    return out


def frame(root: Path, site: str) -> pd.DataFrame:
    s = load_site(root, site, models=(MODEL,), conditions=("C0",))
    pol = frozen_policy(root)
    p = s.probs[(MODEL, "C0")]
    lab, msk = labels_from_raw(s.raw)
    key = "study_id" if site == "source" else "study_key"
    return pd.DataFrame({"site": site, "study": s.cohort[key].astype(str).to_numpy(),
                         "patient": s.cohort["patient"].astype(str).to_numpy(),
                         "stratum": strata(msk.sum(1) > 0, pol.accepted(MODEL, p),
                                           decisions(p, pol.thresholds[MODEL]).any(1))})


def images(root: Path, site: str, studies: set[str]) -> dict[str, list[str]]:
    if site == "source":
        idx = build_index(root, tier="prespecified_eval", purpose="confirmatory_evaluation")
        idx = idx.assign(study=idx["study_id"].astype(str))
        col = "image_path"
    else:
        idx = build_external_index(root)
        idx = idx[idx["_present"]].assign(study=lambda d: d["study_key"].astype(str))
        col = "path_to_image"
    idx = idx[idx.study.isin(studies)]
    return idx.groupby("study")[col].apply(lambda x: sorted(x.astype(str))).to_dict()


def draw(fr: pd.DataFrame, alloc: dict[str, int], rng: np.random.Generator) -> pd.DataFrame:
    parts = []
    for s, n in sorted(alloc.items()):
        pool = fr[fr.stratum == s]
        if n == 0:
            continue
        pick = pool.iloc[np.sort(rng.choice(len(pool), size=n, replace=False))]
        parts.append(pick.assign(inclusion_prob=n / len(pool), item_set="estimation"))
    return pd.concat(parts, ignore_index=True)


def run(root: Path, *, dry_run: bool) -> dict[str, Any]:
    root = Path(root)
    rng = np.random.default_rng(SEED)
    summary, samples = [], []
    for site in ("source", "external"):
        fr = frame(root, site)
        sizes = fr.stratum.value_counts().to_dict()
        alloc = allocate(sizes)
        for s in sorted(sizes):
            summary.append({"site": site, "stratum": s, "group": group_of(s), "frame_studies": int(sizes[s]),
                            "sampled": int(alloc[s]),
                            "inclusion_prob": alloc[s] / sizes[s] if sizes[s] else float("nan")})
        if not dry_run:
            samples.append(draw(fr, alloc, rng))
    if dry_run:
        return {"summary": summary}

    est = pd.concat(samples, ignore_index=True)
    # Reader-accuracy items: every CheXpert validation study with an image on disk.
    ext_idx = build_external_index(root)
    valid = ext_idx[ext_idx["_present"] & ext_idx["study_key"].str.startswith("valid/")]
    qc = pd.DataFrame({"site": "external", "study": sorted(valid.study_key.unique()), "patient": "",
                       "stratum": "QC", "inclusion_prob": np.nan, "item_set": "reader_accuracy"})
    # Practice items: model-train tier, outside both frames; discarded after the session.
    tr = build_index(root, tier="model_train", purpose="training")
    pr_studies = sorted(tr.study_id.astype(str).unique())
    pr = pd.DataFrame({"site": "source", "study": [pr_studies[i] for i in
                                                   sorted(rng.choice(len(pr_studies), PRACTICE, replace=False))],
                       "patient": "", "stratum": "PRACTICE", "inclusion_prob": np.nan, "item_set": "practice"})
    items = pd.concat([est, qc, pr], ignore_index=True)

    paths = images(root, "source", set(items[items.site == "source"].study))
    tr_paths = tr.assign(study=tr.study_id.astype(str)).groupby("study")["image_path"].apply(list).to_dict()
    paths.update({k: v for k, v in tr_paths.items() if k in set(pr.study)})
    paths.update(images(root, "external", set(items[items.site == "external"].study)))
    items["images"] = [json.dumps(paths.get(s, [])) for s in items.study]
    if (items["images"] == "[]").any():
        raise RuntimeError("a sampled study has no image on disk")
    items.insert(0, "item_id", [secrets.token_hex(6) for _ in range(len(items))])

    out = root / OUT_DATA
    out.mkdir(parents=True, exist_ok=True)
    sample_path = out / "sample_v1.csv"
    if sample_path.exists():
        raise FileExistsError(f"{sample_path} exists; the sample is frozen once drawn")
    items.to_csv(sample_path, index=False)
    # Reading order: practice first, then everything else shuffled per reader.
    for reader in ("A", "B"):
        order = items[items.item_set != "practice"].item_id.to_numpy().copy()
        np.random.default_rng(SEED + ord(reader)).shuffle(order)
        lead = items[items.item_set == "practice"].item_id.tolist()
        pd.DataFrame({"position": range(1, len(lead) + len(order) + 1),
                      "item_id": lead + order.tolist()}).to_csv(out / f"order_reader_{reader}.csv", index=False)
    digest = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    return {"summary": summary, "sha256": digest,
            "counts": items.groupby(["item_set", "site"]).size().rename("studies").reset_index()
            .to_dict("records")}


def main(argv=None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Expert adjudication: stratified sample")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--dry-run", action="store_true", help="report stratum sizes and allocation only")
    a = ap.parse_args(argv)
    root = a.project_root.resolve()
    r = run(root, dry_run=a.dry_run)
    res = root / OUT_RESULTS
    res.mkdir(parents=True, exist_ok=True)
    name = "sample_allocation_dry_run.csv" if a.dry_run else "sample_allocation.csv"
    pd.DataFrame(r["summary"]).to_csv(res / name, index=False)
    if not a.dry_run:
        (res / "sample_manifest.json").write_text(json.dumps(
            {"seed": SEED, "per_site": PER_SITE, "shares": SHARES, "model_of_record": MODEL,
             "sample_sha256": r["sha256"], "counts": r["counts"]}, indent=1) + "\n")
    print(pd.DataFrame(r["summary"]).to_string(index=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
