"""CheXpert Plus-specific loaders, study-key derivation, label joins, and
aggregate-safe within-study audits.

Design constraints (C3-E2 safety):
  * The derived study key is a quasi-identifier (it embeds the patient folder).
    It lives ONLY in an internal, temporary column (prefixed ``_c3e_``) and is
    never written to any safe-to-share output.
  * Safe outputs contain only counts, fractions, column/label names, and
    aggregate distributions -- never identifier values, paths, or report text.
  * Grouping uses pandas groupby over the internal string key; it never relies
    on Python's process-randomised built-in ``hash()``. Where a stable digest
    is genuinely needed, ``hashlib.sha1`` is used explicitly.
"""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

import pandas as pd

# Internal (temporary) column names. Anything with this prefix must be stripped
# from a DataFrame before it is written to a safe output.
INTERNAL_PREFIX = "_c3e_"
STUDY_KEY_COL = f"{INTERNAL_PREFIX}study_key"
WEIGHT_COL = f"{INTERNAL_PREFIX}study_equal_weight"
VIEW_NUM_COL = f"{INTERNAL_PREFIX}view_number"
FILENAME_COL = f"{INTERNAL_PREFIX}filename"

_VIEW_NUM_RE = re.compile(r"view(\d+)", re.IGNORECASE)

# Path components are expected to look like: split/patientNNNNN/studyN/viewN.jpg
_PATIENT_RE = re.compile(r"^patient\d+$")
_STUDY_RE = re.compile(r"^study\d+$")
_EXPECTED_COMPONENTS = 4


# --------------------------------------------------------------------------- #
# Task 3 -- study-key derivation
# --------------------------------------------------------------------------- #
def parse_image_path(path: object) -> dict | None:
    """Parse one ``path_to_image`` with PurePosixPath. Fail closed.

    Returns a dict with the four components, or ``None`` when the path is
    malformed (wrong component count, patient/study folder not matching the
    expected pattern, empty filename, non-string input).
    """
    if not isinstance(path, str) or not path.strip():
        return None
    parts = PurePosixPath(path).parts
    if len(parts) != _EXPECTED_COMPONENTS:
        return None
    split_c, patient_f, study_f, filename = parts
    if not _PATIENT_RE.match(patient_f):
        return None
    if not _STUDY_RE.match(study_f):
        return None
    if not filename:
        return None
    return {
        "split": split_c,
        "patient_folder": patient_f,
        "study_folder": study_f,
        "filename": filename,
    }


def derive_study_key_value(path: object) -> str | None:
    """Composite study key = ``patient_folder + '/' + study_folder``.

    The ``study_folder`` label is not globally unique (it restarts within each
    patient), so it must be paired with the patient folder. Returns ``None`` on
    a malformed path (fail closed).
    """
    parsed = parse_image_path(path)
    if parsed is None:
        return None
    return f"{parsed['patient_folder']}/{parsed['study_folder']}"


def derive_study_key(paths: pd.Series) -> tuple[pd.Series, int]:
    """Vectorised study-key derivation.

    Returns ``(keys, n_parse_failures)``. ``keys`` is a Series aligned to the
    input index with ``None`` where parsing failed. The caller decides whether
    a non-zero failure count is fatal (it should be, for a trusted run).
    """
    keys = paths.map(derive_study_key_value)
    n_failures = int(keys.isna().sum())
    return keys, n_failures


def attach_study_key(df: pd.DataFrame, source_column: str,
                     internal_column: str = STUDY_KEY_COL,
                     fail_on_parse_error: bool = True) -> tuple[pd.DataFrame, int]:
    """Attach the derived study key as an internal temporary column.

    The column name is prefixed ``_c3e_`` so :func:`strip_internal_columns`
    removes it before any safe output is written.
    """
    if source_column not in df.columns:
        raise KeyError(f"study-key source column not found: {source_column!r}")
    out = df.copy()
    keys, n_failures = derive_study_key(out[source_column])
    if fail_on_parse_error and n_failures > 0:
        raise ValueError(
            f"study-key derivation failed for {n_failures} row(s); "
            "refusing to continue (fail-closed)."
        )
    out[internal_column] = keys
    return out, n_failures


# --------------------------------------------------------------------------- #
# Task 4 -- JSON Lines label loading and one-to-one join
# --------------------------------------------------------------------------- #
def load_jsonl_labels(path: str | Path, join_key: str = "path_to_image") -> pd.DataFrame:
    """Load a ``*_fixed.json`` label file (JSON Lines: one object per line).

    Read line by line (streaming decode) to avoid materialising the whole file
    as one string. The four-state encoding (1.0 / 0.0 / -1.0 / null) is
    preserved exactly -- values are not coerced or filled here.
    """
    path = Path(path)
    records: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}: invalid JSON on line {lineno}: {exc}") from exc
    if not records:
        raise ValueError(f"{path.name}: no records found (expected JSON Lines).")
    df = pd.DataFrame.from_records(records)
    if join_key not in df.columns:
        raise KeyError(f"{path.name}: join key {join_key!r} not present in label records.")
    return df


