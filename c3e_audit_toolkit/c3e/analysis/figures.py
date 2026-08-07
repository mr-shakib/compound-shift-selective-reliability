"""C3-E6 Stage 11: paper figures.

Two figures, both drawn from committed aggregate artifacts rather than from a
fresh computation, so a figure cannot silently disagree with the number in the
text beside it.

Figure 1 is a forest plot of the confirmatory contrasts. It carries what four
tables of intervals carry, and makes the two reversals visible as intervals
sitting on the wrong side of zero rather than as a word in a verdict column.

Figure 2 places selective risk and coverage side by side at both sites, since
the paper's central claim is that these two move differently: risk degrades on
institutional transfer while coverage holds, and coverage breaks only under
context intervention.

Figures contain aggregate quantities only and no identifier.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ANALYSIS = "results/c3e_cross_site/stage10_analysis"
SOURCE = "results/c3e_mimic/stage8_interventions/stage8_results.csv"
EXTERNAL = "results/c3e_chexpert_plus/stage9b_evaluation/stage9b_results.csv"
OUTPUT_DIR = "paper/figures"

MATERIALITY = 0.02
MODELS = ("M1", "M2", "M3", "M4")
MODEL_LABEL = {"M1": "M1 image-only", "M2": "M2 text-only",
               "M3": "M3 late fusion", "M4": "M4 feature fusion"}
CONDITION_LABEL = {"C0": "C0 original", "C1": "C1 no context",
                   "C2": "C2 misaligned"}


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "serif", "font.size": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
        "figure.dpi": 200, "savefig.bbox": "tight",
    })
    return plt


def forest(root: Path, out: Path) -> Path:
    """Confirmatory contrasts with their intervals, grouped by hypothesis."""
    plt = _style()
    rows = list(csv.DictReader(open(root / ANALYSIS / "stage10_hypotheses.csv")))

    entries = []
    for h in ("H1", "H2", "H3", "H4"):
        block = [r for r in rows if r["hypothesis"] == h]
        for r in block:
            site = f" [{r['site']}]" if r["site"] else ""
            cond = ""
            if "C1-C0" in r["contrast"]:
                cond = " · C1"
            elif "C2-C0" in r["contrast"]:
                cond = " · C2"
            entries.append({
                "label": f"{r['model']}{site}{cond}",
                "group": h,
                "point": float(r["point_estimate"]),
                "lo": float(r["ci_low"]), "hi": float(r["ci_high"]),
                "confirmed": r["confirmed"] == "True",
                "reversed": r.get("reversed_at_materiality") == "True",
            })

    fig, ax = plt.subplots(figsize=(6.6, 0.34 * len(entries) + 1.4))
    ypos, ylabels, boundaries = [], [], []
    y = 0
    last_group = None
    for e in entries:
        if last_group is not None and e["group"] != last_group:
            boundaries.append(y - 0.5)
            y += 0.6
        ypos.append(y)
        ylabels.append(f"{e['group']}  {e['label']}")
        last_group = e["group"]
        y += 1

    for yp, e in zip(ypos, entries):
        if e["confirmed"]:
            colour, marker = "#1a5e20", "o"
        elif e["reversed"]:
            colour, marker = "#8c1c13", "D"
        else:
            colour, marker = "#5a5a5a", "o"
        ax.plot([e["lo"], e["hi"]], [yp, yp], color=colour, lw=1.6,
                solid_capstyle="butt", zorder=2)
        ax.plot([e["point"]], [yp], marker=marker, ms=4.5, color=colour, zorder=3)

    ax.axvline(0.0, color="black", lw=0.9, zorder=1)
    for x in (MATERIALITY, -MATERIALITY):
        ax.axvline(x, color="#999999", lw=0.8, ls=(0, (4, 3)), zorder=1)
    for b in boundaries:
        ax.axhline(b, color="#dddddd", lw=0.6, zorder=0)

    ax.set_yticks(ypos)
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Difference in selective Hamming error (95% CI)")
    ax.annotate("materiality", xy=(MATERIALITY, ypos[-1] + 0.9),
                fontsize=7, color="#777777", ha="center", va="top")

    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([], [], color="#1a5e20", marker="o", ms=4.5, lw=1.6, label="confirmed"),
        Line2D([], [], color="#8c1c13", marker="D", ms=4.5, lw=1.6,
               label="reversed at materiality"),
        Line2D([], [], color="#5a5a5a", marker="o", ms=4.5, lw=1.6, label="not confirmed"),
    ], loc="lower right", fontsize=7.5, frameon=False)

    path = out / "fig1_forest.pdf"
    fig.savefig(path)
    plt.close(fig)
    return path


def risk_and_coverage(root: Path, out: Path) -> Path:
    """Selective risk and realised coverage, both sites, all conditions."""
    plt = _style()

    def load(p, site):
        return [r for r in csv.DictReader(open(root / p))
                if r["target_coverage"] == "0.8"]

    src = {(r["model"], r["condition"]): r for r in load(SOURCE, "source")}
    ext = {(r["model"], r["condition"]): r for r in load(EXTERNAL, "external")}

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    width = 0.26
    conds = ("C0", "C1", "C2")
    colours = {"C0": "#2b5d8a", "C1": "#c98a2e", "C2": "#8c1c13"}
    xs = range(len(MODELS))

    for ax, data, title in ((axes[0], src, "Source site"),
                            (axes[1], ext, "External site")):
        for k, cond in enumerate(conds):
            vals = [float(data[(m, cond)]["selective_hamming_error"]) for m in MODELS]
            ax.bar([x + (k - 1) * width for x in xs], vals, width,
                   label=CONDITION_LABEL[cond], color=colours[cond], zorder=2)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(MODELS)
        ax.set_title(title, fontsize=9)
        ax.set_ylim(0, 0.30)
    axes[0].set_ylabel("Selective Hamming error")
    axes[1].legend(fontsize=7.5, frameon=False, loc="upper right")

    path = out / "fig2_risk.pdf"
    fig.savefig(path)
    plt.close(fig)

    # Coverage, drawn on its own axis because the point is that it behaves
    # differently from risk rather than alongside it.
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    labels, values, colours_c = [], [], []
    for site, data in (("source", src), ("external", ext)):
        for m in MODELS:
            for cond in conds:
                labels.append(f"{m}\n{cond}")
                values.append(float(data[(m, cond)]["realised_coverage"]))
                drift = abs(values[-1] - 0.8)
                colours_c.append("#8c1c13" if drift >= 0.05 else
                                 ("#2b5d8a" if site == "source" else "#4a8fbd"))
    ax.bar(range(len(values)), values, color=colours_c, zorder=2)
    ax.axhline(0.8, color="black", lw=0.9, zorder=3)
    ax.axhspan(0.75, 0.85, color="#cccccc", alpha=0.35, zorder=0)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=5.5)
    ax.set_ylabel("Realised coverage")
    ax.set_ylim(0.6, 1.05)
    ax.text(len(values) / 4, 1.02, "source site", ha="center", fontsize=8)
    ax.text(3 * len(values) / 4, 1.02, "external site", ha="center", fontsize=8)
    ax.axvline(len(values) / 2 - 0.5, color="#999999", lw=0.8)
    path2 = out / "fig3_coverage.pdf"
    fig.savefig(path2)
    plt.close(fig)
    return path


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Render C3E paper figures")
    ap.add_argument("--project-root", type=Path, default=default_root)
    args = ap.parse_args(argv)
    root = Path(args.project_root).resolve()
    out = root / OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    try:
        forest(root, out)
        risk_and_coverage(root, out)
    except Exception as exc:  # noqa: BLE001
        print(f"figures FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for f in sorted(out.glob("*.pdf")):
        print(f"  {f.relative_to(root)}  {f.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
