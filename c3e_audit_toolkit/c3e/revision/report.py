"""Revision R1: generate manuscript tables, number macros and figures.

Every number printed in the revised manuscript comes from a file written by
``c3e.revision.runner`` (results/c3e_revision/) or from a committed stage
artifact, through this module. Nothing is typed by hand.

    python -m c3e.revision.report
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

R = "results/c3e_revision"
GEN = "paper/revision/generated"
FIG = "paper/revision/figures"
TARGETS = ["Cardiomegaly", "Edema", "Consolidation", "Atelectasis", "Pleural Effusion"]
SHORT = {"Cardiomegaly": "Card.", "Edema": "Edema", "Consolidation": "Cons.",
         "Atelectasis": "Atel.", "Pleural Effusion": "Eff."}
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # validated (dataviz skill)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
VERDICT_TEX = {
    "confirmed": "C",
    "same_direction_not_material": "S",
    "inconclusive": "I",
    "opposite_direction_not_material": "O",
    "opposite_direction_material": "O*",
}


TAGS = {("primary", "primary", "original"): "Orig", ("primary", "primary", "evaluable_study"): "Eval",
        ("primary", "primary", "cell_micro"): "Cell", ("primary", "primary", "pathology_macro"): "Macro",
        ("primary", "uncertain_negative", "evaluable_study"): "UncNeg",
        ("primary", "uncertain_positive", "evaluable_study"): "UncPos",
        ("primary", "unmentioned_negative", "evaluable_study"): "UnmNeg",
        ("coverage70", "primary", "evaluable_study"): "CovSeventy",
        ("coverage90", "primary", "evaluable_study"): "CovNinety",
        ("T5", "primary", "evaluable_study"): "TFive", ("T10", "primary", "evaluable_study"): "TTen",
        ("findings_S1", "primary", "evaluable_study"): "Find", ("findings_S1", "primary", "original"): "FindOrig",
        ("seed20260719", "primary", "evaluable_study"): "Seed", ("seed20260719", "primary", "original"): "SeedOrig"}


def f(x, d=4, sign=True):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "--"
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace("-", "$-$") if sign else s


def ci(lo, hi, d=4):
    return f"({f(lo, d)}, {f(hi, d)})"


def pct(x, d=1):
    return f"{100 * x:.{d}f}\\%"


def n(x):
    return f"{int(x):,}"


class Gen:
    def __init__(self, root: Path):
        self.root = root
        self.r = root / R
        self.out = root / GEN
        self.fig = root / FIG
        self.out.mkdir(parents=True, exist_ok=True)
        self.fig.mkdir(parents=True, exist_ok=True)
        self.macros: dict[str, str] = {}
        self.h = pd.read_csv(self.r / "hypotheses.csv")
        self.lev = pd.read_csv(self.r / "levels.csv")
        # The M2/M3 replicate (follow-up) extends the seed-20260719 analysis,
        # whose M1/M4 rows it reproduces exactly; add only its M2/M3 rows.
        fp = self.r / "followup_m2m3_contrasts.csv"
        if fp.exists():
            f2 = pd.read_csv(fp)
            f2 = f2[f2.model.isin(["M2", "M3"])]
            f2.insert(0, "analysis", "seed20260719")
            f2.insert(1, "label_variant", "primary")
            self.h = pd.concat([self.h, f2], ignore_index=True)

    def csv(self, name):
        return pd.read_csv(self.r / f"{name}.csv")

    def mac(self, name, value):
        if not name.isalpha():
            raise ValueError(name)
        self.macros[name] = value

    def write(self, name, text):
        (self.out / f"{name}.tex").write_text(text + "\n", encoding="utf-8")

    # ------------------------------------------------------------------ helpers
    def H(self, analysis="primary", variant="primary", est="evaluable_study"):
        return self.h[(self.h.analysis == analysis) & (self.h.label_variant == variant)
                      & (self.h.estimator == est)]

    def row(self, df, hyp, model, site=None, contrast_has=None):
        x = df[(df.hypothesis == hyp) & (df.model == model)]
        if site is not None:
            x = x[x.site.fillna("") == site]
        if contrast_has is not None:
            x = x[x.contrast.str.contains(contrast_has)]
        if len(x) != 1:
            raise KeyError((hyp, model, site, contrast_has, len(x)))
        return x.iloc[0]

    # ------------------------------------------------------------------ tables
    def t_label_composition(self):
        bp = self.csv("label_audit_by_pathology")
        bs = self.csv("label_audit_by_study")
        lines = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
                 r"Label source & Pathology & \multicolumn{3}{c}{Source (MIMIC-CXR)} & \multicolumn{3}{c}{External (CheXpert Plus)}\\",
                 r"\cmidrule(lr){3-5}\cmidrule(lr){6-8}",
                 r" & & pos/neg & unc. & unm. & pos/neg & unc. & unm.\\", r"\midrule"]
        for ls in ("impression", "findings"):
            for t in TARGETS:
                s = bp[(bp.site == "source") & (bp.label_source == ls) & (bp.scope == "all_eligible") & (bp.pathology == t)].iloc[0]
                e = bp[(bp.site == "external") & (bp.label_source == ls) & (bp.scope == "all_eligible") & (bp.pathology == t)].iloc[0]
                lines.append(f"{ls.capitalize() if t == TARGETS[0] else ''} & {t} & "
                             f"{n(s.positive)}/{n(s.negative)} & {n(s.uncertain)} & {n(s.unmentioned)} & "
                             f"{n(e.positive)}/{n(e.negative)} & {n(e.uncertain)} & {n(e.unmentioned)}\\\\")
            ss = bs[(bs.site == "source") & (bs.label_source == ls) & (bs.scope == "all_eligible")].iloc[0]
            es = bs[(bs.site == "external") & (bs.label_source == ls) & (bs.scope == "all_eligible")].iloc[0]
            lines.append(f" & \\emph{{Studies with no labelled cell}} & \\multicolumn{{3}}{{r}}{{{n(ss.studies_with_no_labelled_cell)} of {n(ss.studies)} ({pct(ss.fraction_no_labelled_cell)})}} & "
                         f"\\multicolumn{{3}}{{r}}{{{n(es.studies_with_no_labelled_cell)} of {n(es.studies)} ({pct(es.fraction_no_labelled_cell)})}}\\\\")
            lines.append(f" & \\emph{{Labelled-cell density; positive rate}} & \\multicolumn{{3}}{{r}}{{{pct(ss.labelled_cell_density)}; {pct(ss.positive_rate_among_labelled)}}} & "
                         f"\\multicolumn{{3}}{{r}}{{{pct(es.labelled_cell_density)}; {pct(es.positive_rate_among_labelled)}}}\\\\")
            if ls == "impression":
                lines.append(r"\midrule")
            for site, s_ in (("Src", ss), ("Ext", es)):
                self.mac(f"NoLab{site}{ls.capitalize()}", pct(s_.fraction_no_labelled_cell))
                self.mac(f"Dens{site}{ls.capitalize()}", pct(s_.labelled_cell_density))
                self.mac(f"Pos{site}{ls.capitalize()}", pct(s_.positive_rate_among_labelled))
                self.mac(f"NoLabN{site}{ls.capitalize()}", n(s_.studies_with_no_labelled_cell))
                self.mac(f"Studies{site}{ls.capitalize()}", n(s_.studies))
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_label_composition", "\n".join(lines))
        ag = self.csv("label_agreement")
        for site in ("source", "external"):
            a = ag[ag.site == site]
            self.mac(f"AgreeMin{'Src' if site == 'source' else 'Ext'}", pct(a.agreement.min()))
            self.mac(f"AgreeMax{'Src' if site == 'source' else 'Ext'}", pct(a.agreement.max()))
        e = bp[(bp.site == "external") & (bp.label_source == "impression") & (bp.scope == "all_eligible")].set_index("pathology")
        s = bp[(bp.site == "source") & (bp.label_source == "impression") & (bp.scope == "all_eligible")].set_index("pathology")
        self.mac("ExtAtelUnc", n(e.loc["Atelectasis", "uncertain"]))
        self.mac("ExtAtelPos", n(e.loc["Atelectasis", "positive"]))
        self.mac("SrcEffUnmNeg", pct(s.loc["Pleural Effusion", "positive_rate_unmentioned_as_negative"]))
        self.mac("ExtEffUnmNeg", pct(e.loc["Pleural Effusion", "positive_rate_unmentioned_as_negative"]))
        self.mac("SrcEdemaUnmNeg", pct(s.loc["Edema", "positive_rate_unmentioned_as_negative"]))
        self.mac("ExtEdemaUnmNeg", pct(e.loc["Edema", "positive_rate_unmentioned_as_negative"]))
        self.mac("SrcAtelPosRate", pct(s.loc["Atelectasis", "positive_rate_among_labelled"]))
        self.mac("ExtAtelPosRate", pct(e.loc["Atelectasis", "positive_rate_among_labelled"]))

    def t_levels(self):
        L = self.lev[(self.lev.analysis == "primary") & (self.lev.label_variant == "primary")]
        lines = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
                 r" & & \multicolumn{3}{c}{Source} & \multicolumn{3}{c}{External}\\",
                 r"\cmidrule(lr){3-5}\cmidrule(lr){6-8}",
                 r"Model & Estimator & C0 & C1 & C2 & C0 & C1 & C2\\", r"\midrule"]
        for m in ("M1", "M2", "M3", "M4"):
            for est, lab in (("original", "original (defective)"), ("evaluable_study", "evaluable-study")):
                cells = []
                for site in ("source", "external"):
                    for c in ("C0", "C1", "C2"):
                        x = L[(L.estimator == est) & (L.site == site) & (L.model == m) & (L.condition == c)].iloc[0]
                        cells.append(f"{x.risk:.4f}")
                lines.append(f"{m if est == 'original' else ''} & {lab} & " + " & ".join(cells) + r"\\")
            covs = []
            for site in ("source", "external"):
                for c in ("C0", "C1", "C2"):
                    x = L[(L.estimator == "original") & (L.site == site) & (L.model == m) & (L.condition == c)].iloc[0]
                    covs.append(f"{x.coverage_all:.3f}")
            lines.append(r" & \emph{coverage (all)} & " + " & ".join(covs) + r"\\")
            if m != "M4":
                lines.append(r"\addlinespace")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_levels", "\n".join(lines))
        for est, tag in (("original", "Orig"), ("evaluable_study", "Eval")):
            for m in ("M1", "M2", "M3", "M4"):
                for site, st in (("source", "Src"), ("external", "Ext")):
                    x = L[(L.estimator == est) & (L.site == site) & (L.model == m) & (L.condition == "C0")].iloc[0]
                    self.mac(f"Risk{tag}{st}{m.replace('1', 'One').replace('2', 'Two').replace('3', 'Three').replace('4', 'Four')}",
                             f"{x.risk:.4f}")

    def t_hypotheses(self):
        o, e = self.H(est="original"), self.H(est="evaluable_study")
        spec = [("H1", "M3", None, None, True), ("H1", "M4", None, None, True),
                ("H2", "M3", None, "C1", True), ("H2", "M4", None, "C1", True),
                ("H3", "M3", None, None, False), ("H3", "M4", None, None, False),
                ("H4", "M3", "source", None, True), ("H4", "M4", "source", None, True),
                ("H4", "M3", "external", None, True), ("H4", "M4", "external", None, True),
                ("H2", "M3", None, "C2", False), ("H2", "M4", None, "C2", False),
                ("H1", "M1", None, None, False), ("H1", "M2", None, None, False)]
        lines = [r"\begin{tabular}{lllrlrl}", r"\toprule",
                 r"H & Model & Contrast & \multicolumn{2}{c}{Original estimator} & \multicolumn{2}{c}{Corrected (evaluable-study)}\\",
                 r"\cmidrule(lr){4-5}\cmidrule(lr){6-7}",
                 r" & & & Estimate (95\% CI) & V & Estimate (95\% CI) & V\\", r"\midrule"]
        names = {"H1": "ext $-$ src, C0", "H2": "interaction", "H3": "gap $-$ gap(M1)", "H4": "C2 $-$ C1"}
        group_breaks = {6: r"\midrule\multicolumn{7}{l}{\emph{Secondary: H4 (direction only, no materiality)}}\\",
                        10: r"\midrule\multicolumn{7}{l}{\emph{Not registered (computed by the original analysis code; descriptive)}}\\",
                        4: r"\midrule\multicolumn{7}{l}{\emph{H3 as coded after inspection (registered H3 $\equiv$ H2-C1)}}\\"}
        for i, (hh, m, site, c, reg) in enumerate(spec):
            if i in group_breaks:
                lines.append(group_breaks[i])
            ro = self.row(o, hh, m, site, c)
            re_ = self.row(e, hh, m, site, c)
            cname = names[hh] + (f", {c}" if c else "") + (f", {site}" if site else "")
            vo = VERDICT_TEX[ro.verdict]
            ve = VERDICT_TEX[re_.verdict]
            if hh == "H3":
                vo += f" [{VERDICT_TEX[ro.verdict_with_stage10_materiality]}]"
                ve += f" [{VERDICT_TEX[re_.verdict_with_stage10_materiality]}]"
            lines.append(f"{hh} & {m} & {cname} & {f(ro.point_estimate)} {ci(ro.ci_low, ro.ci_high)} & {vo} & "
                         f"{f(re_.point_estimate)} {ci(re_.ci_low, re_.ci_high)} & {ve}\\\\")
            key = f"{hh}{m}{site or ''}{c or ''}"
            key = key.replace("1", "One").replace("2", "Two").replace("3", "Three").replace("4", "Four")
            self.mac(f"{key}Orig", f"{f(ro.point_estimate)}~{ci(ro.ci_low, ro.ci_high)}")
            self.mac(f"{key}Eval", f"{f(re_.point_estimate)}~{ci(re_.ci_low, re_.ci_high)}")
            self.mac(f"{key}EvalPt", f(re_.point_estimate))
            self.mac(f"{key}OrigPt", f(ro.point_estimate))
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_hypotheses", "\n".join(lines))

    def t_sensitivity(self):
        specs = [("primary", "primary", "original", "Original estimator (as originally reported)"),
                 ("primary", "primary", "evaluable_study", "Evaluable-study (corrected)"),
                 ("primary", "primary", "cell_micro", "Cell-pooled"),
                 ("primary", "primary", "pathology_macro", "Pathology-macro"),
                 ("primary", "uncertain_negative", "evaluable_study", "Uncertain $\\to$ negative"),
                 ("primary", "uncertain_positive", "evaluable_study", "Uncertain $\\to$ positive"),
                 ("primary", "unmentioned_negative", "evaluable_study", "Unmentioned $\\to$ negative"),
                 ("coverage70", "primary", "evaluable_study", "Coverage 70\\%"),
                 ("coverage90", "primary", "evaluable_study", "Coverage 90\\%"),
                 ("T5", "primary", "evaluable_study", "Informativeness $T=5$"),
                 ("T10", "primary", "evaluable_study", "Informativeness $T=10$"),
                 ("findings_S1", "primary", "evaluable_study", "Findings labels (S1 pipeline)"),
                 ("findings_S1", "primary", "original", "Findings labels, original estimator"),
                 ("seed20260719", "primary", "evaluable_study", "Training seed 20260719"),
                 ("seed20260719", "primary", "original", "Seed 20260719, original estimator")]
        lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
                 r"Specification & H1 M3 & H1 M4 & H3 M3 & H3 M4\\", r"\midrule"]
        rows_fig = []
        for a, v, est, lab in specs:
            df = self.H(a, v, est)
            cells = []
            for hh, m in (("H1", "M3"), ("H1", "M4"), ("H3", "M3"), ("H3", "M4")):
                x = df[(df.hypothesis == hh) & (df.model == m)]
                if len(x) == 0:
                    cells.append("--")
                    continue
                x = x.iloc[0]
                cells.append(f"{f(x.point_estimate)} {ci(x.ci_low, x.ci_high, 3)}")
            lines.append(f"{lab} & " + " & ".join(cells) + r"\\")
            tag = TAGS[(a, v, est)]
            for hh, m in (("H1", "M1"), ("H1", "M2"), ("H1", "M3"), ("H1", "M4"), ("H3", "M3"), ("H3", "M4")):
                x = df[(df.hypothesis == hh) & (df.model == m)]
                if len(x):
                    x = x.iloc[0]
                    mn = m.replace("1", "One").replace("2", "Two").replace("3", "Three").replace("4", "Four")
                    hn = hh.replace("1", "One").replace("3", "Three")
                    self.mac(f"Sens{tag}{hn}{mn}", f"{f(x.point_estimate)}~{ci(x.ci_low, x.ci_high)}")
                    self.mac(f"Sens{tag}{hn}{mn}Pt", f(x.point_estimate))
            for m in ("M1", "M2", "M3", "M4"):
                x = df[(df.hypothesis == "H1") & (df.model == m)]
                if len(x):
                    x = x.iloc[0]
                    rows_fig.append({"spec": lab.replace("$\\to$", "→").replace("\\%", "%").replace("$T=", "T=").replace("$", ""),
                                     "model": m, "pt": x.point_estimate, "lo": x.ci_low, "hi": x.ci_high,
                                     "original": est == "original"})
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_sensitivity", "\n".join(lines))
        return pd.DataFrame(rows_fig)

    def t_label_source(self):
        d = self.csv("label_source_contrasts")
        configs = [("A0_primary", "A0", "primary (impression labels, primary cohort, impression thresholds)"),
                   ("A1_label_swap_only", "A1", "findings labels only"),
                   ("A1c_common_cells_impression", "A1c-I", "common labelled cells, impression labels"),
                   ("A1c_common_cells_findings", "A1c-F", "common labelled cells, findings labels"),
                   ("A2x_cohort_only", "A2x", "findings cohort only"),
                   ("A2_cohort_and_labels", "A2", "findings cohort + labels"),
                   ("A3_published_S1", "A3", "+ findings thresholds and cutoffs (= original S1)"),
                   ("B2_labels_and_thresholds_on_primary_cohort", "B2", "findings labels + thresholds, primary cohort")]
        lines = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
                 r" & & \multicolumn{2}{c}{Evaluable studies} & \multicolumn{2}{c}{H1 M3} & \multicolumn{2}{c}{H1 M4}\\",
                 r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}",
                 r"Step & Change from A0 & Src & Ext & Original & Corrected & Original & Corrected\\", r"\midrule"]
        for key, tag, lab in configs:
            x = d[d.config == key]
            r0 = x.iloc[0]
            cells = []
            for m in ("M3", "M4"):
                for est in ("original", "evaluable_study"):
                    y = x[(x.hypothesis == "H1") & (x.model == m) & (x.estimator == est)].iloc[0]
                    cells.append(f"{f(y.point_estimate)}")
                    self.mac(f"LS{tag.replace('-', '').replace('0', 'Zero').replace('1', 'One').replace('2', 'Two').replace('3', 'Three').replace('c', 'c')}{m.replace('3', 'Three').replace('4', 'Four')}{'Orig' if est == 'original' else 'Eval'}",
                             f"{f(y.point_estimate)}~{ci(y.ci_low, y.ci_high)}")
            lines.append(f"{tag} & {lab} & {pct(r0.src_evaluable_fraction, 0)} & {pct(r0.ext_evaluable_fraction, 0)} & " + " & ".join(cells) + r"\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_label_source", "\n".join(lines))
        meta = json.loads((self.r / "label_source_meta.json").read_text())
        di = meta["external_decision_identity"]
        self.mac("SOneCellsChanged", f"{min(v['cells_with_different_decision_findings_vs_impression_thresholds'] for v in di.values()):,}--{max(v['cells_with_different_decision_findings_vs_impression_thresholds'] for v in di.values()):,}")
        self.mac("SOneStudiesChanged", f"{min(v['studies_with_different_acceptance_findings_vs_impression_cutoff'] for v in di.values()):,}--{max(v['studies_with_different_acceptance_findings_vs_impression_cutoff'] for v in di.values()):,}")
        self.mac("SOneMOneCells", f"{di['M1']['cells_with_different_decision_findings_vs_impression_thresholds']:,}")
        self.mac("SOneMOneStudies", f"{di['M1']['studies_with_different_acceptance_findings_vs_impression_cutoff']:,}")
        mx = max(v['max_abs_prob_diff'] for v in di.values())
        mant, ex = f"{mx:.1e}".split("e")
        self.mac("SOneMaxProbDiff", f"${mant}\\times10^{{{int(ex)}}}$")

    def t_operating(self):
        oc = self.csv("operating_characteristics")
        lines = [r"\begin{tabular}{lllrrrrrr}", r"\toprule",
                 r" & & & \multicolumn{3}{c}{Source} & \multicolumn{3}{c}{External}\\",
                 r"\cmidrule(lr){4-6}\cmidrule(lr){7-9}",
                 r"Model & Pathology & $t_j$ & Sens. & Spec. & Pos.\ call & Sens. & Spec. & Pos.\ call\\", r"\midrule"]
        for m in ("M3", "M4"):
            for t in TARGETS:
                s = oc[(oc.label_variant == "primary") & (oc.scope == "accepted") & (oc.site == "source") & (oc.model == m) & (oc.pathology == t)].iloc[0]
                e = oc[(oc.label_variant == "primary") & (oc.scope == "accepted") & (oc.site == "external") & (oc.model == m) & (oc.pathology == t)].iloc[0]
                lines.append(f"{m if t == TARGETS[0] else ''} & {t} & {s.threshold:.3f} & {s.sensitivity:.3f} & {s.specificity:.3f} & {s.decided_positive_rate_in_scope:.3f} & "
                             f"{e.sensitivity:.3f} & {e.specificity:.3f} & {e.decided_positive_rate_in_scope:.3f}\\\\")
            if m == "M3":
                lines.append(r"\addlinespace")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_operating", "\n".join(lines))
        g = lambda site, t, k: oc[(oc.label_variant == "primary") & (oc.scope == "accepted") & (oc.site == site) & (oc.model == "M4") & (oc.pathology == t)].iloc[0][k]
        self.mac("MFourCardSpecSrc", f"{g('source', 'Cardiomegaly', 'specificity'):.2f}")
        self.mac("MFourCardSpecExt", f"{g('external', 'Cardiomegaly', 'specificity'):.2f}")
        self.mac("MFourEffSpecSrc", f"{g('source', 'Pleural Effusion', 'specificity'):.2f}")
        self.mac("MFourEffSpecExt", f"{g('external', 'Pleural Effusion', 'specificity'):.2f}")
        self.mac("MFourEdemaSpecSrc", f"{g('source', 'Edema', 'specificity'):.2f}")
        self.mac("MFourEdemaSpecExt", f"{g('external', 'Edema', 'specificity'):.2f}")
        self.mac("MFourCardSensSrc", f"{g('source', 'Cardiomegaly', 'sensitivity'):.2f}")
        self.mac("MFourCardSensExt", f"{g('external', 'Cardiomegaly', 'sensitivity'):.2f}")
        self.mac("MFourCardPosSrc", pct(g('source', 'Cardiomegaly', 'decided_positive_rate_in_scope'), 0))
        self.mac("MFourCardPosExt", pct(g('external', 'Cardiomegaly', 'decided_positive_rate_in_scope'), 0))
        return oc

    def t_coverage_context(self):
        cg = self.csv("coverage_gap")
        cg = cg[(cg.analysis == "primary") & (cg.label_variant == "primary")]
        cd = self.csv("context_decomposition")
        cd = cd[cd.estimator == "evaluable_study"]
        lines = [r"\begin{tabular}{lllrrrrr}", r"\toprule",
                 r"Site & Model & Cond. & Policy effect & Pred.\ on C0 set & Selection (o1) & Selection (o2) & Jaccard\\", r"\midrule"]
        for site in ("source", "external"):
            for m in ("M3", "M4"):
                for c in ("C1", "C2"):
                    x = cd[(cd.site == site) & (cd.model == m) & (cd.condition == c)].set_index("term")
                    lines.append(f"{site if (m, c) == ('M3', 'C1') else ''} & {m} & {c} & "
                                 f"{f(x.loc['policy_effect', 'estimate'])} & {f(x.loc['order1_prediction_on_C0_set', 'estimate'])} & "
                                 f"{f(x.loc['order1_selection', 'estimate'])} & {f(x.loc['order2_selection', 'estimate'])} & "
                                 f"{x.loc['policy_effect', 'jaccard_acceptance']:.2f}\\\\")
            if site == "source":
                lines.append(r"\addlinespace")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_context", "\n".join(lines))
        pv = cd.pivot_table(index=["site", "model", "condition"], columns="term", values="estimate").reset_index()
        pv["gap"] = (pv.order1_selection - pv.order2_selection).abs()
        self.mac("OrderGapMM", f"{pv[pv.model.isin(['M3', 'M4'])].gap.max():.3f}")
        self.mac("OrderGapMTwo", f"{pv[pv.model == 'M2'].gap.max():.3f}")
        jac = cd.drop_duplicates(["site", "model", "condition"]).jaccard_acceptance
        self.mac("JaccardMin", f"{jac.min():.2f}")
        self.mac("JaccardMax", f"{jac.max():.2f}")
        allcg = self.csv("coverage_gap")
        if (self.r / "followup_m2m3_coverage_gap.csv").exists():
            fc = self.csv("followup_m2m3_coverage_gap")
            fc = fc[fc.model.isin(["M2", "M3"])].assign(analysis="seed20260719", label_variant="primary")
            allcg = pd.concat([allcg, fc], ignore_index=True)
        sd = allcg[(allcg.analysis == "seed20260719") & (allcg.condition == "C0")]
        self.mac("SeedCovDriftMax", f"{np.max(np.abs(np.r_[sd.coverage_source.values, sd.coverage_external.values] - 0.8)):.3f}")
        g = lambda m, c, col: float(cg[(cg.model == m) & (cg.condition == c)].iloc[0][col])
        self.mac("MTwoCOneCovSrc", f"{g('M2', 'C1', 'coverage_source'):.3f}")
        self.mac("MTwoCOneCovExt", f"{g('M2', 'C1', 'coverage_external'):.3f}")
        self.mac("MThreeCTwoCovSrc", f"{g('M3', 'C2', 'coverage_source'):.3f}")
        self.mac("MThreeCTwoCovExt", f"{g('M3', 'C2', 'coverage_external'):.3f}")
        self.mac("MFourCOneCovExt", f"{g('M4', 'C1', 'coverage_external'):.3f}")
        c0 = cg[cg.condition == "C0"]
        self.mac("CovDriftMaxCZero", f"{np.max(np.abs(np.r_[c0.coverage_source.values, c0.coverage_external.values] - 0.8)):.3f}")

    def t_comparators(self):
        d = self.csv("comparators")
        rk = self.csv("comparator_ranking")
        fits = json.loads((self.r / "comparator_fits.json").read_text())
        lab = {"frozen": "Frozen (|2p$-$1|)", "temp_margin": "Temperature-scaled margin",
               "expected_loss": "Expected-loss (decision-aware)", "conformal": "Split-conformal singletons"}
        lines = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
                 r" & & \multicolumn{2}{c}{Coverage (C0)} & \multicolumn{2}{c}{Failure AUROC} & & \\",
                 r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}",
                 r"Model & Policy & Src & Ext & Src & Ext & H1 corrected (95\% CI) & Ext.\ coverage C1\\", r"\midrule"]
        for m in ("M3", "M4"):
            for p, pl in lab.items():
                x = d[(d.model == m) & (d.policy == p) & (d.condition == "C0")].iloc[0]
                x1 = d[(d.model == m) & (d.policy == p) & (d.condition == "C1")].iloc[0]
                rs = rk[(rk.model == m) & (rk.policy == p) & (rk.site == "source")].iloc[0]
                re_ = rk[(rk.model == m) & (rk.policy == p) & (rk.site == "external")].iloc[0]
                lines.append(f"{m if p == 'frozen' else ''} & {pl} & {x.coverage_source:.3f} & {x.coverage_external:.3f} & "
                             f"{rs.failure_auroc:.3f} & {re_.failure_auroc:.3f} & {f(x.gap_evaluable_study)} {ci(x.gap_evaluable_study_ci_low, x.gap_evaluable_study_ci_high, 3)} & {x1.coverage_external:.3f}\\\\")
            if m == "M3":
                lines.append(r"\addlinespace")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_comparators", "\n".join(lines))
        accs = [fi["conformal_calibration_acceptance"] for fi in fits]
        self.mac("ConfAccMin", pct(min(accs), 0))
        self.mac("ConfAccMax", pct(max(accs), 0))
        fr = rk[rk.policy == "frozen"].failure_auroc
        el = rk[rk.policy == "expected_loss"].failure_auroc
        self.mac("FailAUROCFrozenMin", f"{fr.min():.2f}")
        self.mac("FailAUROCFrozenMax", f"{fr.max():.2f}")
        self.mac("FailAUROCELMin", f"{el.min():.2f}")
        self.mac("FailAUROCELMax", f"{el.max():.2f}")
        x = d[(d.model == "M4") & (d.policy == "expected_loss") & (d.condition == "C0")].iloc[0]
        self.mac("ELMFourExtCov", f"{x.coverage_external:.3f}")

    def t_uncertainty(self):
        cu = self.csv("calibration_uncertainty")
        e = self.H(est="evaluable_study")
        o = self.H(est="original")
        lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
                 r"Model & Estimator & H1 & SD (evaluation bootstrap) & SD (calibration resample) & Calibration 2.5--97.5\%\\", r"\midrule"]
        for m in ("M1", "M2", "M3", "M4"):
            for est, df in (("original", o), ("evaluable_study", e)):
                x = df[(df.hypothesis == "H1") & (df.model == m)].iloc[0]
                c = cu[(cu.model == m) & (cu.estimator == est)].iloc[0]
                sd_eval = (x.ci_high - x.ci_low) / 3.92
                lines.append(f"{m if est == 'original' else ''} & {'original' if est == 'original' else 'evaluable-study'} & {f(x.point_estimate)} & {sd_eval:.4f} & {c.h1_sd_calibration:.4f} & {ci(c.h1_q025, c.h1_q975)}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_uncertainty", "\n".join(lines))
        ratios = []
        for m in ("M1", "M2", "M3", "M4"):
            x = e[(e.hypothesis == "H1") & (e.model == m)].iloc[0]
            c = cu[(cu.model == m) & (cu.estimator == "evaluable_study")].iloc[0]
            ratios.append(c.h1_sd_calibration / ((x.ci_high - x.ci_low) / 3.92))
        self.mac("CalRatioMin", f"{min(ratios):.1f}")
        self.mac("CalRatioMax", f"{max(ratios):.1f}")
        c = cu[(cu.model == "M4") & (cu.estimator == "evaluable_study")].iloc[0]
        self.mac("CalSDMFour", f"{c.h1_sd_calibration:.3f}")
        x = e[(e.hypothesis == "H1") & (e.model == "M4")].iloc[0]
        self.mac("EvalSDMFour", f"{(x.ci_high - x.ci_low) / 3.92:.3f}")
        ths = json.loads(c.threshold_sd_by_pathology) if isinstance(c.threshold_sd_by_pathology, str) else c.threshold_sd_by_pathology
        self.mac("ThrSDMaxMFour", f"{max(ths):.3f}")

    def t_context_scan(self):
        d = self.csv("context_scan")
        names = {"report_section_header": "Header", "conclusion_language": "Concl",
                 "comparison_language": "Compar", "query_language": "Query",
                 "names_a_target_finding": "Target"}
        for _, r in d.iterrows():
            self.mac(f"Scan{names[r.pattern]}{'Src' if r.site == 'source' else 'Ext'}", pct(r.share, 2 if r.share < 0.01 else 1))

    def t_c2(self):
        d = self.csv("c2_audit").set_index("site")
        for site, tag in (("source", "Src"), ("external", "Ext")):
            x = d.loc[site]
            self.mac(f"CTwoIdent{tag}", n(x.rows_identical_text))
            self.mac(f"CTwoSamePat{tag}", n(x.rows_same_patient_donor))
            self.mac(f"CTwoMultiDonor{tag}", n(x.studies_whose_images_received_multiple_donor_studies))
            self.mac(f"CTwoMultiImg{tag}", n(x.multi_image_studies))
            self.mac(f"CTwoTermDiff{tag}", pct(x.fraction_rows_donor_target_term_profile_differs, 0))
            self.mac(f"CTwoTokens{tag}", f"{x.mean_effective_tokens_recipient:.1f}")
            self.mac(f"CTwoRows{tag}", n(x.image_rows))

    def t_subgroups(self):
        v = self.csv("view_strata")
        v = v[v.estimator == "evaluable_study"]
        lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
                 r"Stratum & Model & Studies src/ext & Risk src & Risk ext & Transfer gap (95\% CI)\\", r"\midrule"]
        for st in ("AP_only", "PA_only"):
            for m in ("M1", "M2", "M3", "M4"):
                x = v[(v.stratum == st) & (v.model == m)].iloc[0]
                lines.append(f"{st.replace('_only', '-only') if m == 'M1' else ''} & {m} & {n(x.studies_source)}/{n(x.studies_external)} & {x.risk_source:.4f} & {x.risk_external:.4f} & {f(x.transfer_gap)} {ci(x.ci_low, x.ci_high)}\\\\")
            if st == "AP_only":
                lines.append(r"\addlinespace")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_views", "\n".join(lines))
        x = v[(v.stratum == "AP_only") & (v.model == "M4")].iloc[0]
        y = v[(v.stratum == "PA_only") & (v.model == "M4")].iloc[0]
        self.mac("ViewAPMFour", f"{f(x.transfer_gap)}~{ci(x.ci_low, x.ci_high)}")
        self.mac("ViewPAMFour", f"{f(y.transfer_gap)}~{ci(y.ci_low, y.ci_high)}")
        self.mac("APShareSrc", pct(x.studies_source / 14766, 0))
        self.mac("APShareExt", pct(x.studies_external / 132923, 0))
        dd = self.csv("external_demographic_disparity")
        lines = [r"\begin{tabular}{llrrl}", r"\toprule",
                 r"Variable & Model & Coverage disparity (MET016) & Worst-group risk (MET017) & Worst group\\", r"\midrule"]
        for var in ("sex", "age_band", "race", "insurance_type"):
            for m in ("M3", "M4"):
                x = dd[(dd.variable == var) & (dd.model == m)].iloc[0]
                lines.append(f"{var.replace('_', ' ') if m == 'M3' else ''} & {m} & {x.MET016_coverage_disparity:.3f} {ci(x.MET016_ci_low, x.MET016_ci_high, 3)} & "
                             f"{x.MET017_worst_group_risk:.3f} {ci(x.MET017_ci_low, x.MET017_ci_high, 3)} & {x.MET017_worst_group}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_demographics", "\n".join(lines))
        y = dd[(dd.variable == "age_band") & (dd.model == "M4")].iloc[0]
        self.mac("AgeCovDispMFour", f"{y.MET016_coverage_disparity:.3f}")
        y = dd[(dd.variable == "insurance_type") & (dd.model == "M4")].iloc[0]
        self.mac("InsCovDispMFour", f"{y.MET016_coverage_disparity:.3f}")
        x = dd[(dd.variable == "age_band") & (dd.model == "M3")].iloc[0]
        self.mac("AgeCovDispMThree", f"{x.MET016_coverage_disparity:.3f}~{ci(x.MET016_ci_low, x.MET016_ci_high, 3)}")

    def t_pathology(self):
        d = self.csv("pathology_contrasts")
        d = d[(d.hypothesis == "H1") & (d.analysis == "primary")]
        lines = [r"\begin{tabular}{llrrr}", r"\toprule",
                 r"Model & Pathology & Primary labels (95\% CI) & Holm $p$ & Unmentioned $\to$ negative\\", r"\midrule"]
        for m in ("M3", "M4"):
            for t in TARGETS:
                a = d[(d.model == m) & (d.pathology == t) & (d.label_variant == "primary")].iloc[0]
                b = d[(d.model == m) & (d.pathology == t) & (d.label_variant == "unmentioned_negative")].iloc[0]
                hp = f"{a.holm_p_across_pathologies:.3f}" if a.holm_p_across_pathologies >= 0.001 else "$<$0.001"
                lines.append(f"{m if t == TARGETS[0] else ''} & {t} & {f(a.point_estimate, 3)} {ci(a.ci_low, a.ci_high, 3)} & {hp} & {f(b.point_estimate, 3)} {ci(b.ci_low, b.ci_high, 3)}\\\\")
            if m == "M3":
                lines.append(r"\addlinespace")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_pathology", "\n".join(lines))
        g = lambda m, t, v: d[(d.model == m) & (d.pathology == t) & (d.label_variant == v)].iloc[0].point_estimate
        self.mac("PathMFourCard", f(g("M4", "Cardiomegaly", "primary"), 3))
        self.mac("PathMFourAtel", f(g("M4", "Atelectasis", "primary"), 3))
        un = [g("M4", t, "unmentioned_negative") for t in TARGETS]
        self.mac("PathMFourUnmMax", f(max(un), 2))
        self.mac("PathMFourUnmMin", f(min(un), 2))

    def t_multiplicity(self):
        lines = [r"\begin{tabular}{lllrrr}", r"\toprule",
                 r"Estimator & H & Model & Estimate & 95\% CI & Bonferroni ($k=6$) 99.17\% CI\\", r"\midrule"]
        from ..analysis.bootstrap import holm_adjust
        for est in ("original", "evaluable_study"):
            df = self.H(est=est)
            fam = []
            for hh, m, c in (("H1", "M3", None), ("H1", "M4", None), ("H2", "M3", "C1"), ("H2", "M4", "C1"),
                             ("H3", "M3", None), ("H3", "M4", None)):
                x = self.row(df, hh, m, None, c)
                fam.append(x)
                lines.append(f"{'original' if est == 'original' else 'evaluable-study'} & {hh}{'-C1' if c else ''} & {m} & {f(x.point_estimate)} & {ci(x.ci_low, x.ci_high)} & {ci(x.ci_low_bonferroni6, x.ci_high_bonferroni6)}\\\\")
            if est == "original":
                lines.append(r"\addlinespace")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("tab_multiplicity", "\n".join(lines))

    def t_cohort(self):
        wf = pd.read_csv(self.root / "results/c3e_mimic/stage3c/stage3c_exclusion_waterfall.csv")
        ps = pd.read_csv(self.root / "results/c3e_mimic/stage3e/stage3e_partition_summary.csv")
        ext = json.loads((self.root / "results/c3e_chexpert_plus/stage9b_evaluation/stage9b_evaluation.json").read_text())["cohort"]
        lab = {"all_studies": "All reports/studies", "recognised_structure": "No recognised section header",
               "separable_label_sections": "Findings and impression merged",
               "frontal_view_available": "No frontal (AP/PA) image",
               "official_split_assigned": "Official split assigned",
               "context_informative_T3": "Context not informative ($<3$ effective tokens)",
               "primary_label_source_present": "No impression section"}
        lines = [r"\begin{tabular}{lrr}", r"\toprule", r"Step (source site) & Removed & Remaining\\", r"\midrule"]
        for _, r in wf.iterrows():
            lines.append(f"{lab[r.step]} & {'--' if r.studies_removed == 0 and r.step == 'all_studies' else n(r.studies_removed)} & {n(r.studies_after)}\\\\")
        lines += [r"\midrule", r"Tier & Patients / studies / frontal images & \\"]
        names = {"model_train": "Model training", "threshold_calibration": "Threshold calibration",
                 "prespecified_eval": "Prespecified evaluation (primary)",
                 "official_validate": "Official validate (not analysed)", "official_test": "Official test (not analysed)"}
        for _, r in ps.iterrows():
            lines.append(f"{names[r.tier]} & {n(r.patients)} / {n(r.studies)} / {n(r.frontal_images)} & \\\\")
        lines += [r"\midrule", r"External site (CheXpert Plus) & & \\",
                  f"Usable frontal images / studies / patients & {n(ext['images'])} / {n(ext['studies'])} / {n(ext['patients'])} & \\\\",
                  f"Intervention cohort (N1 at $T=3$): images / studies / patients & {n(ext['n1_images'])} / {n(ext['n1_studies'])} / {n(ext['n1_patients'])} & \\\\",
                  r"\bottomrule", r"\end{tabular}"]
        self.write("tab_cohort", "\n".join(lines))
        st = ext["natural_states_by_study"]
        self.mac("ExtNOne", n(st["N1"]))
        self.mac("ExtNTwo", n(st["N2"]))
        self.mac("ExtNThree", n(st["N3"]))
        self.mac("ExtStudies", n(ext["studies"]))
        self.mac("ExtPatients", n(ext["patients"]))
        self.mac("ExtImages", n(ext["images"]))
        self.mac("ExtNOnePatients", n(ext["n1_patients"]))
        self.mac("ExtNOneImages", n(ext["n1_images"]))


    # ------------------------------------------------------------------ supplement tables
    def s_tables(self):
        # S: H1/H3/H4 for every model under every specification.
        rows = []
        specs = [k for k in TAGS]
        lab = {("primary", "primary", "original"): "original", ("primary", "primary", "evaluable_study"): "evaluable-study",
               ("primary", "primary", "cell_micro"): "cell-pooled", ("primary", "primary", "pathology_macro"): "pathology-macro",
               ("primary", "uncertain_negative", "evaluable_study"): "unc.$\\to$neg", ("primary", "uncertain_positive", "evaluable_study"): "unc.$\\to$pos",
               ("primary", "unmentioned_negative", "evaluable_study"): "unm.$\\to$neg", ("coverage70", "primary", "evaluable_study"): "cov.\\ 70\\%",
               ("coverage90", "primary", "evaluable_study"): "cov.\\ 90\\%", ("T5", "primary", "evaluable_study"): "$T=5$", ("T10", "primary", "evaluable_study"): "$T=10$",
               ("findings_S1", "primary", "evaluable_study"): "findings", ("findings_S1", "primary", "original"): "findings, original",
               ("seed20260719", "primary", "evaluable_study"): "seed 2", ("seed20260719", "primary", "original"): "seed 2, original"}
        lines = [r"\begin{longtable}{llrrrr}", r"\toprule", r"Contrast & Specification & M1 & M2 & M3 & M4\\", r"\midrule", r"\endhead"]
        for hh, site, cont in (("H1", "", None), ("H2", "", "C1"), ("H2", "", "C2"), ("H3", "", None), ("H4", "source", None), ("H4", "external", None)):
            first = True
            for key in specs:
                df = self.H(*key)
                cells = []
                for m in ("M1", "M2", "M3", "M4"):
                    x = df[(df.hypothesis == hh) & (df.model == m) & (df.site.fillna("") == site)]
                    if cont:
                        x = x[x.contrast.str.contains(cont)]
                    cells.append("--" if len(x) == 0 else f"{f(x.iloc[0].point_estimate, 3)} {ci(x.iloc[0].ci_low, x.iloc[0].ci_high, 3)}")
                name = f"{hh}{'-' + cont if cont else ''}{' ' + site if site else ''}" if first else ""
                lines.append(f"{name} & {lab[key]} & " + " & ".join(cells) + r"\\")
                first = False
            lines.append(r"\midrule")
        lines[-1] = r"\bottomrule"
        lines.append(r"\end{longtable}")
        self.write("supp_all_specs", "\n".join(lines))

        # S: label-source decomposition with intervals, all models.
        d = self.csv("label_source_contrasts")
        lines = [r"\begin{longtable}{llrrrr}", r"\toprule", r"Step & Estimator & M1 & M2 & M3 & M4\\", r"\midrule", r"\endhead"]
        for key in d.config.drop_duplicates():
            first = True
            for est in ("original", "evaluable_study", "cell_micro"):
                cells = []
                for m in ("M1", "M2", "M3", "M4"):
                    x = d[(d.config == key) & (d.estimator == est) & (d.hypothesis == "H1") & (d.model == m)].iloc[0]
                    cells.append(f"{f(x.point_estimate, 3)} {ci(x.ci_low, x.ci_high, 3)}")
                code = {"A1c_common_cells_impression": "A1c-I",
                        "A1c_common_cells_findings": "A1c-F"}.get(key, key.split("_")[0])
                lines.append(f"{code if first else ''} & {est.replace('_', '-')} & " + " & ".join(cells) + r"\\")
                first = False
            lines.append(r"\midrule")
        lines[-1] = r"\bottomrule"
        lines.append(r"\end{longtable}")
        self.write("supp_label_source", "\n".join(lines))

        # S: operating characteristics under unmentioned-as-negative.
        oc = self.csv("operating_characteristics")
        lines = [r"\begin{tabular}{llrrrr}", r"\toprule", r"Model & Pathology & Sens.\\ src & Spec.\\ src & Sens.\\ ext & Spec.\\ ext\\", r"\midrule"]
        for m in ("M3", "M4"):
            for t in TARGETS:
                g = lambda site: oc[(oc.label_variant == "unmentioned_negative") & (oc.scope == "accepted") & (oc.site == site) & (oc.model == m) & (oc.pathology == t)].iloc[0]
                s_, e_ = g("source"), g("external")
                lines.append(f"{m if t == TARGETS[0] else ''} & {t} & {s_.sensitivity:.3f} & {s_.specificity:.3f} & {e_.sensitivity:.3f} & {e_.specificity:.3f}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("supp_oc_unmentioned", "\n".join(lines))

        # S: context decomposition with intervals.
        cd = self.csv("context_decomposition")
        cd = cd[cd.estimator == "evaluable_study"]
        lines = [r"\begin{longtable}{lllrr}", r"\toprule", r"Site/model/cond. & Term & & Estimate & 95\\% CI\\", r"\midrule", r"\endhead"]
        for (site, m, c), g in cd.groupby(["site", "model", "condition"], sort=True):
            first = True
            for _, r in g.iterrows():
                lines.append(f"{site + ' ' + m + ' ' + c if first else ''} & {r.term.replace('_', ' ')} & & {f(r.estimate)} & {ci(r.ci_low, r.ci_high)}\\\\")
                first = False
        lines += [r"\bottomrule", r"\end{longtable}"]
        self.write("supp_context", "\n".join(lines))

        # S: C2 audit.
        c2 = self.csv("c2_audit").set_index("site")
        keys = [("image_rows", "image rows"), ("studies", "studies"), ("rows_identical_text", "rows with identical text after C2"),
                ("rows_identical_text_from_different_patient", "\\quad of which donated by a different patient"),
                ("rows_same_patient_donor", "rows with a same-patient donor"), ("rows_self_donor", "rows donating to themselves"),
                ("multi_image_studies", "multi-image studies"),
                ("studies_whose_images_received_multiple_donor_studies", "\\quad receiving context from $>1$ donor study"),
                ("studies_whose_images_received_different_context_strings", "\\quad receiving $>1$ distinct context string"),
                ("fraction_rows_donor_target_term_profile_differs", "rows whose target-term profile changed"),
                ("mean_effective_tokens_recipient", "mean effective tokens")]
        lines = [r"\begin{tabular}{lrr}", r"\toprule", r"Quantity & Source & External\\", r"\midrule"]
        for k, lab_ in keys:
            a, b = c2.loc["source", k], c2.loc["external", k]
            fmt = (lambda v: f"{float(v):.3f}") if "fraction" in k or "mean" in k else (lambda v: n(v))
            lines.append(f"{lab_} & {fmt(a)} & {fmt(b)}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("supp_c2", "\n".join(lines))

        # S: threshold-free metrics and failure detection.
        tf = self.csv("threshold_free")
        lines = [r"\begin{tabular}{lllrrr}", r"\toprule", r"Score & Metric & Model & Source & External & Difference (95\\% CI)\\", r"\midrule"]
        for _, r in tf.iterrows():
            lines.append(f"{r.score.replace('_', ' ')} & {r.metric.upper()} & {r.model} & {r.source:.4f} & {r.external:.4f} & {f(r.difference)} {ci(r.ci_low, r.ci_high)}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("supp_threshold_free", "\n".join(lines))

        fd = self.csv("failure_detection")
        fd = fd[fd.level == "cell"].pivot_table(index=["model", "pathology"], columns=["site", "score"], values="auroc_correct_vs_any_error")
        lines = [r"\begin{tabular}{llrrrr}", r"\toprule",
                 r" & & \multicolumn{2}{c}{Source} & \multicolumn{2}{c}{External}\\", r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}",
                 r"Model & Pathology & $|2p-1|$ & $|\mathrm{logit}\,p-\mathrm{logit}\,t|$ & $|2p-1|$ & $|\mathrm{logit}\,p-\mathrm{logit}\,t|$\\", r"\midrule"]
        for (m, t), r in fd.iterrows():
            lines.append(f"{m} & {t} & {r[('source', 'abs_2p_minus_1')]:.3f} & {r[('source', 'threshold_margin')]:.3f} & {r[('external', 'abs_2p_minus_1')]:.3f} & {r[('external', 'threshold_margin')]:.3f}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("supp_failure_cells", "\n".join(lines))

        # S: Stage 6 runs recovered from logs.
        st = json.loads((self.r / "stage6_runs_from_logs.json").read_text())
        lines = [r"\begin{tabular}{llrrl}", r"\toprule", r"Model & Log / run & Epochs & Best epoch (AUROC) & Validation macro AUROC by epoch\\", r"\midrule"]
        for r in st:
            curve = ", ".join(f"{e['val_auroc_macro']:.3f}" for e in r["curve"])
            lines.append(f"{r['model']} & {Path(r['log']).name.replace('_', '\\_')} / {r['run_index']} & {r['epochs']} & {r['best_epoch']} ({r['best_val_auroc_macro']:.4f}) & {curve}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("supp_stage6", "\n".join(lines))

        # S: comparator fits.
        fits = json.loads((self.r / "comparator_fits.json").read_text())
        lines = [r"\begin{tabular}{lrrrl}", r"\toprule", r"Model & Conformal $\alpha$ & Calibration acceptance & Expected-loss cutoff & Temperatures (Card., Edema, Cons., Atel., Eff.)\\", r"\midrule"]
        for fi in fits:
            temps = ", ".join(f"{fi['temperature'][t]:.2f}" for t in TARGETS)
            lines.append(f"{fi['model']} & {fi['conformal_alpha']:.3f} & {fi['conformal_calibration_acceptance']:.3f} & {fi['cutoff_expected_loss']:.3f} & {temps}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("supp_comparator_fits", "\n".join(lines))

        # S: reproduction checks.
        rp = self.csv("stage10_reproduction")
        s7 = self.csv("stage7_reproduction")
        al = self.csv("alignment_checks")
        lines = [r"\begin{tabular}{llr}", r"\toprule", r"Check & Item & Result\\", r"\midrule"]
        for _, r in rp.iterrows():
            lines.append(f"Stage 10 replay & {r.analysis.replace('_', ' ')} ({r.stage10_rows} rows) & max $|\\Delta|$ = {r.max_abs_difference:g}\\\\")
        for _, r in s7.iterrows():
            lines.append(f"Stage 7 re-selection & {r.model}{' seed 20260719' if str(r.train_seed) not in ('nan', 'None', '') else ''} & thresholds $|\\Delta|$={r.max_abs_threshold_diff:g}; cutoffs $|\\Delta|$={r.max_abs_cutoff_diff:g}\\\\")
        for _, r in al.iterrows():
            lines.append(f"Cohort alignment & {r.site} {r.label_source} $T={r.threshold}${(' ' + r.cache_suffix.replace('__', '').replace('seed', 'seed ')) if isinstance(r.cache_suffix, str) and 'seed' in r.cache_suffix else ''} & {n(r.rows)} rows exact\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        self.write("supp_reproduction", "\n".join(lines))

    def s_gpu_status(self):
        lines = []
        perm_path = self.r / "followup_c2_permutations.csv"
        perm = pd.read_csv(perm_path) if perm_path.exists() else pd.DataFrame()
        done = perm[perm.status == "done"] if len(perm) else perm
        lines.append(r"\paragraph{Additional C2 donor permutations (post hoc).}")
        if len(done):
            sub = done[(done.estimator == "evaluable_study") & (done.contrast.str.startswith("H4"))]
            lines += [r"\begin{center}\small\begin{tabular}{llrrl}", r"\toprule",
                      r"Site & C2 seed & Model & H4 (C2$-$C1), 95\% CI & Verdict\\", r"\midrule"]
            for _, r in sub.sort_values(["site", "c2_seed", "model"]).iterrows():
                lines.append(f"{r.site} & {int(r.c2_seed)}{' (frozen)' if int(r.c2_seed) == 20260718 else ''} & {r.model} & "
                             f"{f(r.point_estimate)} {ci(r.ci_low, r.ci_high)} & {VERDICT_TEX[r.verdict]}\\\\")
            lines += [r"\bottomrule", r"\end{tabular}\end{center}",
                      "Verdict codes as in the main text (C: interval above zero). Corrected estimator; all other inputs are the primary ones."]
            pend = perm[perm.status == "pending"]
            if len(pend):
                lines.append("Not completed at the time of writing: " + ", ".join(
                    f"{r.site} C2 seed {int(r.c2_seed)}" + (f" ({r.model})" if "model" in pend and isinstance(r.model, str) else "")
                    for _, r in pend.iterrows()) + ".")
            for site in ("source", "external"):
                x = sub[(sub.site == site) & (sub.model == "M3")]
                if len(x) >= 2:
                    self.mac(f"PermHFourMThree{'Src' if site == 'source' else 'Ext'}Range",
                             f"{f(x.point_estimate.min())} to {f(x.point_estimate.max())}")
        else:
            lines.append("Not completed at the time of writing.")
        st_path = self.r / "followup_m2m3_status.csv"
        st = pd.read_csv(st_path).iloc[0] if st_path.exists() else None
        lines.append(r"\paragraph{M2 and M3 under training seed 20260719 (post hoc).}")
        if st is not None and st.status == "done":
            c = self.csv("followup_m2m3_contrasts")
            lines += [r"\begin{center}\small\begin{tabular}{lllrl}", r"\toprule",
                      r"H & Model & Estimator & Estimate (95\% CI) & V\\", r"\midrule"]
            for hh, m, cc, site in (("H1", "M1", None, ""), ("H1", "M2", None, ""), ("H1", "M3", None, ""), ("H1", "M4", None, ""),
                                    ("H2", "M3", "C1", ""), ("H3", "M3", None, ""), ("H4", "M3", None, "source"), ("H4", "M3", None, "external")):
                for est in ("original", "evaluable_study"):
                    x = c[(c.hypothesis == hh) & (c.model == m) & (c.estimator == est) & (c.site.fillna("") == site)]
                    if cc:
                        x = x[x.contrast.str.contains(cc)]
                    x = x.iloc[0]
                    lines.append(f"{hh}{('-' + cc) if cc else ''}{(' ' + site) if site else ''} & {m} & {est.replace('_', '-')} & {f(x.point_estimate)} {ci(x.ci_low, x.ci_high)} & {VERDICT_TEX[x.verdict]}\\\\")
                    key = f"RepTwo{hh}{m}{site}{est[:4]}".replace("1", "One").replace("2", "Two").replace("3", "Three").replace("4", "Four").replace("_", "")
                    self.mac(key, f"{f(x.point_estimate)}~{ci(x.ci_low, x.ci_high)}")
            lines += [r"\bottomrule", r"\end{tabular}\end{center}"]
            self.mac("MTwoMThreeReplicateStatus", "completed")
        else:
            lines.append("M2 was being retrained under seed 20260719 (model-train tier, frozen settings) when this "
                         "supplement was generated; no M2/M3 replicate result is reported. The command that completes "
                         "it is \\texttt{bash scripts/run\\_revision\\_gpu\\_queue.sh} followed by "
                         "\\texttt{python -m c3e.revision.runner --only followup} and \\texttt{python -m c3e.revision.report}.")
            self.mac("MTwoMThreeReplicateStatus", "not completed")
        self.write("supp_gpu_status", "\n".join(lines))

    # ------------------------------------------------------------------ figures
    def figures(self, sens: pd.DataFrame):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                             "xtick.color": INK2, "ytick.color": INK2, "axes.linewidth": 0.6,
                             "font.family": "DejaVu Sans"})

        # Figure 1: H1 across specifications.
        specs = list(dict.fromkeys(sens.spec))
        fig, axes = plt.subplots(1, 4, figsize=(7.2, 3.6), sharey=True)
        for ax, m in zip(axes, ("M1", "M2", "M3", "M4")):
            d = sens[sens.model == m].set_index("spec").reindex(specs)
            y = np.arange(len(specs))[::-1]
            ax.axvline(0, color=INK2, lw=0.6)
            for xv in (-0.02, 0.02):
                ax.axvline(xv, color=GRID, lw=0.8, ls="--")
            for yi, (_, r) in zip(y, d.iterrows()):
                if not np.isfinite(r.pt):
                    continue
                col = PALETTE[1] if r.original else PALETTE[0]
                mk = "s" if r.original else "o"
                ax.plot([r.lo, r.hi], [yi, yi], color=col, lw=1.6, solid_capstyle="round")
                ax.plot(r.pt, yi, marker=mk, color=col, ms=4.5, mec="white", mew=0.6)
            ax.set_title(m, fontsize=9, color=INK)
            ax.grid(axis="x", color=GRID, lw=0.4)
            ax.set_axisbelow(True)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
        axes[0].set_yticks(np.arange(len(specs))[::-1])
        axes[0].set_yticklabels(specs)
        fig.supxlabel("H1: external minus source selective error at the frozen operating point (95% CI)", fontsize=8, color=INK)
        from matplotlib.lines import Line2D
        fig.legend(handles=[Line2D([], [], color=PALETTE[1], marker="s", lw=1.6, label="original estimator (label-less studies counted correct)"),
                            Line2D([], [], color=PALETTE[0], marker="o", lw=1.6, label="label-less studies excluded (corrected and sensitivities)")],
                   loc="upper center", ncol=2, frameon=False, fontsize=7.5, bbox_to_anchor=(0.6, 1.02))
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        fig.savefig(self.fig / "fig1_h1_specifications.pdf", bbox_inches="tight")
        plt.close(fig)

        # Figure 2: label composition (impression; share of studies per pathology).
        bp = self.csv("label_audit_by_pathology")
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), sharey=True)
        cats = [("positive", "positive"), ("negative", "negative"), ("uncertain", "uncertain"), ("unmentioned", "unmentioned")]
        for ax, ls in zip(axes, ("impression", "findings")):
            ylab, pos = [], 0
            yt = []
            for site in ("source", "external"):
                for t in TARGETS:
                    r = bp[(bp.site == site) & (bp.label_source == ls) & (bp.scope == "all_eligible") & (bp.pathology == t)].iloc[0]
                    left = 0.0
                    for k, (c, _) in enumerate(cats):
                        w = r[c] / r.studies
                        ax.barh(pos, w, left=left, color=PALETTE[k] if c != "unmentioned" else "#e9e8e4",
                                edgecolor="white", linewidth=0.8, height=0.8)
                        left += w
                    ylab.append(f"{'Src' if site == 'source' else 'Ext'} {SHORT[t]}")
                    yt.append(pos)
                    pos -= 1
                pos -= 0.6
            ax.set_yticks(yt)
            ax.set_yticklabels(ylab, fontsize=7)
            ax.set_xlim(0, 1)
            ax.set_title(f"{ls.capitalize()}-derived labels", fontsize=9, color=INK)
            ax.set_xlabel("Share of studies in the evaluation cohort")
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
        from matplotlib.patches import Patch
        fig.legend(handles=[Patch(color=PALETTE[0], label="positive"), Patch(color=PALETTE[1], label="negative"),
                            Patch(color=PALETTE[2], label="uncertain"), Patch(color="#e9e8e4", label="unmentioned")],
                   loc="upper center", ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.55, 1.04))
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        fig.savefig(self.fig / "fig2_label_composition.pdf", bbox_inches="tight")
        plt.close(fig)

        # Figure 3: risk-coverage (evaluable studies), frozen score.
        rc = self.csv("rc_curves")
        rc = rc[(rc.score == "frozen") & (rc.condition == "C0")]
        L = self.lev[(self.lev.analysis == "primary") & (self.lev.label_variant == "primary") & (self.lev.estimator == "evaluable_study") & (self.lev.condition == "C0")]
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
        markers = ["o", "s", "^", "D"]
        for ax, site in zip(axes, ("source", "external")):
            for k, m in enumerate(("M1", "M2", "M3", "M4")):
                d = rc[(rc.site == site) & (rc.model == m)]
                ax.plot(d.coverage_evaluable, d.risk_evaluable_study, color=PALETTE[k], lw=1.6, label=m)
                pt = L[(L.site == site) & (L.model == m)].iloc[0]
                ax.plot(pt.coverage_evaluable, pt.risk, marker=markers[k], color=PALETTE[k], ms=5, mec="white", mew=0.7)
            ax.set_title(f"{'Source (MIMIC-CXR-JPG)' if site == 'source' else 'External (CheXpert Plus)'}", fontsize=9, color=INK)
            ax.set_xlabel("Coverage (evaluable studies)")
            ax.grid(color=GRID, lw=0.4)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
        axes[0].set_ylabel("Selective error among\nevaluable accepted studies")
        axes[1].legend(frameon=False, fontsize=7.5, loc="upper left")
        fig.tight_layout()
        fig.savefig(self.fig / "fig3_risk_coverage.pdf", bbox_inches="tight")
        plt.close(fig)

        # Figure 4: per-pathology sensitivity/specificity, M4, accepted, source vs external.
        oc = self.csv("operating_characteristics")
        oc = oc[(oc.label_variant == "primary") & (oc.scope == "accepted") & (oc.model == "M4")]
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.4), sharey=True)
        for ax, k in zip(axes, ("sensitivity", "specificity")):
            for i, t in enumerate(TARGETS[::-1]):
                s = oc[(oc.site == "source") & (oc.pathology == t)].iloc[0][k]
                e = oc[(oc.site == "external") & (oc.pathology == t)].iloc[0][k]
                ax.plot([s, e], [i, i], color=GRID, lw=2, zorder=1)
                ax.plot(s, i, "o", color=PALETTE[0], ms=6, mec="white", mew=0.7, zorder=2, label="source" if i == 0 else None)
                ax.plot(e, i, "s", color=PALETTE[1], ms=6, mec="white", mew=0.7, zorder=2, label="external" if i == 0 else None)
            ax.set_yticks(range(5))
            ax.set_yticklabels(TARGETS[::-1])
            ax.set_xlim(0.3, 1.0)
            ax.set_xlabel(k.capitalize() + " among accepted studies (labelled cells)")
            ax.grid(axis="x", color=GRID, lw=0.4)
            for s_ in ("top", "right"):
                ax.spines[s_].set_visible(False)
        axes[1].legend(frameon=False, fontsize=7.5, loc="lower left")
        fig.tight_layout()
        fig.savefig(self.fig / "fig4_operating_points.pdf", bbox_inches="tight")
        plt.close(fig)

        # Figure 5: within-site H4 (C2 - C1) for M3 and M4 across specifications,
        # C2 permutations and training seeds (corrected estimator unless noted).
        specs5 = [("primary", "primary", "evaluable_study", "Evaluable-study (corrected)"),
                  ("primary", "primary", "original", "Original estimator"),
                  ("primary", "primary", "cell_micro", "Cell-pooled"),
                  ("primary", "primary", "pathology_macro", "Pathology-macro"),
                  ("primary", "uncertain_negative", "evaluable_study", "Uncertain → negative"),
                  ("primary", "uncertain_positive", "evaluable_study", "Uncertain → positive"),
                  ("primary", "unmentioned_negative", "evaluable_study", "Unmentioned → negative"),
                  ("coverage70", "primary", "evaluable_study", "Coverage 70%"),
                  ("coverage90", "primary", "evaluable_study", "Coverage 90%"),
                  ("T5", "primary", "evaluable_study", "Informativeness T=5"),
                  ("T10", "primary", "evaluable_study", "Informativeness T=10"),
                  ("findings_S1", "primary", "evaluable_study", "Findings labels"),
                  ("seed20260719", "primary", "evaluable_study", "Training seed 2")]
        perm = self.csv("followup_c2_permutations") if (self.r / "followup_c2_permutations.csv").exists() else None
        rows5 = []
        for a, v, est, lab in specs5:
            df = self.H(a, v, est)
            for site in ("source", "external"):
                for m in ("M3", "M4"):
                    x = df[(df.hypothesis == "H4") & (df.model == m) & (df.site == site)]
                    if len(x):
                        x = x.iloc[0]
                        rows5.append(dict(spec=lab, site=site, model=m, pt=x.point_estimate, lo=x.ci_low, hi=x.ci_high))
        if perm is not None:
            pr = perm[(perm.status == "done") & (perm.estimator == "evaluable_study") & (perm.contrast.str.startswith("H4"))
                      & (perm.c2_seed != 20260718)]
            for (site, m), g in pr.groupby(["site", "model"]):
                if m not in ("M3", "M4"):
                    continue
                for k, (_, r) in enumerate(g.sort_values("c2_seed").iterrows(), start=2):
                    rows5.append(dict(spec=f"C2 permutation {k}", site=site, model=m, pt=r.point_estimate, lo=r.ci_low, hi=r.ci_high))
        d5 = pd.DataFrame(rows5)
        order = list(dict.fromkeys([r["spec"] for r in rows5]))
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.9), sharey=True)
        for ax, site in zip(axes, ("source", "external")):
            ax.axvline(0, color=INK2, lw=0.6)
            for k, m in enumerate(("M3", "M4")):
                d = d5[(d5.site == site) & (d5.model == m)].set_index("spec")
                for i, sp in enumerate(order):
                    if sp not in d.index:
                        continue
                    r = d.loc[sp]
                    y = len(order) - 1 - i + (0.17 if m == "M3" else -0.17)
                    ax.plot([r.lo, r.hi], [y, y], color=PALETTE[k], lw=1.6, solid_capstyle="round")
                    ax.plot(r.pt, y, marker="o" if m == "M3" else "s", color=PALETTE[k], ms=4.5, mec="white", mew=0.6,
                            label=m if (i == 0 and site == "source") else None)
            ax.set_title("Source (MIMIC-CXR-JPG)" if site == "source" else "External (CheXpert Plus)", fontsize=9, color=INK)
            ax.grid(axis="x", color=GRID, lw=0.4)
            ax.set_axisbelow(True)
            for s_ in ("top", "right"):
                ax.spines[s_].set_visible(False)
        axes[0].set_yticks(range(len(order)))
        axes[0].set_yticklabels(order[::-1])
        fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, fontsize=7.5, loc="upper center",
                   ncol=2, bbox_to_anchor=(0.62, 1.03))
        fig.supxlabel("H4: selective error with misaligned (C2) minus absent (C1) context (95% CI)", fontsize=8, color=INK)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(self.fig / "fig5_h4_within_site.pdf", bbox_inches="tight")
        plt.close(fig)

    def run(self):
        self.t_cohort()
        self.t_label_composition()
        self.t_levels()
        self.t_hypotheses()
        sens = self.t_sensitivity()
        self.t_label_source()
        self.t_operating()
        self.t_coverage_context()
        self.t_comparators()
        self.t_uncertainty()
        self.t_c2()
        self.t_context_scan()
        self.t_subgroups()
        self.t_pathology()
        self.t_multiplicity()
        self.s_tables()
        self.s_gpu_status()
        self.figures(sens)
        body = ["% Generated by c3e.revision.report from results/c3e_revision; do not edit."]
        body += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(self.macros.items())]
        self.write("numbers", "\n".join(body))
        return sorted(self.macros)


def main(argv=None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=default_root)
    a = ap.parse_args(argv)
    names = Gen(a.project_root.resolve()).run()
    print(f"{len(names)} macros; tables and figures written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
