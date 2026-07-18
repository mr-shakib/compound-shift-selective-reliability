"""Schema validation for CheXpert Plus audit configs.

Every field consumed by :mod:`c3e.chexpert` and the ``chexpert`` CLI command is
validated here, so no unsupported YAML field is silently accepted. The
validator is intentionally strict: unknown top-level keys are reported, and
label-source / study-key / grouping / safe-output / image-policy blocks are
checked for the exact shape the loader relies on.
"""
from __future__ import annotations

# Top-level keys recognised by the CheXpert config schema.
_KNOWN_TOP_LEVEL = {
    "dataset_name", "table_path", "label_source", "id_columns", "study_key",
    "grouping", "split_column", "view_column", "frontal_values", "ap_pa_column",
    "context_columns", "labels", "positive_value", "negative_value",
    "uncertain_value", "unmentioned_is_missing", "image_policy", "safe_output",
    "output_dir", "low_information", "gate", "analysis_policy",
    "sensitivity_analyses",
}

_REQUIRED_TOP_LEVEL = {
    "dataset_name", "table_path", "label_source", "id_columns", "study_key",
    "grouping", "split_column", "view_column", "frontal_values",
    "context_columns", "labels", "positive_value", "negative_value",
    "uncertain_value", "unmentioned_is_missing", "output_dir",
    "analysis_policy", "sensitivity_analyses",
}

_VALID_DUP_POLICY = {"fail", "allow"}
_VALID_UNMATCHED_POLICY = {"fail", "allow"}