def join_labels(
    table: pd.DataFrame,
    labels: pd.DataFrame,
    join_key: str = "path_to_image",
    *,
    cardinality: str = "one_to_one",
    on_duplicate_keys: str = "fail",
    on_unmatched: str = "fail",
) -> tuple[pd.DataFrame, dict]:
    """Join label records onto the main table through ``join_key``.

    Validates cardinality and matching. Fails on duplicate join keys and on any
    unmatched record unless explicitly overridden (``on_unmatched='allow'``).
    Returns ``(merged, stats)`` where ``stats`` is aggregate-safe (counts only).
    """
    for name, frame in (("table", table), ("labels", labels)):
        if join_key not in frame.columns:
            raise KeyError(f"{name}: join key {join_key!r} not present.")

    tk = table[join_key]
    lk = labels[join_key]
    dup_table = int(tk.duplicated().sum())
    dup_labels = int(lk.duplicated().sum())

    if on_duplicate_keys == "fail" and (dup_table or dup_labels):
        raise ValueError(
            f"duplicate join keys (table={dup_table}, labels={dup_labels}); "
            "refusing one-to-one join."
        )

    tset, lset = set(tk), set(lk)
    matched = len(tset & lset)
    unmatched_table = len(tset - lset)
    unmatched_labels = len(lset - tset)

    if cardinality == "one_to_one":
        table_unique = (dup_table == 0)
        labels_unique = (dup_labels == 0)
    else:
        table_unique = labels_unique = None

    if on_unmatched == "fail" and (unmatched_table > 0 or unmatched_labels > 0):
        raise ValueError(
            f"unmatched records (main-only={unmatched_table}, "
            f"label-only={unmatched_labels}); set on_unmatched='allow' to override."
        )

    # Do not duplicate the join key or clobber label columns silently.
    overlap = (set(table.columns) & set(labels.columns)) - {join_key}
    label_cols = [c for c in labels.columns if c not in overlap or c == join_key]
    merged = table.merge(labels[label_cols], on=join_key, how="left",
                         validate="one_to_one" if cardinality == "one_to_one" else None)

    expansion = round(len(merged) / len(table), 6) if len(table) else None
    stats = {
        "join_key": join_key,
        "table_rows": int(len(table)),
        "label_records": int(len(labels)),
        "matched_keys": int(matched),
        "unmatched_main_rows": int(unmatched_table),
        "unmatched_label_records": int(unmatched_labels),
        "duplicate_keys_table": dup_table,
        "duplicate_keys_labels": dup_labels,
        "table_key_unique": table_unique,
        "labels_key_unique": labels_unique,
        "cardinality": cardinality,
        "expansion_factor": expansion,
        "merged_rows": int(len(merged)),
    }
    return merged, stats


# --------------------------------------------------------------------------- #
# Task 6 -- within-study label-disagreement audit (aggregate-safe)
# --------------------------------------------------------------------------- #
def _encode_state(value: object, cfg: dict) -> str:
    """Map a raw label value to one of {pos, neg, unc, null}."""
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return "null"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "null"
    if v == float(cfg["positive_value"]):
        return "pos"
    if v == float(cfg["negative_value"]):
        return "neg"
    if v == float(cfg["uncertain_value"]):
        return "unc"
    return "null"


