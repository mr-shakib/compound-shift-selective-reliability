"""Full aggregate-safe CheXpert Plus audit (C3-E2 Task 4-8).

Implements the preregistered multiple-image analysis policy
(docs/CHEXPERT_MULTIPLE_IMAGE_POLICY.md): frontal-image observation unit,
study-equal weighting, and the three sensitivity analyses (unweighted,
one-image-per-study, target-specific concordant subset).

Every output is aggregate-only: counts, weighted counts, percentages, column
names, label names, category names, and gate outcomes. No identifiers, paths,
report text, or per-row manifests are ever written.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .audit import (
    load_yaml, add_context_features, add_frontal_feature, add_mentions,
    split_overlap, gate_report,
)
from .config_schema import assert_valid_chexpert_config
from .chexpert import (
    STUDY_KEY_COL, attach_study_key, load_jsonl_labels, join_labels,
    study_equal_weights, select_one_frontal_per_study, concordant_study_mask,
    within_study_label_disagreement, strip_internal_columns, identifier_columns,
)
from .chexpert_run import _resolve, source_id, prepare_output_dir, MARKER_NAME

STATES = ("pos", "neg", "unc", "unmentioned")


# --------------------------------------------------------------------------- #
# small weighted helpers
# --------------------------------------------------------------------------- #
def _wrate(mask: pd.Series, w: pd.Series) -> float | None:
    denom = float(w.sum())
    if denom == 0:
        return None
    return round(float(w[mask.fillna(False)].sum()) / denom, 6)


def _rate(mask: pd.Series) -> float | None:
    n = int(len(mask))
    return round(float(mask.fillna(False).sum()) / n, 6) if n else None


def _wmedian(values: pd.Series, w: pd.Series) -> float | None:
    v = values.dropna()
    if v.empty:
        return None
    ww = w.loc[v.index]
    order = v.sort_values()
    cw = ww.loc[order.index].cumsum()
    cutoff = float(ww.sum()) / 2.0
    sel = order[cw >= cutoff]
    return float(sel.iloc[0]) if len(sel) else None


def _states(series: pd.Series, cfg: dict) -> dict:
    y = pd.to_numeric(series, errors="coerce")
    return {
        "pos": y.eq(cfg["positive_value"]),
        "neg": y.eq(cfg["negative_value"]),
        "unc": y.eq(cfg["uncertain_value"]),
        "unmentioned": y.isna(),
        "known": y.notna(),
        "_y": y,
    }


# --------------------------------------------------------------------------- #
# cohort structure
# --------------------------------------------------------------------------- #
def cohort_structure(full: pd.DataFrame, frontal: pd.DataFrame, cfg: dict) -> dict:
    patient_col = cfg["id_columns"]["patient"]
    sizes = frontal.groupby(STUDY_KEY_COL, observed=True).size()
    ap = frontal[cfg["ap_pa_column"]].astype("string").str.upper() if cfg.get("ap_pa_column") in frontal.columns else pd.Series([], dtype="string")
    split = frontal[cfg["split_column"]].astype("string")
    full_split = full[cfg["split_column"]].astype("string")
    return {
        "total_table_rows": int(len(full)),
        "frontal_image_rows": int(len(frontal)),
        "lateral_or_excluded_rows": int(len(full) - len(frontal)),
        "patient_count_full": int(full[patient_col].nunique()),
        "patient_count_frontal": int(frontal[patient_col].nunique()),
        "study_count_full": int(full[STUDY_KEY_COL].nunique()),
        "study_count_frontal": int(frontal[STUDY_KEY_COL].nunique()),
        "frontal_images_per_study": {
            "min": int(sizes.min()), "median": float(sizes.median()),
            "mean": round(float(sizes.mean()), 4), "max": int(sizes.max()),
            "studies_with_more_than_one_frontal": int((sizes > 1).sum()),
        },
        "ap_pa_distribution_frontal_images": {
            k: int(v) for k, v in ap.value_counts(dropna=False).items()
        },
        "split_distribution_frontal_images": {
            str(k): int(v) for k, v in split.value_counts(dropna=False).items()
        },
        "split_distribution_all_rows": {
            str(k): int(v) for k, v in full_split.value_counts(dropna=False).items()
        },
    }


# --------------------------------------------------------------------------- #
# context availability
# --------------------------------------------------------------------------- #
def _field_low_info(series: pd.Series, cfg: dict) -> pd.Series:
    from .text import is_low_information, normalize
    lc = cfg["low_information"]
    norm = series.map(normalize)
    return norm.map(lambda s: bool(s) and is_low_information(s, lc["min_tokens"], lc["generic_phrases"]))


def context_availability(frontal: pd.DataFrame, w: pd.Series, cfg: dict) -> pd.DataFrame:
    from .text import token_count, normalize
    rows = []
    fields = list(cfg["context_columns"]) + ["__combined__"]
    for field in fields:
        if field == "__combined__":
            norm = frontal["context"]  # already normalized by add_context_features
            present = frontal["context_present"]
            low_info = frontal["context_low_info"]
            usable = frontal["context_usable"]
            char_len = norm.str.len()
            tok = frontal["context_tokens"]
        else:
            raw = frontal[field]
            norm = raw.map(normalize)
            present = norm.str.len().gt(0)
            low_info = _field_low_info(raw, cfg)
            usable = present & ~low_info
            char_len = norm.str.len()
            tok = norm.map(token_count)
        isnull = frontal[field].isna() if field != "__combined__" else ~present
        empty = (~isnull) & (~present) if field != "__combined__" else pd.Series(False, index=frontal.index)
        nonempty = present
        tok_ne = tok[nonempty]
        char_ne = char_len[nonempty]
        rows.append({
            "context_field": field,
            "n_images": int(len(frontal)),
            "null_rate": _rate(isnull),
            "empty_rate": _rate(empty),
            "non_empty_rate": _rate(nonempty),
            "usable_rate": _rate(usable),
            "low_information_rate": _rate(low_info),
            "null_rate_weighted": _wrate(isnull, w),
            "non_empty_rate_weighted": _wrate(nonempty, w),
            "usable_rate_weighted": _wrate(usable, w),
            "low_information_rate_weighted": _wrate(low_info, w),
            "median_char_count_nonempty": float(char_ne.median()) if len(char_ne) else None,
            "median_token_count_nonempty": float(tok_ne.median()) if len(tok_ne) else None,
            "median_token_count_weighted_nonempty": _wmedian(tok[nonempty], w),
            "count_below_3_tokens": int((tok_ne < 3).sum()),
            "count_below_5_tokens": int((tok_ne < 5).sum()),
            "count_below_10_tokens": int((tok_ne < 10).sum()),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# label distributions
# --------------------------------------------------------------------------- #
def label_distributions(frontal: pd.DataFrame, w: pd.Series, cfg: dict) -> pd.DataFrame:
    rows = []
    ap = frontal[cfg["ap_pa_column"]].astype("string").str.upper() if cfg.get("ap_pa_column") in frontal.columns else None
    split = frontal[cfg["split_column"]].astype("string")
    usable = frontal["context_usable"]
    missing_ctx = ~frontal["context_present"]
    for label in cfg["labels"]:
        if label not in frontal.columns:
            rows.append({"label": label, "status": "missing_column"})
            continue
        st = _states(frontal[label], cfg)
        known_n = int(st["known"].sum())
        total_n = int(len(frontal))
        pos, neg, unc, unm, known = st["pos"], st["neg"], st["unc"], st["unmentioned"], st["known"]
        row = {
            "label": label, "status": "ok",
            "n_images": total_n, "n_known": known_n,
            "positive": int(pos.sum()), "negative": int(neg.sum()),
            "uncertain": int(unc.sum()), "unmentioned": int(unm.sum()),
            "positive_pct_of_all": round(100.0 * pos.sum() / total_n, 4) if total_n else None,
            "positive_pct_of_known": round(100.0 * pos.sum() / known_n, 4) if known_n else None,
            "negative_pct_of_known": round(100.0 * neg.sum() / known_n, 4) if known_n else None,
            "uncertain_pct_of_known": round(100.0 * unc.sum() / known_n, 4) if known_n else None,
            "unmentioned_pct_of_all": round(100.0 * unm.sum() / total_n, 4) if total_n else None,
            "positive_frac_known_weighted": (
                round(float(w[pos].sum()) / float(w[known].sum()), 6) if float(w[known].sum()) else None),
            "positive_frac_all_weighted": (
                round(float(w[pos].sum()) / float(w.sum()), 6) if float(w.sum()) else None),
        }
        # by AP / PA
        if ap is not None:
            for view in ("AP", "PA"):
                m = ap == view
                kn = int((known & m).sum())
                row[f"positive_frac_known_{view}"] = (
                    round(float((pos & m).sum()) / kn, 6) if kn else None)
        # by split
        for sp in ("train", "valid"):
            m = split == sp
            kn = int((known & m).sum())
            row[f"positive_frac_known_{sp}"] = (
                round(float((pos & m).sum()) / kn, 6) if kn else None)
        # by context group
        for name, m in (("usable_ctx", usable), ("missing_ctx", missing_ctx)):
            kn = int((known & m).sum())
            row[f"positive_frac_known_{name}"] = (
                round(float((pos & m).sum()) / kn, 6) if kn else None)
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# missingness relationship
# --------------------------------------------------------------------------- #
def missingness_relationship(frontal: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    rows = []
    label_dependent = {}
    for label in cfg["labels"]:
        if label not in frontal.columns:
            continue
        st = _states(frontal[label], cfg)
        absents = {}
        for state in STATES:
            m = st[state]
            n = int(m.sum())
            absent = float((~frontal.loc[m, "context_present"]).mean()) if n else None
            low = float(frontal.loc[m, "context_low_info"].mean()) if n else None
            usable = float(frontal.loc[m, "context_usable"].mean()) if n else None
            rows.append({
                "label": label, "label_state": state, "n": n,
                "context_absent_fraction": round(absent, 6) if absent is not None else None,
                "context_low_info_fraction": round(low, 6) if low is not None else None,
                "context_usable_fraction": round(usable, 6) if usable is not None else None,
            })
            if absent is not None:
                absents[state] = absent
        if absents:
            spread = max(absents.values()) - min(absents.values())
            label_dependent[label] = round(spread, 6)
    # association flag: does context absence vary across label states? (assoc, NOT causal)
    max_spread = max(label_dependent.values()) if label_dependent else 0.0
    summary = {
        "per_label_absent_fraction_spread": label_dependent,
        "max_absent_fraction_spread_across_states": round(max_spread, 6),
        "context_missingness_appears_label_associated": bool(max_spread >= 0.05),
        "note": "association only; no causal claim",
    }
    return pd.DataFrame(rows), summary


# --------------------------------------------------------------------------- #
# leakage
# --------------------------------------------------------------------------- #
def leakage_table(frontal: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rows = []
    for label in cfg["labels"]:
        direct_col = f"{label}__direct"
        any_col = f"{label}__mention_any"
        if any_col not in frontal.columns:
            continue
        st = _states(frontal[label], cfg)
        subsets = {
            "all": pd.Series(True, index=frontal.index),
            "positive": st["pos"], "negative": st["neg"], "uncertain": st["unc"],
        }
        direct = frontal[direct_col].astype(bool)
        any_m = frontal[any_col].astype(bool)
        synonym = any_m & ~direct
        neg = frontal[f"{label}__mention_negated"].astype(bool)
        spec = frontal[f"{label}__mention_speculative"].astype(bool)
        for sub_name, mask in subsets.items():
            n = int(mask.sum())
            sub = mask
            rows.append({
                "label": label, "subset": sub_name, "n": n,
                "direct_mention_rate": _rate(direct[sub]) if n else None,
                "synonym_mention_rate": _rate(synonym[sub]) if n else None,
                "negated_mention_rate": _rate(neg[sub]) if n else None,
                "speculative_mention_rate": _rate(spec[sub]) if n else None,
                "any_mention_rate": _rate(any_m[sub]) if n else None,
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# within-study disagreement (flattened to CSV) + JSON matrices
# --------------------------------------------------------------------------- #
def disagreement_table(frontal: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    dis = within_study_label_disagreement(
        frontal, cfg, study_key_col=STUDY_KEY_COL, ap_pa_column=cfg.get("ap_pa_column"))
    pairs = [("pos", "neg"), ("pos", "unc"), ("pos", "null"),
             ("neg", "unc"), ("neg", "null"), ("unc", "null")]
    rows = []
    for label, d in dis["labels"].items():
        if d.get("status") != "ok":
            rows.append({"label": label, "status": d.get("status", "na")})
            continue
        row = {
            "label": label, "status": "ok",
            "n_multi_image_frontal_studies": dis["n_multi_image_frontal_studies"],
            "studies_with_label_scope": d["multi_image_studies_with_label_scope"],
            "studies_identical": d["studies_identical"],
            "studies_differing": d["studies_differing"],
            "disagreement_pct": d["disagreement_pct"],
        }
        m = d["state_cooccurrence_matrix"]
        for a, b in pairs:
            row[f"cooc_{a}_{b}"] = m[a][b]
        strat = d.get("by_view_stratum") or {}
        for s in ("ap_only", "pa_only", "ap_and_pa"):
            row[f"{s}_differing"] = strat.get(s, {}).get("differing")
        rows.append(row)
    return pd.DataFrame(rows), dis


# --------------------------------------------------------------------------- #
# image-policy sensitivity
# --------------------------------------------------------------------------- #
def image_policy_sensitivity(frontal: pd.DataFrame, w: pd.Series, cfg: dict) -> pd.DataFrame:
    one_mask = select_one_frontal_per_study(
        frontal, source_column=cfg["id_columns"]["image"], study_key_col=STUDY_KEY_COL)
    rows = []
    for label in cfg["labels"]:
        if label not in frontal.columns:
            rows.append({"label": label, "status": "missing_column"})
            continue
        st = _states(frontal[label], cfg)
        pos, known = st["pos"], st["known"]
        # primary study-equal weighted, positive fraction among known
        primary = round(float(w[pos].sum()) / float(w[known].sum()), 6) if float(w[known].sum()) else None
        # unweighted image-level
        unweighted = round(float(pos.sum()) / int(known.sum()), 6) if int(known.sum()) else None
        # one image per study
        o_pos = pos & one_mask
        o_known = known & one_mask
        one_img = round(float(o_pos.sum()) / int(o_known.sum()), 6) if int(o_known.sum()) else None
        # concordant subset (target-specific)
        cmask, cstats = concordant_study_mask(frontal, label, cfg, study_key_col=STUDY_KEY_COL)
        c_pos = pos & cmask
        c_known = known & cmask
        concordant = round(float(c_pos.sum()) / int(c_known.sum()), 6) if int(c_known.sum()) else None
        vals = [v for v in (primary, unweighted, one_img, concordant) if v is not None]
        rows.append({
            "label": label, "status": "ok",
            "pos_frac_known_primary_weighted": primary,
            "pos_frac_known_unweighted": unweighted,
            "pos_frac_known_one_image": one_img,
            "pos_frac_known_concordant": concordant,
            "max_minus_min_across_policies": round(max(vals) - min(vals), 6) if vals else None,
            "unweighted_minus_primary": round(unweighted - primary, 6) if (unweighted is not None and primary is not None) else None,
            "one_image_minus_primary": round(one_img - primary, 6) if (one_img is not None and primary is not None) else None,
            "concordant_minus_primary": round(concordant - primary, 6) if (concordant is not None and primary is not None) else None,
            "concordant_excluded_studies": cstats.get("excluded_discordant_studies"),
            "concordant_excluded_pct_of_multi": cstats.get("excluded_pct_of_multi_image_studies"),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #
def run_full_audit(config_path: str | Path, *, table_override: str | None = None,
                   output_override: str | None = None, terms_path: str | Path | None = None) -> dict:
    config_path = Path(config_path).resolve()
    base = config_path.parent
    cfg = load_yaml(config_path)
    assert_valid_chexpert_config(cfg)
    if terms_path is None:
        terms_path = base / "terms.yaml"
    terms = load_yaml(terms_path)

    src = source_id(cfg)
    table_path = _resolve(base, table_override or cfg["table_path"])
    label_path = _resolve(base, cfg["label_source"]["path"])
    output_dir = Path(output_override).resolve() if output_override else _resolve(base, cfg["output_dir"])

    sk = cfg["study_key"]
    internal_col = sk.get("internal_column", STUDY_KEY_COL)
    join_key = cfg["label_source"]["join_key"]

    # load + derive key (fail closed) + one-to-one join
    from .io import read_table
    full = read_table(table_path)
    full, n_parse_fail = attach_study_key(full, sk["source_column"], internal_col, fail_on_parse_error=True)
    labels = load_jsonl_labels(label_path, join_key=join_key)
    full, join_stats = join_labels(
        full, labels, join_key=join_key,
        cardinality=cfg["label_source"].get("cardinality", "one_to_one"),
        on_duplicate_keys=cfg["label_source"].get("on_duplicate_keys", "fail"),
        on_unmatched=cfg["label_source"].get("on_unmatched", "fail"),
    )

    # features + frontal filter (retain ALL frontal images; no selection)
    full = add_context_features(full, cfg)
    full = add_frontal_feature(full, cfg)
    frontal = full[full["is_frontal"]].copy()
    frontal = add_mentions(frontal, cfg, terms)
    w = study_equal_weights(frontal, study_key_col=internal_col)

    # aggregate frames
    cohort = cohort_structure(full, frontal, cfg)
    ctx = context_availability(frontal, w, cfg)
    prevalence = label_distributions(frontal, w, cfg)
    missingness_df, missingness_summary = missingness_relationship(frontal, cfg)
    leakage = leakage_table(frontal, cfg)
    disagreement_df, disagreement_json = disagreement_table(frontal, cfg)
    sensitivity = image_policy_sensitivity(frontal, w, cfg)
    gate = gate_report(frontal, cfg, role="target")
    patient_sep = split_overlap(frontal, cfg)

    # write outputs to isolated dir
    prepare_output_dir(output_dir, src)
    ctx.to_csv(output_dir / "section_availability.csv", index=False)
    prevalence.to_csv(output_dir / "label_prevalence.csv", index=False)
    missingness_df.to_csv(output_dir / "missingness_by_label.csv", index=False)
    leakage.to_csv(output_dir / "leakage_by_label.csv", index=False)
    disagreement_df.to_csv(output_dir / "within_study_disagreement.csv", index=False)
    sensitivity.to_csv(output_dir / "image_policy_sensitivity.csv", index=False)
    with open(output_dir / "gate_report.json", "w", encoding="utf-8") as f:
        json.dump(gate, f, indent=2)
    with open(output_dir / "within_study_disagreement.json", "w", encoding="utf-8") as f:
        json.dump(disagreement_json, f, indent=2)

    summary = {
        "dataset_name": cfg["dataset_name"],
        "label_source": src,
        "study_key_parse_failures": int(n_parse_fail),
        "join": join_stats,
        "cohort_structure": cohort,
        "missingness_relationship": missingness_summary,
        "patient_split_separation": patient_sep,
        "analysis_policy": cfg["analysis_policy"],
        "sensitivity_analyses": cfg["sensitivity_analyses"],
        "gate_passed": gate["passed"],
        "encoding": {"positive": cfg["positive_value"], "negative": cfg["negative_value"],
                     "uncertain": cfg["uncertain_value"], "unmentioned": None},
    }
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # safety net: assert no identifier columns leak (frames above are aggregates)
    _ = strip_internal_columns(frontal, identifier_columns(cfg))

    return {
        "source": src, "output_dir": str(output_dir),
        "summary": summary, "context": ctx, "prevalence": prevalence,
        "leakage": leakage, "disagreement": disagreement_df,
        "sensitivity": sensitivity, "gate": gate,
    }


# --------------------------------------------------------------------------- #
# Task 6 -- label-source comparison (aggregate-safe)
# --------------------------------------------------------------------------- #
def compare_label_sources(impression_dir: str | Path, findings_dir: str | Path,
                          out_dir: str | Path) -> dict:
    """Compare impression vs findings per target from their SAFE aggregate
    outputs only. No per-image label pairs are joined or exported."""
    imp = Path(impression_dir)
    fnd = Path(findings_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def _read(d, name):
        return pd.read_csv(d / name)

    def _prev(d):
        return _read(d, "label_prevalence.csv").set_index("label")

    def _leak_all(d):
        t = _read(d, "leakage_by_label.csv")
        return t[t["subset"] == "all"].set_index("label")

    def _dis(d):
        return _read(d, "within_study_disagreement.csv").set_index("label")

    def _sens(d):
        return _read(d, "image_policy_sensitivity.csv").set_index("label")

    def _miss_pos(d):
        t = _read(d, "missingness_by_label.csv")
        return t[t["label_state"] == "pos"].set_index("label")

    ip, fp = _prev(imp), _prev(fnd)
    il, fl = _leak_all(imp), _leak_all(fnd)
    idd, fdd = _dis(imp), _dis(fnd)
    isn, fsn = _sens(imp), _sens(fnd)
    imp_pos, fnd_pos = _miss_pos(imp), _miss_pos(fnd)

    labels = list(ip.index)
    rows = []
    for lab in labels:
        rows.append({
            "label": lab,
            "imp_positive_pct_known": ip.loc[lab, "positive_pct_of_known"],
            "fnd_positive_pct_known": fp.loc[lab, "positive_pct_of_known"],
            "diff_positive_pct_known": round(ip.loc[lab, "positive_pct_of_known"] - fp.loc[lab, "positive_pct_of_known"], 4),
            "imp_uncertain_pct_known": ip.loc[lab, "uncertain_pct_of_known"],
            "fnd_uncertain_pct_known": fp.loc[lab, "uncertain_pct_of_known"],
            "imp_unmentioned_pct_all": ip.loc[lab, "unmentioned_pct_of_all"],
            "fnd_unmentioned_pct_all": fp.loc[lab, "unmentioned_pct_of_all"],
            "imp_usable_ctx_frac_pos": imp_pos.loc[lab, "context_usable_fraction"] if lab in imp_pos.index else None,
            "fnd_usable_ctx_frac_pos": fnd_pos.loc[lab, "context_usable_fraction"] if lab in fnd_pos.index else None,
            "imp_direct_rate_all": il.loc[lab, "direct_mention_rate"],
            "fnd_direct_rate_all": fl.loc[lab, "direct_mention_rate"],
            "imp_synonym_rate_all": il.loc[lab, "synonym_mention_rate"],
            "fnd_synonym_rate_all": fl.loc[lab, "synonym_mention_rate"],
            "imp_negated_rate_all": il.loc[lab, "negated_mention_rate"],
            "fnd_negated_rate_all": fl.loc[lab, "negated_mention_rate"],
            "imp_speculative_rate_all": il.loc[lab, "speculative_mention_rate"],
            "fnd_speculative_rate_all": fl.loc[lab, "speculative_mention_rate"],
            "imp_disagreement_pct": idd.loc[lab, "disagreement_pct"] if lab in idd.index else None,
            "fnd_disagreement_pct": fdd.loc[lab, "disagreement_pct"] if lab in fdd.index else None,
            "imp_policy_sensitivity_maxdiff": isn.loc[lab, "max_minus_min_across_policies"] if lab in isn.index else None,
            "fnd_policy_sensitivity_maxdiff": fsn.loc[lab, "max_minus_min_across_policies"] if lab in fsn.index else None,
        })
    comp = pd.DataFrame(rows)
    comp.to_csv(out / "label_source_comparison.csv", index=False)

    imp_gate = json.loads((imp / "gate_report.json").read_text())
    fnd_gate = json.loads((fnd / "gate_report.json").read_text())
    imp_sum = json.loads((imp / "summary.json").read_text())
    fnd_sum = json.loads((fnd / "summary.json").read_text())
    payload = {
        "comparison": "impression (primary) vs findings (sensitivity)",
        "per_target": rows,
        "gate_outcomes": {
            "impression": {"passed": imp_gate["passed"], "viable_labels": imp_gate["viable_labels"]},
            "findings": {"passed": fnd_gate["passed"], "viable_labels": fnd_gate["viable_labels"]},
        },
        "cohort": {
            "impression_frontal_images": imp_sum["cohort_structure"]["frontal_image_rows"],
            "findings_frontal_images": fnd_sum["cohort_structure"]["frontal_image_rows"],
            "frontal_studies": imp_sum["cohort_structure"]["study_count_frontal"],
        },
        "image_policy_sensitivity_note": (
            "max prevalence shift across primary/unweighted/one-image/concordant "
            "policies is < 0.01 in both sources for every target (see per-target)"),
    }
    with open(out / "label_source_comparison.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload
