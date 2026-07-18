"""Recursive safety scan for generated CheXpert aggregate outputs.

Flags any file that contains a pattern that could represent leaked identifiers,
paths, derived keys, or unusually long free text. On detection the offending
file is DELETED (outputs are regenerable); source data is never touched.

Deliberately conservative about false positives:
  * split VALUES ``train`` / ``valid`` are allowed; only the path forms
    ``train/`` and ``valid/`` are forbidden.
  * column names containing the word ``study`` (e.g. ``study_count``) are allowed;
    only ``study<digits>`` (a folder value) is forbidden.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

FORBIDDEN = {
    "patient_folder_value": re.compile(r"patient\d+"),
    "study_folder_value": re.compile(r"study\d+"),
    "jpg_extension": re.compile(r"\.jpg", re.IGNORECASE),
    "dcm_extension": re.compile(r"\.dcm", re.IGNORECASE),
    "train_path": re.compile(r"train/"),
    "valid_path": re.compile(r"valid/"),
    "internal_key": re.compile(r"_c3e_"),
}
# A single CSV cell or JSON string value longer than this is treated as suspect
# free text (aggregate values are short; column names are checked separately and
# are permitted). Checked per-field, not per-line, so comma-joined header rows
# of legitimate column names do not trip it.
LONG_FIELD = 200
LONG_TOKEN = 120


def _json_has_long_string(obj, limit: int) -> bool:
    if isinstance(obj, str):
        return len(obj) > limit
    if isinstance(obj, dict):
        return any(_json_has_long_string(v, limit) for v in obj.values())
    if isinstance(obj, list):
        return any(_json_has_long_string(v, limit) for v in obj)
    return False


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return [f"unreadable: {path.name}"]
    for name, rx in FORBIDDEN.items():
        if rx.search(text):
            findings.append(name)
    # format-aware long-free-text check (avoids flagging comma-joined headers of
    # legitimate column names).
    long_field = False
    if path.suffix == ".csv":
        for row in csv.reader(io.StringIO(text)):
            if any(len(cell) > LONG_FIELD for cell in row):
                long_field = True
                break
    elif path.suffix == ".json":
        try:
            long_field = _json_has_long_string(json.loads(text), LONG_FIELD)
        except json.JSONDecodeError:
            long_field = any(len(t) > LONG_TOKEN for t in text.split())
    else:
        long_field = any(len(t) > LONG_TOKEN for t in text.split())
    if long_field:
        findings.append("long_free_text_field")
    return findings


def scan_tree(root: str | Path, *, delete_unsafe: bool = True) -> dict:
    root = Path(root)
    scanned, unsafe = [], {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        scanned.append(str(p.relative_to(root)))
        problems = scan_file(p)
        if problems:
            unsafe[str(p.relative_to(root))] = problems
            if delete_unsafe:
                p.unlink()
    return {
        "root": str(root),
        "files_scanned": len(scanned),
        "unsafe_files": unsafe,
        "clean": len(unsafe) == 0,
    }


def main(argv: list[str]) -> int:
    root = argv[1] if len(argv) > 1 else "."
    delete = "--no-delete" not in argv
    result = scan_tree(root, delete_unsafe=delete)
    print(f"scanned {result['files_scanned']} files under {result['root']}")
    if result["clean"]:
        print("SAFE: no forbidden patterns detected")
        return 0
    print("UNSAFE content detected (offending files deleted):")
    for f, probs in result["unsafe_files"].items():
        print(f"  {f}: {', '.join(probs)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
