"""Recover study identity for the cached per-study predictions.

The Stage 8 and 9b caches store probabilities, labels, masks and patient
identifiers in a deterministic row order, but not the study identifier. Label
-source, view and subgroup analyses need that identifier, so it is recovered by
replaying the cohort construction through the *same* functions the stages used
(``build_index`` / ``build_external_index``, ``natural_state``, the same
groupby ordering) without opening any image. The reconstruction is then
verified against the cache -- patients, observed labels and masks must match
exactly -- and refused otherwise.

Outputs are row-level and contain identifiers, so they are written only under
the gitignored ``data/revision/`` tree.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..calibration.policy import TARGETS
from ..evaluation.interventions import natural_state
from ..external.dataset import PARQUET, build_external_index
from ..training.dataset import build_index

ALIGN_DIR = "data/revision/alignment"


class AlignmentError(RuntimeError):
    """The reconstructed cohort does not match the cache it claims to describe."""


def _label_category(raw: pd.DataFrame) -> pd.DataFrame:
    """Per-cell category: pos / neg / unc / unm (unmentioned)."""
    out = pd.DataFrame(index=raw.index)
    for t in TARGETS:
        v = raw[t]
        out[t] = np.select([v == 1.0, v == 0.0, v == -1.0], ["pos", "neg", "unc"], "unm")
    return out


def source_cohort(root: Path, *, label_source: str = "impression", threshold: int = 3,
                  tier: str = "prespecified_eval") -> pd.DataFrame:
    """Study-level source cohort in Stage 8 cache row order."""
    purpose = "calibration" if tier == "threshold_calibration" else "confirmatory_evaluation"
    idx = build_index(root, tier=tier, purpose=purpose, label_source=label_source)
    idx["natural_state"] = idx["context"].map(lambda t: natural_state(t, threshold))
    if tier != "threshold_calibration":
        idx = idx[idx["natural_state"] == "N1"]
    idx = idx.copy()
    idx["dicom_id"] = idx["image_path"].map(lambda p: Path(p).stem)

    meta = pd.read_csv(Path(root) / "data/mimic/metadata/mimic-cxr-2.0.0-metadata.csv.gz",
                       usecols=["dicom_id", "ViewPosition"])
    idx = idx.merge(meta, on="dicom_id", how="left")

    g = idx.groupby(["subject_id", "study_id"], sort=True)
    studies = g.agg(n_images=("image_path", "size"),
                    views=("ViewPosition", lambda s: "|".join(sorted(set(map(str, s)))))
                    ).reset_index()
    first = g[TARGETS].first().reset_index()   # labels are study-level at the source
    studies = studies.merge(first, on=["subject_id", "study_id"], how="left")
    studies["site"] = "source"
    studies["study_key"] = studies["study_id"].astype(str)
    studies["patient"] = studies["subject_id"].astype(str)
    return studies


def external_cohort(root: Path, *, label_source: str = "impression",
                    threshold: int = 3,
                    treat_as_present: frozenset[str] = frozenset()) -> pd.DataFrame:
    """Study-level external cohort in Stage 9b cache row order.

    ``treat_as_present`` names images that were on disk when the primary run
    was made and have since been lost (the seed-replicate run records one such
    image). Only a path whose inclusion reproduces the cache exactly is used.
    """
    idx = build_external_index(root, label_source=label_source, threshold=threshold)
    if treat_as_present:
        idx.loc[idx["path_to_image"].isin(treat_as_present), "_present"] = True
    idx = idx[idx["_present"]].drop(columns=["_present"])
    idx = idx[idx["natural_state"] == "N1"].reset_index(drop=True)

    demo = pd.read_parquet(Path(root) / PARQUET, columns=[
        "path_to_image", "ap_pa", "age", "sex", "race", "ethnicity", "insurance_type"])
    idx = idx.merge(demo, on="path_to_image", how="left")

    # Mirror _aggregate: observed labels are the first non-null 0/1 value.
    obs = idx[TARGETS].where(idx[TARGETS].isin([0.0, 1.0]))
    unc = (idx[TARGETS] == -1.0)
    work = pd.concat([idx[["study_key", "deid_patient_id", "ap_pa", "age", "sex", "race",
                           "ethnicity", "insurance_type"]],
                      obs.add_suffix("__obs"), unc.add_suffix("__unc")], axis=1)
    g = work.groupby("study_key", sort=True)
    agg = {"deid_patient_id": "first", "age": "first", "sex": "first", "race": "first",
           "ethnicity": "first", "insurance_type": "first"}
    agg.update({t + "__obs": "first" for t in TARGETS})
    agg.update({t + "__unc": "any" for t in TARGETS})
    studies = g.agg(agg)
    studies["n_images"] = g.size()
    studies["views"] = g["ap_pa"].agg(lambda s: "|".join(sorted(set(map(str, s)))))
    studies = studies.reset_index()
    for t in TARGETS:
        studies[t] = np.where(studies[t + "__obs"].notna(), studies[t + "__obs"],
                              np.where(studies[t + "__unc"], -1.0, np.nan))
    studies = studies.drop(columns=[c for c in studies.columns if c.endswith(("__obs", "__unc"))])
    studies["site"] = "external"
    studies["patient"] = studies["deid_patient_id"].astype(str)
    return studies


def verify_against_cache(cohort: pd.DataFrame, cache: dict) -> dict[str, object]:
    """Exact agreement of patients, observed labels and masks, or raise."""
    pats = np.asarray(cache["patients"]).astype(str)
    if len(pats) != len(cohort):
        raise AlignmentError(f"row count {len(cohort)} != cache {len(pats)}")
    if not np.array_equal(pats, cohort["patient"].to_numpy().astype(str)):
        raise AlignmentError("patient order differs from cache")
    raw = cohort[TARGETS].to_numpy(dtype=float)
    mask = np.isin(raw, [0.0, 1.0]).astype(float)
    labels = np.where(mask > 0, raw, 0.0)
    if not np.array_equal(mask, np.asarray(cache["mask"], dtype=float)):
        raise AlignmentError("label mask differs from cache")
    if not np.array_equal(labels, np.asarray(cache["labels"], dtype=float)):
        raise AlignmentError("observed labels differ from cache")
    return {"rows": int(len(cohort)), "patients_match": True, "labels_match": True,
            "mask_match": True}


def load_cache(root: Path, site: str, model: str, cond: str, label_source: str = "impression",
               suffix: str = "") -> dict:
    p = Path(root) / f"data/predictions/{site}__{model}__{cond}__{label_source}{suffix}.npz"
    z = np.load(p, allow_pickle=False)
    return {k: z[k] for k in z.files}


def missing_external_images(root: Path, threshold: int = 3) -> list[str]:
    idx = build_external_index(Path(root), label_source="impression", threshold=threshold)
    return sorted(idx.loc[~idx["_present"], "path_to_image"].tolist())


def build_and_verify(root: Path, *, site: str, label_source: str, threshold: int = 3,
                     suffix: str = "", cache_model: str = "M1") -> tuple[pd.DataFrame, dict]:
    """Reconstruct, verify exactly, and store. External: try each lost image."""
    root = Path(root)
    cache = load_cache(root, site, cache_model, "C0", label_source, suffix)
    restored: list[str] = []
    if site == "source":
        cohort = source_cohort(root, label_source=label_source, threshold=threshold)
        check = verify_against_cache(cohort, cache)
    else:
        candidates = [frozenset()] + [frozenset([p]) for p in missing_external_images(root, threshold)]
        check, cohort, last = None, None, None
        for cand in candidates:
            c = external_cohort(root, label_source=label_source, threshold=threshold,
                                treat_as_present=cand)
            try:
                check = verify_against_cache(c, cache)
            except AlignmentError as exc:
                last = exc
                continue
            cohort, restored = c, sorted(cand)
            break
        if cohort is None:
            raise AlignmentError(f"no candidate reproduces the external cache: {last}")
    check["restored_lost_images"] = len(restored)
    out = root / ALIGN_DIR
    out.mkdir(parents=True, exist_ok=True)
    tag = f"{site}__{label_source}__T{threshold}" + ("" if "seed" not in suffix else
                                                     "__" + suffix.split("__")[-1])
    cohort.to_parquet(out / f"{tag}.parquet", index=False)
    check.update({"site": site, "label_source": label_source, "threshold": threshold})
    return cohort, check


def label_categories(cohort: pd.DataFrame) -> pd.DataFrame:
    return _label_category(cohort[TARGETS])
