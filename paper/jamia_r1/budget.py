"""JAMIA Research and Applications budget check for the R1 build.

Counts what JAMIA counts: body words from Background and Significance through
Conclusion, excluding title page, abstract, references, figures and tables.
Number macros from ../revision/generated/numbers.tex are expanded before
counting (detex would otherwise drop them). Writes wordcount.tex for the title
page and exits non-zero if any limit is exceeded.

    python3 budget.py
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMITS = {"body": 4000, "abstract": 250, "tables": 4, "figures": 6}


def macros() -> dict[str, str]:
    m = {}
    for line in (HERE / "../revision/generated/numbers.tex").read_text().splitlines():
        r = re.match(r"\\newcommand\{\\(\w+)\}\{(.*)\}$", line)
        if r:
            m[r.group(1)] = r.group(2)
    return m


def plain(tex: str, mac: dict[str, str]) -> str:
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tex = re.sub(r"\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}", " ", tex, flags=re.S)
    for _ in range(2):
        tex = re.sub(r"\\(\w+)\{\}", lambda r: mac.get(r.group(1), r.group(0)), tex)
        tex = re.sub(r"\\(\w+)(?![\w{])", lambda r: mac.get(r.group(1), r.group(0)), tex)
    out = subprocess.run(["detex", "-n"], input=tex, capture_output=True, text=True).stdout
    return out


def words(text: str) -> int:
    return len([t for t in text.split() if re.search(r"[A-Za-z0-9]", t)])


def main() -> int:
    mac = macros()
    secs = sorted((HERE / "sections").glob("*.tex"))
    body, rows = 0, []
    for f in secs:
        w = words(plain(f.read_text(), mac))
        rows.append((f.stem, w))
        body += w
    main_tex = (HERE / "main_jamia_r1.tex").read_text()
    abstract = main_tex.split("% ABSTRACT-START")[1].split("% ABSTRACT-END")[0]
    abstract = re.sub(r"\\textbf\{(Objective|Materials and Methods|Results|Discussion|Conclusion):\}", "", abstract)
    ab = words(plain(abstract, mac))
    all_tex = "".join(f.read_text() for f in secs)
    tables = len(re.findall(r"\\begin\{table\}", all_tex))
    figures = len(re.findall(r"\\begin\{figure\}", all_tex))
    holes = len(re.findall(r"\\authorinput\{", main_tex + all_tex))
    alt = len(re.findall(r"\\alttext\{", all_tex))
    (HERE / "wordcount.tex").write_text(f"{body:,}\n")
    (HERE / "abstractcount.tex").write_text(f"{ab}\n")

    print(f"{'SECTION':<28}{'WORDS':>8}")
    for name, w in rows:
        print(f"{name:<28}{w:>8}")
    print(f"{'BODY TOTAL':<28}{body:>8}   limit {LIMITS['body']}")
    print(f"{'ABSTRACT (excl. headings)':<28}{ab:>8}   limit {LIMITS['abstract']}")
    print(f"{'TABLES':<28}{tables:>8}   limit {LIMITS['tables']}")
    print(f"{'FIGURES':<28}{figures:>8}   limit {LIMITS['figures']}  (alt texts: {alt})")
    print(f"{'AUTHOR-INPUT PLACEHOLDERS':<28}{holes:>8}")
    over = [k for k, v in (("body", body), ("abstract", ab), ("tables", tables), ("figures", figures))
            if v > LIMITS[k]]
    if alt != figures:
        over.append("alt text missing")
    print("OVER LIMIT: " + ", ".join(over) if over else "All JAMIA limits met.")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
