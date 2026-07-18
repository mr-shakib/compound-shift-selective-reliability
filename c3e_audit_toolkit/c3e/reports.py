from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile
import re
import pandas as pd

SECTION_ALIASES = {
    "history": {
        "history", "clinical history", "indication", "reason for examination",
        "reason for exam", "exam indication", "clinical indication"
    },
    "findings": {"findings", "finding"},
    "impression": {"impression", "conclusion"},
    "comparison": {"comparison", "comparisons"},
    "technique": {"technique", "procedure"},
}

HEADER_RE = re.compile(r"(?m)^\s*([A-Z][A-Z /_-]{2,40})\s*:\s*")

def _normalize_header(header: str) -> str:
    return re.sub(r"\s+", " ", header.strip().lower().replace("_", " "))

def parse_sections(text: str) -> dict[str, str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    matches = list(HEADER_RE.finditer(text))
    sections: dict[str, list[str]] = {}
    if not matches:
        return {"unsectioned": text.strip()}
    prefix = text[:matches[0].start()].strip()
    if prefix:
        sections.setdefault("prefix", []).append(prefix)
    for i, match in enumerate(matches):
        header = _normalize_header(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        canonical = header
        for key, aliases in SECTION_ALIASES.items():
            if header in aliases:
                canonical = key
                break
        sections.setdefault(canonical, []).append(body)
    return {k: "\n".join(v).strip() for k, v in sections.items()}

def extract_study_id(name: str) -> int | None:
    m = re.search(r"(?:^|[/\\])s(\d+)\.txt$", name)
    if not m:
        m = re.search(r"s(\d+)\.txt$", name)
    return int(m.group(1)) if m else None

def _row_from_text(name: str, text: str) -> dict:
    sid = extract_study_id(name)
    sections = parse_sections(text)
    return {
        "study_id": sid,
        "context": sections.get("history", ""),
        "findings_present": bool(sections.get("findings", "").strip()),
        "impression_present": bool(sections.get("impression", "").strip()),
        "comparison_present": bool(sections.get("comparison", "").strip()),
        "all_section_names": "|".join(sorted(sections)),
    }

def read_mimic_reports(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    rows = []
    if path.is_file() and path.suffix.lower() == ".zip":
        with ZipFile(path) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".txt"):
                    continue
                sid = extract_study_id(name)
                if sid is None:
                    continue
                text = zf.read(name).decode("utf-8", errors="replace")
                rows.append(_row_from_text(name, text))
    elif path.is_dir():
        for p in path.rglob("*.txt"):
            sid = extract_study_id(str(p))
            if sid is None:
                continue
            rows.append(_row_from_text(str(p), p.read_text(encoding="utf-8", errors="replace")))
    else:
        raise FileNotFoundError(f"Reports path is neither an extracted directory nor ZIP: {path}")
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No MIMIC report text files were found.")
    if df["study_id"].duplicated().any():
        df = df.sort_values("study_id").drop_duplicates("study_id", keep="first")
    return df
