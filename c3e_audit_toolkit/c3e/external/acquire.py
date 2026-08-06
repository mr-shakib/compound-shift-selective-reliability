"""C3-E9a: external-site image acquisition from CheXpert Plus.

Downloads the 191,071 frontal PNGs named in the frozen CheXpert Plus cohort and
reduces each to the same 224px input the source site uses.

Why this streams. The full-resolution PNGs total roughly 620 GB, which does not
fit on this host, but the 224px derivatives are about 2.6 GB. Each batch is
therefore downloaded, verified, resized, and deleted before the next begins, so
peak disk stays in the low gigabytes and the MIMIC originals never have to be
sacrificed for space.

Preprocessing is deliberately identical to Stage 6a: single bilinear step from
full resolution to 224, grayscale, JPEG quality 95. A second resampling applied
only at the external site would be a preprocessing difference that tracks the
site variable this study exists to estimate.

Integrity is checked against the publisher's md5 for every file, in the same
spirit as the Stage 5 SHA-256 pass that caught a truncated MIMIC image.

Row-level outputs stay in the gitignored data tree. Only aggregate counts and
provenance reach results/.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures as futures
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

import pandas as pd
import requests

STAGE = "C3-E9a"
TITLE = "EXTERNAL-SITE IMAGE ACQUISITION"

DECLARATIONS = (
    "STAGE 9a ONLY",
    "EXTERNAL-SITE IMAGE ACQUISITION AND RESIZE",
    "NO EXTERNAL-SITE INFERENCE",
    "NO EXTERNAL-SITE TUNING",
    "NO THRESHOLD SELECTION",
    "NO CROSS-SITE CLAIM",
    "PREPROCESSING IDENTICAL TO THE SOURCE SITE",
    "IMAGES CONFINED TO THE PROTECTED DATA TREE",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)

API = "https://stanford.redivis.com/api/v1"
OWNER = "aimi"
DATASET_NAME = "chexpert_plus"
DATASET_VERSION = "1.0"
DATASET = f"{OWNER}.{DATASET_NAME}:5yyj:v1_0"
INDEX_TABLES = {"train": "png_train", "valid": "png_valid"}

PARQUET = "data/chexpert_plus/df_chexpert_plus_240401.parquet"
DEST = "data/chexpert_plus/images_224"
STAGING = "data/chexpert_plus/_staging"
OUTPUT_DIR = "results/c3e_chexpert_plus/stage9a_acquisition"
EXPECTED_FRONTAL = 191071

# Frozen by protocol v0.4.0, matching Stage 6a exactly.
RESOLUTION = 224
JPEG_QUALITY = 95


def _token() -> str:
    tok = os.environ.get("REDIVIS_API_TOKEN")
    if not tok:
        raise RuntimeError(
            "REDIVIS_API_TOKEN is not set. Export it in the shell; it is never "
            "read from a file or accepted on the command line.")
    return tok


def fetch_index(table_name: str) -> pd.DataFrame:
    """Read a file index table into a frame of name -> id, md5, size.

    Uses the Redivis client's export path rather than the REST rows endpoint.
    That endpoint ignores `startIndex`, so it cannot be paged, and a single
    large page stalls; the client's export handles the full table in one call.
    """
    import redivis

    os.environ.setdefault("REDIVIS_API_ENDPOINT", API)
    table = (redivis.organization(OWNER)
             .dataset(DATASET_NAME, version=DATASET_VERSION)
             .table(table_name))
    return table.to_pandas_dataframe()


def build_worklist(root: Path) -> pd.DataFrame:
    """Join the frozen frontal cohort to the file index.

    The parquet names images as ``train/patientNNNNN/studyN/viewM_frontal.jpg``
    while the index names them ``patientNNNNN/studyN/viewM_frontal.png``. The
    split prefix and the extension both differ; the stem is the join key.
    """
    meta = pd.read_parquet(root / PARQUET,
                           columns=["path_to_image", "frontal_lateral", "split"])
    frontal = meta[meta["frontal_lateral"].str.lower() == "frontal"].copy()
    if len(frontal) != EXPECTED_FRONTAL:
        raise RuntimeError(
            f"cohort has {len(frontal)} frontal rows, expected {EXPECTED_FRONTAL}. "
            "The frozen external cohort is the authorization boundary.")

    frontal["_split"] = frontal["path_to_image"].str.split("/").str[0]
    frontal["_key"] = (frontal["path_to_image"]
                       .str.split("/", n=1).str[1]
                       .str.replace(r"\.jpg$", ".png", regex=True))

    parts = []
    for split, ref in INDEX_TABLES.items():
        print(f"  fetching {split} file index ...", file=sys.stderr, flush=True)
        idx = fetch_index(ref)
        idx["_split"] = split
        parts.append(idx)
        print(f"    {len(idx):,} files", file=sys.stderr, flush=True)
    index = pd.concat(parts, ignore_index=True)

    work = frontal.merge(index, left_on=["_key", "_split"],
                         right_on=["file_name", "_split"], how="inner")
    missing = len(frontal) - len(work)
    if missing:
        raise RuntimeError(
            f"{missing} frontal images have no matching file in the index; "
            "refusing to proceed with an incomplete external cohort")
    return work[["path_to_image", "file_id", "file_name", "md5_hash", "size"]]


def _fetch_one(args: tuple[str, str, str, Path, Path]) -> tuple[str, int, str]:
    """Download, verify md5, resize, write, delete. Returns (path, bytes, status)."""
    from PIL import Image

    token, file_id, md5_expected, staging, out_path = args
    if out_path.exists() and out_path.stat().st_size > 0:
        return (str(out_path), out_path.stat().st_size, "present")

    tmp = staging / f"{file_id.replace('/', '_')}.png"
    try:
        r = requests.get(f"{API}/rawFiles/{file_id}",
                         headers={"Authorization": f"Bearer {token}"},
                         timeout=300)
        r.raise_for_status()
        blob = r.content
        got = base64.b64encode(hashlib.md5(blob).digest()).decode()
        if got != md5_expected:
            return (str(out_path), 0, "md5_mismatch")

        with Image.open(io.BytesIO(blob)) as im:
            im = im.convert("L").resize((RESOLUTION, RESOLUTION), Image.BILINEAR)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            im.save(out_path, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return (str(out_path), out_path.stat().st_size, "ok")
    except Exception as exc:  # noqa: BLE001
        if out_path.exists():
            out_path.unlink()
        return (str(out_path), 0, f"error:{type(exc).__name__}")
    finally:
        if tmp.exists():
            tmp.unlink()


def run(*, project_root: str | Path, workers: int = 8,
        limit: int | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    token = _token()
    dest, staging = root / DEST, root / STAGING
    dest.mkdir(parents=True, exist_ok=True)
    staging.mkdir(parents=True, exist_ok=True)

    print(f"{STAGE} — {TITLE}", file=sys.stderr)
    print(f"  dataset: {DATASET}", file=sys.stderr, flush=True)
    work = build_worklist(root)
    if limit:
        work = work.head(limit)
    total_bytes = int(work["size"].sum())
    print(f"  cohort : {len(work):,} frontal images, "
          f"{total_bytes / 1073741824:.0f} GB to transfer", file=sys.stderr)
    print(f"  output : {DEST} at {RESOLUTION}px (streamed, originals not retained)",
          file=sys.stderr, flush=True)

    jobs = [(token, r.file_id, r.md5_hash, staging,
             dest / r.path_to_image.replace(".jpg", ".jpg"))
            for r in work.itertuples()]

    started = time.time()
    done = ok = present = 0
    mismatched: list[str] = []
    errors: list[str] = []
    out_bytes = 0
    last = 0.0

    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for path, size, status in pool.map(_fetch_one, jobs):
            done += 1
            if status == "ok":
                ok += 1
                out_bytes += size
            elif status == "present":
                present += 1
                out_bytes += size
            elif status == "md5_mismatch":
                mismatched.append(path)
            else:
                errors.append(f"{status}")
            now = time.time()
            if now - last >= 3.0 or done == len(jobs):
                last = now
                el = now - started
                rate = done / el if el else 0.0
                eta = (len(jobs) - done) / rate if rate else 0.0
                print(f"\r  {done:,}/{len(jobs):,} ({done / len(jobs):6.1%})  "
                      f"{rate:5.1f} img/s  {out_bytes / 1048576:6.0f} MB out  "
                      f"bad {len(mismatched)}  err {len(errors)}  "
                      f"eta {int(eta // 3600)}:{int(eta % 3600 // 60):02d}:{int(eta % 60):02d}   ",
                      end="" if done < len(jobs) else "\n", file=sys.stderr, flush=True)

    status = "PASS" if not mismatched and not errors and (ok + present) == len(jobs) else "FAIL"
    return {
        "stage": STAGE, "title": TITLE, "status": status,
        "declarations": list(DECLARATIONS),
        "source": {"provider": "Stanford Redivis", "dataset": DATASET,
                   "index_tables": [f"{DATASET}.{t}" for t in INDEX_TABLES.values()]},
        "preprocessing": {"resolution": RESOLUTION, "jpeg_quality": JPEG_QUALITY,
                          "resample_filter": "bilinear", "steps": "single resize from full resolution",
                          "identical_to_source_site": True},
        "acquisition": {
            "images_expected": len(jobs),
            "images_written": ok, "images_already_present": present,
            "md5_mismatches": len(mismatched), "errors": len(errors),
            "transferred_bytes": total_bytes, "output_bytes": out_bytes,
            "elapsed_seconds": round(time.time() - started, 1),
        },
        "integrity": {"method": "md5 against the publisher file index",
                      "checked": len(jobs), "unresolved_mismatches": len(mismatched)},
        "compliance": {"external_site_inference": False, "external_site_tuning": False,
                       "threshold_selection": False, "cross_site_claim": False,
                       "identifiers_emitted_to_results": False},
        "environment": {"python": platform.python_version(),
                        "platform": f"{platform.system()}-{platform.machine()}"},
    }


def write_outputs(root: Path, report: dict[str, Any]) -> None:
    out = root / OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage9a_acquisition.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    a = report["acquisition"]
    md = [f"# {STAGE} — External-Site Image Acquisition", "",
          f"Status: **{report['status']}**", ""]
    md += [f"- **{d}**" for d in DECLARATIONS]
    md += ["", "| field | value |", "| --- | ---: |",
           f"| images expected | {a['images_expected']:,} |",
           f"| images written | {a['images_written']:,} |",
           f"| already present | {a['images_already_present']:,} |",
           f"| md5 mismatches | {a['md5_mismatches']} |",
           f"| errors | {a['errors']} |",
           f"| transferred | {a['transferred_bytes'] / 1073741824:.0f} GB |",
           f"| stored at 224px | {a['output_bytes'] / 1073741824:.2f} GB |",
           f"| elapsed | {a['elapsed_seconds'] / 3600:.1f} h |", "",
           "Preprocessing matches the source site exactly: a single bilinear resize",
           "from full resolution to 224px, grayscale, JPEG quality 95. Applying a",
           "second resampling only at the external site would introduce a",
           "preprocessing difference tracking the site variable under study.", "",
           "Image paths are restricted data and are not included here.", ""]
    (out / "stage9a_acquisition.md").write_text("\n".join(md), encoding="utf-8")

    def sha(p: Path) -> str:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        return h.hexdigest()

    names = ["stage9a_acquisition.json", "stage9a_acquisition.md"]
    (out / "stage9a_manifest.json").write_text(json.dumps({
        "stage": STAGE, "title": TITLE, "status": report["status"],
        "declarations": list(DECLARATIONS), "output_dir": OUTPUT_DIR,
        "artifacts": [{"name": n, "byte_size": (out / n).stat().st_size,
                       "sha256": sha(out / n)} for n in names],
        "compliance": report["compliance"], "environment": report["environment"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Run C3-E9a external image acquisition")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)
    try:
        report = run(project_root=args.project_root, workers=args.workers,
                     limit=args.limit)
        if args.limit is None:
            write_outputs(Path(args.project_root).resolve(), report)
    except Exception as exc:  # noqa: BLE001
        print(f"{STAGE} FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"stage": STAGE, "status": report["status"],
                      **report["acquisition"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