def validate_chexpert_config(cfg: dict) -> list[str]:
    """Return a list of human-readable problems. Empty list == valid."""
    problems: list[str] = []

    if not isinstance(cfg, dict):
        return ["config root is not a mapping"]

    unknown = set(cfg) - _KNOWN_TOP_LEVEL
    for k in sorted(unknown):
        problems.append(f"unknown top-level field: {k!r}")

    for k in sorted(_REQUIRED_TOP_LEVEL - set(cfg)):
        problems.append(f"missing required field: {k!r}")

    # --- label_source -----------------------------------------------------
    ls = cfg.get("label_source")
    if isinstance(ls, dict):
        for req in ("path", "format", "join_key"):
            if not ls.get(req):
                problems.append(f"label_source.{req} is required")
        if ls.get("format") not in (None, "jsonl"):
            problems.append("label_source.format must be 'jsonl'")
        if ls.get("join_key") not in (None, "path_to_image"):
            problems.append("label_source.join_key must be 'path_to_image'")
        if ls.get("cardinality") not in (None, "one_to_one"):
            problems.append("label_source.cardinality must be 'one_to_one'")
        if ls.get("on_duplicate_keys", "fail") not in _VALID_DUP_POLICY:
            problems.append("label_source.on_duplicate_keys must be 'fail' or 'allow'")
        if ls.get("on_unmatched", "fail") not in _VALID_UNMATCHED_POLICY:
            problems.append("label_source.on_unmatched must be 'fail' or 'allow'")
        # report_fixed.json must never be an active label source
        if isinstance(ls.get("path"), str) and "report_fixed" in ls["path"]:
            problems.append("label_source.path uses report_fixed.json, which is "
                            "forbidden (input-target leakage)")
    elif ls is not None:
        problems.append("label_source must be a mapping")

    # --- id_columns -------------------------------------------------------
    idc = cfg.get("id_columns")
    if isinstance(idc, dict):
        for req in ("patient", "image"):
            if not idc.get(req):
                problems.append(f"id_columns.{req} is required")
        if "study" in idc:
            problems.append("id_columns.study must NOT be set: no native study "
                            "column exists; use the derived study_key block")
    elif idc is not None:
        problems.append("id_columns must be a mapping")

    # --- study_key (derived) ---------------------------------------------
    sk = cfg.get("study_key")
    if isinstance(sk, dict):
        if sk.get("derived") is not True:
            problems.append("study_key.derived must be true (study key is derived, not native)")
        if not sk.get("source_column"):
            problems.append("study_key.source_column is required")
        if sk.get("method") not in (None, "pureposixpath_patient_study"):
            problems.append("study_key.method must be 'pureposixpath_patient_study'")
        ic = sk.get("internal_column", "")
        if not (isinstance(ic, str) and ic.startswith("_c3e_")):
            problems.append("study_key.internal_column must be an internal name "
                            "starting with '_c3e_' (never exported)")
    elif sk is not None:
        problems.append("study_key must be a mapping")

    # --- grouping ---------------------------------------------------------
    gr = cfg.get("grouping")
    if isinstance(gr, dict):
        if gr.get("split_unit") != "patient":
            problems.append("grouping.split_unit must be 'patient'")
        if gr.get("cluster_unit") != "study":
            problems.append("grouping.cluster_unit must be 'study'")
        if gr.get("observation_unit") != "image":
            problems.append("grouping.observation_unit must be 'image'")
    elif gr is not None:
        problems.append("grouping must be a mapping")

    # --- image_policy (no selection/aggregation this phase) --------------
    ip = cfg.get("image_policy")
    if isinstance(ip, dict):
        if ip.get("select_one_per_study", False) is not False:
            problems.append("image_policy.select_one_per_study must be false this phase")
        if ip.get("aggregate_labels", False) is not False:
            problems.append("image_policy.aggregate_labels must be false this phase")
    elif ip is not None:
        problems.append("image_policy must be a mapping")

    # --- safe_output ------------------------------------------------------
    so = cfg.get("safe_output")
    if isinstance(so, dict):
        if so.get("write_manifest", False) is not False:
            problems.append("safe_output.write_manifest must be false (no manifest export)")
    elif so is not None:
        problems.append("safe_output must be a mapping")

    # --- labels & encodings ----------------------------------------------
    labels = cfg.get("labels")
    if not isinstance(labels, list) or not labels:
        problems.append("labels must be a non-empty list")
    for key in ("positive_value", "negative_value", "uncertain_value"):
        if key in cfg and not isinstance(cfg[key], (int, float)):
            problems.append(f"{key} must be numeric")
    if cfg.get("unmentioned_is_missing") is not True:
        problems.append("unmentioned_is_missing must be true")

    cc = cfg.get("context_columns")
    if not isinstance(cc, list) or not cc:
        problems.append("context_columns must be a non-empty list")

    if not isinstance(cfg.get("frontal_values"), list) or not cfg.get("frontal_values"):
        problems.append("frontal_values must be a non-empty list")

    # --- analysis_policy (preregistered primary analysis) ----------------
    ap = cfg.get("analysis_policy")
    if isinstance(ap, dict):
        if ap.get("primary_observation_unit") != "image":
            problems.append("analysis_policy.primary_observation_unit must be 'image'")
        if ap.get("study_equal_weighting") is not True:
            problems.append("analysis_policy.study_equal_weighting must be true")
        if ap.get("patient_clustered_bootstrap") is not True:
            problems.append("analysis_policy.patient_clustered_bootstrap must be true")
        reps = ap.get("bootstrap_replicates_final")
        if not isinstance(reps, int) or reps < 1000:
            problems.append("analysis_policy.bootstrap_replicates_final must be an int >= 1000")
        if ap.get("retain_all_frontal_images") is not True:
            problems.append("analysis_policy.retain_all_frontal_images must be true")
        if ap.get("aggregate_labels", False) is not False:
            problems.append("analysis_policy.aggregate_labels must be false")
    elif ap is not None:
        problems.append("analysis_policy must be a mapping")

    # --- sensitivity_analyses --------------------------------------------
    sa = cfg.get("sensitivity_analyses")
    if isinstance(sa, dict):
        if sa.get("unweighted_image_level") is not True:
            problems.append("sensitivity_analyses.unweighted_image_level must be true")
        oi = sa.get("one_image_per_study")
        if isinstance(oi, dict):
            if oi.get("enabled") is not True:
                problems.append("sensitivity_analyses.one_image_per_study.enabled must be true")
            if oi.get("selection_rule") != "lowest_view_number_then_stable_lexical":
                problems.append("sensitivity_analyses.one_image_per_study.selection_rule must be "
                                "'lowest_view_number_then_stable_lexical'")
            if oi.get("label_blind") is not True:
                problems.append("sensitivity_analyses.one_image_per_study.label_blind must be true")
        else:
            problems.append("sensitivity_analyses.one_image_per_study must be a mapping")
        cs = sa.get("concordant_study_subset")
        if isinstance(cs, dict):
            if cs.get("enabled") is not True:
                problems.append("sensitivity_analyses.concordant_study_subset.enabled must be true")
            if cs.get("target_specific") is not True:
                problems.append("sensitivity_analyses.concordant_study_subset.target_specific must be true")
            if cs.get("disagreement_policy") != "exclude_for_target":
                problems.append("sensitivity_analyses.concordant_study_subset.disagreement_policy "
                                "must be 'exclude_for_target'")
        else:
            problems.append("sensitivity_analyses.concordant_study_subset must be a mapping")
    elif sa is not None:
        problems.append("sensitivity_analyses must be a mapping")

    return problems


def assert_valid_chexpert_config(cfg: dict) -> None:
    problems = validate_chexpert_config(cfg)
    if problems:
        raise ValueError("invalid CheXpert config:\n  - " + "\n  - ".join(problems))
