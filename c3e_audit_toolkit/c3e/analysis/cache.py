"""Per-study prediction cache shared by the evaluation stages.

Two problems, one mechanism.

A full evaluation pass is twelve model-by-condition inference runs over a large
cohort, and losing the machine partway through discards all of it. Caching each
pass makes a rerun resume rather than restart.

Separately, the bootstrap needs per-study errors, confidences and patient
identifiers, which the evaluation stages compute and then throw away. Without a
cache the analysis would have to re-run inference to recover numbers that were
already produced, and re-running inference to obtain an interval invites the
suspicion that the interval was chosen.

Caches hold study-level probabilities and patient identifiers, so they are
restricted data and live in the gitignored tree. They are keyed by the model
checkpoint digest, so a cache produced by different weights is never silently
reused.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

CACHE_DIR = "data/predictions"


def _key(site: str, model_id: str, condition: str, label_source: str,
         threshold: int) -> str:
    # The threshold determines which studies are N1 and therefore which studies
    # are in the cohort at all. A cache keyed without it would be silently
    # reused across thresholds and describe the wrong cohort.
    suffix = "" if threshold == 3 else f"__T{threshold}"
    return f"{site}__{model_id}__{condition}__{label_source}{suffix}"


def cache_path(root: Path, site: str, model_id: str, condition: str,
               label_source: str = "impression", threshold: int = 3) -> Path:
    return (Path(root) / CACHE_DIR /
            f"{_key(site, model_id, condition, label_source, threshold)}.npz")


def checkpoint_digest(path: Path) -> str:
    """Short digest of the weights that produced a cache."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def save(root: Path, site: str, model_id: str, condition: str, *,
         probabilities: np.ndarray, labels: np.ndarray, mask: np.ndarray,
         patients: np.ndarray, checkpoint_sha: str,
         label_source: str = "impression", threshold: int = 3) -> Path:
    p = cache_path(root, site, model_id, condition, label_source, threshold)
    p.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        p, probabilities=probabilities, labels=labels, mask=mask,
        patients=np.asarray(patients).astype(str),
        meta=np.array([json.dumps({
            "site": site, "model_id": model_id, "condition": condition,
            "label_source": label_source, "checkpoint_sha": checkpoint_sha,
            "informativeness_threshold": threshold,
            "studies": int(len(probabilities)),
        })]))
    return p


def load(root: Path, site: str, model_id: str, condition: str, *,
         checkpoint_sha: str, label_source: str = "impression",
         threshold: int = 3) -> dict[str, Any] | None:
    """Return a cached pass, or None when absent or produced by other weights."""
    p = cache_path(root, site, model_id, condition, label_source, threshold)
    if not p.exists():
        return None
    try:
        blob = np.load(p, allow_pickle=False)
        meta = json.loads(str(blob["meta"][0]))
    except Exception:  # noqa: BLE001
        return None
    if meta.get("informativeness_threshold", 3) != threshold:
        return None
    if meta.get("checkpoint_sha") != checkpoint_sha:
        # Different weights produced this. Reusing it would silently mix models.
        return None
    return {"probabilities": blob["probabilities"], "labels": blob["labels"],
            "mask": blob["mask"], "patients": blob["patients"], "meta": meta}