def within_study_label_disagreement(
    df: pd.DataFrame,
    cfg: dict,
    study_key_col: str = STUDY_KEY_COL,
    *,
    frontal_col: str = "is_frontal",
    ap_pa_column: str | None = None,
) -> dict:
    """Aggregate-safe within-study label agreement/disagreement audit.

    For each target label: number of multi-image frontal studies, how many have
    identical vs differing labels across their frontal images, the disagreement
    percentage, a 4-state co-occurrence matrix, and (when an AP/PA column is
    given) the same stratified by AP-only / PA-only / AP+PA studies.

    Output contains only counts and percentages -- never study identifiers.
    """
    states = ("pos", "neg", "unc", "null")
    if study_key_col not in df.columns:
        raise KeyError(f"internal study-key column missing: {study_key_col!r}")

    frontal = df[df[frontal_col]] if frontal_col in df.columns else df
    # studies with >1 frontal image
    sizes = frontal.groupby(study_key_col, observed=True).size()
    multi_studies = set(sizes[sizes > 1].index)

    # AP/PA stratum per study (only meaningful among frontal images)
    stratum_of: dict = {}
    if ap_pa_column and ap_pa_column in frontal.columns:
        apv = frontal[ap_pa_column].astype("string").str.upper()
        tmp = pd.DataFrame({"k": frontal[study_key_col], "ap": apv == "AP", "pa": apv == "PA"})
        has_ap = tmp.groupby("k", observed=True)["ap"].any()
        has_pa = tmp.groupby("k", observed=True)["pa"].any()
        for k in multi_studies:
            a, p = bool(has_ap.get(k, False)), bool(has_pa.get(k, False))
            if a and p:
                stratum_of[k] = "ap_and_pa"
            elif a:
                stratum_of[k] = "ap_only"
            elif p:
                stratum_of[k] = "pa_only"
            else:
                stratum_of[k] = "other"

    def _blank_matrix() -> dict:
        return {a: {b: 0 for b in states} for a in states}

    result: dict = {
        "n_multi_image_frontal_studies": int(len(multi_studies)),
        "labels": {},
    }
    strata = ("ap_only", "pa_only", "ap_and_pa")

    for label in cfg["labels"]:
        if label not in frontal.columns:
            result["labels"][label] = {"status": "missing_column"}
            continue
        enc = frontal[label].map(lambda v: _encode_state(v, cfg))
        g = pd.DataFrame({"k": frontal[study_key_col], "s": enc})
        g = g[g["k"].isin(multi_studies)]

        identical = differing = 0
        matrix = _blank_matrix()
        strat_counts = {s: {"identical": 0, "differing": 0} for s in strata}
        for k, grp in g.groupby("k", observed=True):
            present = sorted(set(grp["s"]))
            if len(present) <= 1:
                identical += 1
                verdict = "identical"
            else:
                differing += 1
                verdict = "differing"
                # symmetric co-occurrence among distinct present states
                for i, a in enumerate(present):
                    for b in present[i + 1:]:
                        matrix[a][b] += 1
                        matrix[b][a] += 1
            st = stratum_of.get(k)
            if st in strat_counts:
                strat_counts[st][verdict] += 1

        n = identical + differing
        result["labels"][label] = {
            "status": "ok",
            "multi_image_studies_with_label_scope": int(n),
            "studies_identical": int(identical),
            "studies_differing": int(differing),
            "disagreement_pct": round(100.0 * differing / n, 4) if n else None,
            "state_cooccurrence_matrix": matrix,
            "by_view_stratum": {
                s: {
                    **strat_counts[s],
                    "disagreement_pct": (
                        round(100.0 * strat_counts[s]["differing"] /
                              (strat_counts[s]["identical"] + strat_counts[s]["differing"]), 4)
                        if (strat_counts[s]["identical"] + strat_counts[s]["differing"]) else None
                    ),
                }
                for s in strata
            } if stratum_of else None,
        }
    return result


# --------------------------------------------------------------------------- #
# Multiple-image analysis policy (preregistered: CHEXPERT_MULTIPLE_IMAGE_POLICY.md)
# --------------------------------------------------------------------------- #
def study_equal_weights(df: pd.DataFrame, study_key_col: str = STUDY_KEY_COL) -> pd.Series:
    """Study-equal image weights: each image in a study of size ``m`` gets ``1/m``.

    Every study therefore contributes total weight exactly 1. Intended to be run
    on a frontal-only frame so the weights implement study-equal weighting over
    frontal images. Returns a Series aligned to ``df.index``.
    """
    if study_key_col not in df.columns:
        raise KeyError(f"internal study-key column missing: {study_key_col!r}")
    sizes = df.groupby(study_key_col, observed=True)[study_key_col].transform("size")
    return 1.0 / sizes.astype(float)


def parse_view_number(path: object) -> int | None:
    """Parse the integer view number from a ``viewN_...`` filename component.

    Label-blind: reads only the filename, never labels/text/pathology. Returns
    ``None`` when the path is malformed or has no ``viewN`` token.
    """
    parsed = parse_image_path(path)
    if parsed is None:
        return None
    m = _VIEW_NUM_RE.search(parsed["filename"])
    return int(m.group(1)) if m else None


def select_one_frontal_per_study(
    df: pd.DataFrame,
    source_column: str = "path_to_image",
    study_key_col: str = STUDY_KEY_COL,
) -> pd.Series:
    """Deterministic, label-blind one-image-per-study selection (Sensitivity B).

    Rule: lowest parsed view number, then stable lexical order of the filename
    component. Never consults labels, text, pathology, quality, or model output.
    Returns a boolean mask (one True per study) aligned to ``df.index``.
    """
    if study_key_col not in df.columns:
        raise KeyError(f"internal study-key column missing: {study_key_col!r}")
    parsed = df[source_column].map(parse_image_path)
    view_num = parsed.map(lambda p: _VIEW_NUM_RE.search(p["filename"]).group(1)
                          if p and _VIEW_NUM_RE.search(p["filename"]) else None)
    # numeric sort key; missing view numbers sort last (large sentinel)
    view_sort = view_num.map(lambda v: int(v) if v is not None else 10**9)
    filename = parsed.map(lambda p: p["filename"] if p else "￿")
    work = pd.DataFrame({
        "k": df[study_key_col], "vn": view_sort, "fn": filename,
    }, index=df.index)
    # stable sort by (study, view number, filename); keep first per study
    order = work.sort_values(["k", "vn", "fn"], kind="stable")
    chosen_idx = order.groupby("k", observed=True).head(1).index
    mask = pd.Series(False, index=df.index)
    mask.loc[chosen_idx] = True
    return mask


