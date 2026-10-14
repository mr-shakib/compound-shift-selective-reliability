"""Full-resolution originals for the sampled studies only.

The analysis pipeline keeps 224-pixel copies; readers need the originals. This
fetches exactly the images named in the frozen sample list and nothing else:

* MIMIC-CXR-JPG through the PhysioNet S3 access point used in Stage 5
  (credentials from the AWS CLI configuration), verified against the
  publisher's SHA-256 list. Every sampled path is already inside the Stage 3E
  manifests, which remain the authorization boundary.
* CheXpert Plus PNGs through the Redivis API used in Stage 9a
  (``REDIVIS_API_TOKEN`` from the environment), verified against the published
  md5 and kept at full resolution.

Images go to ``data/adjudication/images_full/`` (gitignored). Credentials are
never accepted on the command line or written anywhere.

    python -m c3e.adjudication.fetch [--workers 8]
"""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd

from ..external.acquire import API, INDEX_TABLES, _token, fetch_index
from .sample import OUT_DATA

S3_BASE = ("s3://arn:aws:s3:us-east-1:724665945834:accesspoint/mimic-cxr-jpg-v2-1-0-01/"
           "mimic-cxr-jpg/2.1.0")
MIMIC_SUMS = "data/mimic/SHA256SUMS_jpg.txt"
MIMIC_MANIFEST = "data/mimic/download_manifests/ALL_frontal_jpg_paths.txt"
FULL = f"{OUT_DATA}/images_full"


def full_path(root: Path, site: str, image: str) -> Path:
    """Where a sampled image's original lives (CheXpert originals are PNG)."""
    rel = image if site == "source" else image.rsplit(".", 1)[0] + ".png"
    return Path(root) / FULL / site / rel


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _mimic_one(args) -> tuple[str, str]:
    rel, out, expected = args
    if out.exists() and _sha256(out) == expected:
        return rel, "present"
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["aws", "s3", "cp", "--quiet", f"{S3_BASE}/{rel}", str(out)],
                       capture_output=True, env={**os.environ, "AWS_REGION": os.environ.get("AWS_REGION", "us-east-1")})
    if r.returncode != 0 or not out.exists():
        return rel, "error"
    if _sha256(out) != expected:
        out.unlink()
        return rel, "sha256_mismatch"
    return rel, "ok"


def _chexpert_one(args) -> tuple[str, str]:
    import requests
    token, rel, file_id, md5, out = args
    if out.exists() and out.stat().st_size > 0:
        return rel, "present"
    r = requests.get(f"{API}/rawFiles/{file_id}", headers={"Authorization": f"Bearer {token}"}, timeout=300)
    if r.status_code != 200:
        return rel, f"http_{r.status_code}"
    if base64.b64encode(hashlib.md5(r.content).digest()).decode() != md5:
        return rel, "md5_mismatch"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    return rel, "ok"


def run(root: Path, workers: int = 8) -> list[dict]:
    root = Path(root)
    items = pd.read_csv(root / OUT_DATA / "sample_v1.csv")
    rows = [(s, img) for s, imgs in zip(items.site, items.images) for img in json.loads(imgs)]
    src = sorted({img for s, img in rows if s == "source"})
    ext = sorted({img for s, img in rows if s == "external"})
    status = []

    if src:
        allowed = set(Path(root / MIMIC_MANIFEST).read_text().split())
        outside = [p for p in src if p not in allowed]
        if outside:
            raise RuntimeError(f"{len(outside)} sampled MIMIC paths are outside the Stage 3E manifests")
        sums = {}
        for line in Path(root / MIMIC_SUMS).read_text().splitlines():
            parts = line.split()
            if len(parts) == 2:
                sums[parts[1].lstrip("*")] = parts[0]
        jobs = [(p, full_path(root, "source", p), sums[p]) for p in src]
        with ThreadPoolExecutor(workers) as ex:
            status += [{"site": "source", "status": st} for _, st in ex.map(_mimic_one, jobs)]

    if ext:
        token = _token()
        index = []
        for split, table in INDEX_TABLES.items():
            t = fetch_index(table)
            t["_key"] = split + "/" + t["file_name"].astype(str)
            index.append(t)
        index = pd.concat(index).set_index("_key")
        jobs = []
        for p in ext:
            key = p.rsplit(".", 1)[0] + ".png"
            row = index.loc[key]
            jobs.append((token, p, row["file_id"], row["md5_hash"], full_path(root, "external", p)))
        with ThreadPoolExecutor(workers) as ex:
            status += [{"site": "external", "status": st} for _, st in ex.map(_chexpert_one, jobs)]
    return status


def main(argv=None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Expert adjudication: fetch full-resolution originals")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    st = pd.DataFrame(run(a.project_root.resolve(), a.workers))
    summary = st.groupby(["site", "status"]).size().rename("images").reset_index()
    print(summary.to_string(index=False), file=sys.stderr)
    bad = st[~st.status.isin(["ok", "present"])]
    if len(bad):
        print(f"{len(bad)} images failed; rerun to retry", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
