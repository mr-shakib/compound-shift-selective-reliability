"""C3-E6 Stage 6a: one-time image preprocessing to the frozen input resolution.

Decodes each acquired frontal JPG once, resizes to the protocol's 224px input,
and writes it back as a small JPG. The full-resolution originals are untouched.

Why this exists. The acquired images average 1.8 MB at full radiograph
resolution. Decoding them at training speed saturates the CPU long before the
GPU is busy, and the study trains four models for up to fifteen epochs each, so
the same decode would otherwise be paid roughly sixty times per image. Paying it
once turns ~318 GB into a few GB that fit in page cache.

Resolution, channel handling, and the interpolation choice are fixed by
`models.exact_backbones` in the protocol registry and are not tunable here.

Preprocessed tensors are restricted data and stay in the gitignored data tree.
Only aggregate counts and provenance reach results/.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

STAGE = "C3-E6 Stage 6a"
TITLE = "IMAGE PREPROCESSING TO FROZEN INPUT RESOLUTION"

DECLARATIONS = (
    "STAGE 6a ONLY",
    "IMAGE DECODE AND RESIZE",
    "NO MODEL TRAINING IN THIS RUN",
    "NO LABELS READ",
    "NO PREDICTION THRESHOLD SELECTION",
    "NO EVALUATION OR METRIC COMPUTATION",
    "ORIGINALS LEFT UNMODIFIED",
    "PREPROCESSED IMAGES CONFINED TO THE PROTECTED DATA TREE",
    "NO IDENTIFIERS EMITTED TO RESULTS",
)

MANIFEST = "data/mimic/download_manifests/ALL_frontal_jpg_paths.txt"
SRC_DIR = "data/mimic/images"
DST_DIR = "data/mimic/images_224"
OUTPUT_DIR = "results/c3e_mimic/stage6_training"
EXPECTED_TOTAL = 193282

# Frozen by protocol v0.4.0 models.exact_backbones.image
RESOLUTION = 224
JPEG_QUALITY = 95


def _resize_one(args: tuple[Path, Path]) -> int:
    """Decode, resize, and write one image. Returns bytes written, 0 on failure."""
    from PIL import Image

    src, dst = args
    if dst.exists() and dst.stat().st_size > 0:
        return dst.stat().st_size
    try:
        with Image.open(src) as im:
            # Radiographs are single-channel; the backbone expects three, but the
            # replication is done at load time rather than baked in here so the
            # stored file stays small.
            im = im.convert("L")
            im = im.resize((RESOLUTION, RESOLUTION), Image.BILINEAR)
            dst.parent.mkdir(parents=True, exist_ok=True)
            im.save(dst, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return dst.stat().st_size
    except Exception:
        if dst.exists():
            dst.unlink()
        return 0


def run(*, project_root: str | Path, workers: int = 8,
        limit: int | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    manifest = root / MANIFEST
    src_root = root / SRC_DIR
    dst_root = root / DST_DIR

    paths = [p.strip() for p in manifest.read_text().splitlines() if p.strip()]
    if limit is None and len(paths) != EXPECTED_TOTAL:
        raise ValueError(
            f"manifest lists {len(paths)} images, expected {EXPECTED_TOTAL}. "
            "The manifest is the authorization boundary; investigate before running."
        )
    if limit:
        paths = paths[:limit]

    print(f"{STAGE} — {TITLE}", file=sys.stderr, flush=True)
    print(f"  source     : {SRC_DIR}", file=sys.stderr)
    print(f"  destination: {DST_DIR} (gitignored)", file=sys.stderr)
    print(f"  resolution : {RESOLUTION}px, quality {JPEG_QUALITY}", file=sys.stderr)
    print(f"  images     : {len(paths):,}   workers: {workers}", file=sys.stderr, flush=True)

    jobs = [(src_root / p, dst_root / p) for p in paths]
    started = time.time()
    done = 0
    failed = 0
    out_bytes = 0
    last_report = 0.0

    with futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for size in pool.map(_resize_one, jobs, chunksize=64):
            done += 1
            if size == 0:
                failed += 1
            else:
                out_bytes += size
            now = time.time()
            if now - last_report >= 2.0 or done == len(jobs):
                last_report = now
                el = now - started
                rate = done / el if el > 0 else 0.0
                eta = (len(jobs) - done) / rate if rate > 0 else 0.0
                print(
                    f"\r  {done:,}/{len(jobs):,} ({done / len(jobs):6.1%})  "
                    f"{rate:6.0f} img/s  {out_bytes / 1048576:7.0f} MB out  "
                    f"failed {failed}  eta {int(eta // 3600)}:{int(eta % 3600 // 60):02d}:"
                    f"{int(eta % 60):02d}   ",
                    end="" if done < len(jobs) else "\n",
                    file=sys.stderr, flush=True,
                )

    elapsed = time.time() - started
    src_bytes = sum(j[0].stat().st_size for j in jobs if j[0].exists())

    report = {
        "stage": STAGE, "title": TITLE,
        "status": "PASS" if failed == 0 else "FAIL",
        "declarations": list(DECLARATIONS),
        "input_resolution": RESOLUTION,
        "jpeg_quality": JPEG_QUALITY,
        "resample_filter": "bilinear",
        "channel_handling": "stored single-channel; replicated to three at load time",
        "images_expected": len(jobs),
        "images_written": done - failed,
        "images_failed": failed,
        "source_bytes": src_bytes,
        "output_bytes": out_bytes,
        "compression_ratio": round(src_bytes / out_bytes, 1) if out_bytes else 0.0,
        "elapsed_seconds": round(elapsed, 1),
        "compliance": {
            "model_training": False,
            "labels_read": False,
            "threshold_selection": False,
            "evaluation_performed": False,
            "originals_modified": False,
            "identifiers_emitted_to_results": False,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": f"{platform.system()}-{platform.machine()}",
        },
    }
    return report


def write_outputs(root: Path, report: dict[str, Any]) -> None:
    out = root / OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage6a_preprocess.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md = [f"# {STAGE} — Image Preprocessing", "",
          f"Status: **{report['status']}**", ""]
    md += [f"- **{d}**" for d in DECLARATIONS]
    md += ["", "| field | value |", "| --- | ---: |",
           f"| input resolution | {report['input_resolution']}px |",
           f"| images written | {report['images_written']:,} |",
           f"| images failed | {report['images_failed']} |",
           f"| source size | {report['source_bytes'] / 1073741824:.1f} GB |",
           f"| output size | {report['output_bytes'] / 1073741824:.2f} GB |",
           f"| compression | {report['compression_ratio']}x |",
           f"| elapsed | {report['elapsed_seconds']:.0f} s |", "",
           "Resolution, channel handling, and the resample filter are fixed by",
           "`models.exact_backbones` in protocol v0.4.0 and are not tunable at this stage.",
           "", "Image paths are restricted data and are not included here.", ""]
    (out / "stage6a_preprocess.md").write_text("\n".join(md), encoding="utf-8")

    def sha(p: Path) -> str:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    names = ["stage6a_preprocess.json", "stage6a_preprocess.md"]
    manifest = {
        "stage": STAGE, "title": TITLE, "status": report["status"],
        "declarations": list(DECLARATIONS), "output_dir": OUTPUT_DIR,
        "artifacts": [{"name": n, "byte_size": (out / n).stat().st_size,
                       "sha256": sha(out / n)} for n in names],
        "compliance": report["compliance"], "environment": report["environment"],
    }
    (out / "stage6a_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Run C3-E6 Stage 6a image preprocessing")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)

    try:
        report = run(project_root=args.project_root, workers=args.workers, limit=args.limit)
    except Exception as exc:  # noqa: BLE001
        print(f"Stage 6a FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if args.limit is None:
        write_outputs(Path(args.project_root).resolve(), report)
    print(json.dumps({k: report[k] for k in
                      ("stage", "status", "images_written", "images_failed",
                       "output_bytes", "compression_ratio", "elapsed_seconds")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