def concordant_study_mask(
    df: pd.DataFrame,
    label: str,
    cfg: dict,
    study_key_col: str = STUDY_KEY_COL,
) -> tuple[pd.Series, dict]:
    """Target-specific concordant-study membership (Sensitivity C).

    A study is concordant for ``label`` when it is single-image, or when all of
    its images' *observed* (non-null) states for ``label`` agree. Discordant
    multi-image studies are excluded for this target only. Concordance is a
    filter -- no any-positive / majority / forced aggregation.

    Returns ``(row_mask, stats)``. ``row_mask`` selects rows in concordant
    studies; ``stats`` is aggregate-safe (counts/percentages only).
    """
    if label not in df.columns:
        return pd.Series(False, index=df.index), {"status": "missing_column"}
    enc = df[label].map(lambda v: _encode_state(v, cfg))
    work = pd.DataFrame({"k": df[study_key_col], "s": enc}, index=df.index)
    sizes = work.groupby("k", observed=True)["s"].size()

    def _distinct_nonnull(states: pd.Series) -> int:
        return states[states != "null"].nunique()

    distinct = work.groupby("k", observed=True)["s"].apply(_distinct_nonnull)
    multi = sizes > 1
    discordant_keys = set(distinct[(multi) & (distinct > 1)].index)
    concordant_keys = set(sizes.index) - discordant_keys

    row_mask = work["k"].isin(concordant_keys)
    n_studies = int(len(sizes))
    n_multi = int(multi.sum())
    n_excluded = int(len(discordant_keys))
    stats = {
        "status": "ok",
        "total_studies": n_studies,
        "multi_image_studies": n_multi,
        "concordant_studies": int(len(concordant_keys)),
        "excluded_discordant_studies": n_excluded,
        "excluded_pct_of_all_studies": round(100.0 * n_excluded / n_studies, 4) if n_studies else None,
        "excluded_pct_of_multi_image_studies": round(100.0 * n_excluded / n_multi, 4) if n_multi else None,
    }
    return row_mask, stats


def patient_clustered_bootstrap_indices(
    df: pd.DataFrame,
    patient_col: str,
    seed: int,
    n_replicates: int,
):
    """Yield row-index arrays for a patient-clustered bootstrap.

    Resamples *patients* with replacement; each sampled patient contributes ALL
    of its rows (whole cluster kept intact). Deterministic given ``seed``. This
    is a utility for later inferential evaluation; the descriptive audit does
    not call it. Never resamples images independently.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    groups = {p: idx.to_numpy() for p, idx in df.groupby(patient_col, observed=True).groups.items()}
    patients = list(groups)
    for _ in range(n_replicates):
        sampled = rng.choice(len(patients), size=len(patients), replace=True)
        parts = [groups[patients[i]] for i in sampled]
        yield np.concatenate(parts) if parts else np.array([], dtype=int)


# --------------------------------------------------------------------------- #
# Safe-output helpers
# --------------------------------------------------------------------------- #
def strip_internal_columns(df: pd.DataFrame, extra_forbidden: list[str] | None = None) -> pd.DataFrame:
    """Return a copy with all internal (``_c3e_``) columns and any explicitly
    forbidden identifier/text columns removed. Use before writing safe output.
    """
    drop = [c for c in df.columns if c.startswith(INTERNAL_PREFIX)]
    if extra_forbidden:
        drop += [c for c in extra_forbidden if c in df.columns]
    return df.drop(columns=list(dict.fromkeys(drop)), errors="ignore")


def identifier_columns(cfg: dict) -> list[str]:
    """Columns that carry identifiers/paths/free text and must never appear in
    a safe output. Derived from the config, plus the internal study key."""
    cols: list[str] = [STUDY_KEY_COL]
    idc = cfg.get("id_columns", {}) or {}
    cols += [v for v in idc.values() if v]
    lbl = cfg.get("label_source", {}) or {}
    if lbl.get("join_key"):
        cols.append(lbl["join_key"])
    cols += list(cfg.get("context_columns", []) or [])
    # common raw-text / path columns
    cols += ["report", "path_to_image", "path_to_dcm", "context",
             "section_narrative", "section_findings", "section_impression"]
    return list(dict.fromkeys(cols))
