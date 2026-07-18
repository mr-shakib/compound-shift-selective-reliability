"""Tests for the CheXpert Plus study-key derivation, JSONL label loading and
one-to-one join, within-study disagreement audit, config schema, output
isolation, and safe-output (no-identifier-leakage) guarantees.

All data here is synthetic. No real paths, identifiers, or report text.
"""
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from c3e.chexpert import (
    parse_image_path, derive_study_key_value, derive_study_key, attach_study_key,
    load_jsonl_labels, join_labels, within_study_label_disagreement,
    strip_internal_columns, identifier_columns, STUDY_KEY_COL,
    study_equal_weights, parse_view_number, select_one_frontal_per_study,
    concordant_study_mask, patient_clustered_bootstrap_indices,
)
from c3e.config_schema import validate_chexpert_config, assert_valid_chexpert_config
from c3e.chexpert_run import run_chexpert, prepare_output_dir, source_id

CONFIG_DIR = Path(__file__).parents[1] / "configs"


# --------------------------------------------------------------------------- #
# Task 3 -- study-key derivation
# --------------------------------------------------------------------------- #
def test_valid_training_path():
    assert derive_study_key_value(
        "train/patient00001/study1/view1_frontal.jpg") == "patient00001/study1"


def test_valid_validation_path():
    assert derive_study_key_value(
        "valid/patient64321/study12/view1_lateral.jpg") == "patient64321/study12"


def test_malformed_path():
    # wrong number of components -> fail closed
    assert derive_study_key_value("just/three/components") is None
    assert derive_study_key_value("a/b/c/d/e") is None
    assert derive_study_key_value("") is None
    assert derive_study_key_value(None) is None
    assert derive_study_key_value(1234) is None


def test_patient_folder_mismatch():
    # patient folder does not match patient\d+ -> fail closed
    assert derive_study_key_value(
        "train/PATIENT_X/study1/view1_frontal.jpg") is None
    assert derive_study_key_value(
        "train/subject001/study1/view1_frontal.jpg") is None


def test_study_folder_missing():
    # study component absent / not study\d+ -> fail closed
    assert derive_study_key_value(
        "train/patient00001/view1_frontal.jpg") is None  # only 3 components
    assert derive_study_key_value(
        "train/patient00001/exam1/view1_frontal.jpg") is None  # not study\d+


def test_parse_image_path_components():
    p = parse_image_path("train/patient00007/study3/view2_frontal.jpg")
    assert p == {"split": "train", "patient_folder": "patient00007",
                 "study_folder": "study3", "filename": "view2_frontal.jpg"}


def test_derive_study_key_counts_failures():
    s = pd.Series([
        "train/patient00001/study1/a.jpg",
        "train/patient00001/study1/b.jpg",
        "bad/path",
        None,
    ])
    keys, n_fail = derive_study_key(s)
    assert n_fail == 2
    assert keys.iloc[0] == "patient00001/study1"
    assert keys.iloc[1] == "patient00001/study1"
    assert keys.isna().iloc[2]


def test_attach_study_key_fails_closed():
    df = pd.DataFrame({"path_to_image": ["train/patient1/study1/a.jpg", "malformed"]})
    with pytest.raises(ValueError):
        attach_study_key(df, "path_to_image", fail_on_parse_error=True)
    # with fail_on_parse_error False it attaches and reports the failure count
    out, n_fail = attach_study_key(df, "path_to_image", fail_on_parse_error=False)
    assert n_fail == 1
    assert STUDY_KEY_COL in out.columns


# --------------------------------------------------------------------------- #
# Task 4 -- JSONL loading + one-to-one join
# --------------------------------------------------------------------------- #
def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_jsonl_load_preserves_four_states(tmp_path: Path):
    p = tmp_path / "labels.json"
    _write_jsonl(p, [
        {"path_to_image": "train/patient1/study1/a.jpg", "Edema": 1.0},
        {"path_to_image": "train/patient1/study2/b.jpg", "Edema": 0.0},
        {"path_to_image": "train/patient2/study1/c.jpg", "Edema": -1.0},
        {"path_to_image": "train/patient2/study2/d.jpg", "Edema": None},
    ])
    df = load_jsonl_labels(p, join_key="path_to_image")
    assert len(df) == 4
    assert df["Edema"].iloc[0] == 1.0
    assert df["Edema"].iloc[1] == 0.0
    assert df["Edema"].iloc[2] == -1.0
    assert pd.isna(df["Edema"].iloc[3])  # null distinct from 0


def test_jsonl_missing_join_key_raises(tmp_path: Path):
    p = tmp_path / "labels.json"
    _write_jsonl(p, [{"Edema": 1.0}])
    with pytest.raises(KeyError):
        load_jsonl_labels(p, join_key="path_to_image")


def test_one_to_one_join_passes():
    table = pd.DataFrame({"path_to_image": ["a", "b", "c"], "x": [1, 2, 3]})
    labels = pd.DataFrame({"path_to_image": ["a", "b", "c"], "Edema": [1.0, 0.0, None]})
    merged, stats = join_labels(table, labels)
    assert stats["cardinality"] == "one_to_one"
    assert stats["unmatched_main_rows"] == 0
    assert stats["unmatched_label_records"] == 0
    assert stats["duplicate_keys_table"] == 0
    assert stats["expansion_factor"] == 1.0
    assert len(merged) == 3


def test_join_fails_on_duplicate_keys():
    table = pd.DataFrame({"path_to_image": ["a", "a", "b"]})
    labels = pd.DataFrame({"path_to_image": ["a", "b"], "Edema": [1.0, 0.0]})
    with pytest.raises(ValueError):
        join_labels(table, labels)


def test_join_fails_on_unmatched_records():
    table = pd.DataFrame({"path_to_image": ["a", "b", "c"]})
    labels = pd.DataFrame({"path_to_image": ["a", "b"], "Edema": [1.0, 0.0]})
    with pytest.raises(ValueError):
        join_labels(table, labels)  # on_unmatched='fail' default
    # explicit override allows it
    merged, stats = join_labels(table, labels, on_unmatched="allow")
    assert stats["unmatched_main_rows"] == 1


# --------------------------------------------------------------------------- #
# Task 6 -- within-study disagreement
# --------------------------------------------------------------------------- #
def _cfg_min():
    return {
        "labels": ["Cardiomegaly", "Edema"],
        "positive_value": 1, "negative_value": 0, "uncertain_value": -1,
    }


def test_within_study_disagreement():
    # study K1: 2 frontal images, Cardiomegaly differs (1 vs 0), Edema agrees (1,1)
    # study K2: 1 frontal image (not multi) -> excluded
    df = pd.DataFrame({
        STUDY_KEY_COL: ["K1", "K1", "K2"],
        "is_frontal": [True, True, True],
        "ap_pa": ["AP", "PA", "AP"],
        "Cardiomegaly": [1.0, 0.0, 1.0],
        "Edema": [1.0, 1.0, 0.0],
    })
    out = within_study_label_disagreement(df, _cfg_min(), ap_pa_column="ap_pa")
    assert out["n_multi_image_frontal_studies"] == 1
    card = out["labels"]["Cardiomegaly"]
    assert card["studies_differing"] == 1
    assert card["studies_identical"] == 0
    assert card["disagreement_pct"] == 100.0
    # co-occurrence of pos and neg recorded symmetrically
    assert card["state_cooccurrence_matrix"]["pos"]["neg"] == 1
    assert card["state_cooccurrence_matrix"]["neg"]["pos"] == 1
    edema = out["labels"]["Edema"]
    assert edema["studies_differing"] == 0
    assert edema["studies_identical"] == 1
    # AP+PA stratum picked up the differing study
    assert card["by_view_stratum"]["ap_and_pa"]["differing"] == 1


# --------------------------------------------------------------------------- #
# Config schema
# --------------------------------------------------------------------------- #
def test_real_configs_validate():
    for name in ("chexpert_plus_impression.yaml", "chexpert_plus_findings.yaml"):
        cfg = yaml.safe_load((CONFIG_DIR / name).read_text())
        assert validate_chexpert_config(cfg) == [], name


def test_schema_rejects_report_fixed():
    cfg = yaml.safe_load((CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    cfg["label_source"]["path"] = "../../data/chexpert_plus/labels/report_fixed.json"
    problems = validate_chexpert_config(cfg)
    assert any("report_fixed" in p for p in problems)


def test_schema_rejects_native_study_column():
    cfg = yaml.safe_load((CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    cfg["id_columns"]["study"] = "study_id"
    problems = validate_chexpert_config(cfg)
    assert any("id_columns.study" in p for p in problems)


def test_schema_rejects_unknown_field():
    cfg = yaml.safe_load((CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    cfg["totally_unsupported"] = 1
    problems = validate_chexpert_config(cfg)
    assert any("unknown top-level field" in p for p in problems)


def test_schema_requires_analysis_policy():
    cfg = yaml.safe_load((CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    del cfg["analysis_policy"]
    problems = validate_chexpert_config(cfg)
    assert any("analysis_policy" in p for p in problems)


def test_schema_rejects_low_bootstrap_replicates():
    cfg = yaml.safe_load((CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    cfg["analysis_policy"]["bootstrap_replicates_final"] = 100
    problems = validate_chexpert_config(cfg)
    assert any("bootstrap_replicates_final" in p for p in problems)


def test_schema_rejects_label_aggregation():
    cfg = yaml.safe_load((CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    cfg["analysis_policy"]["aggregate_labels"] = True
    problems = validate_chexpert_config(cfg)
    assert any("aggregate_labels" in p for p in problems)


# --------------------------------------------------------------------------- #
# Output isolation
# --------------------------------------------------------------------------- #
def test_configs_have_isolated_output_dirs():
    imp = yaml.safe_load((CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    fnd = yaml.safe_load((CONFIG_DIR / "chexpert_plus_findings.yaml").read_text())
    assert imp["output_dir"] != fnd["output_dir"]
    assert imp["output_dir"].rstrip("/").endswith("impression")
    assert fnd["output_dir"].rstrip("/").endswith("findings")


def test_output_dir_marker_prevents_cross_source_overwrite(tmp_path: Path):
    out = tmp_path / "shared"
    prepare_output_dir(out, "impression")
    prepare_output_dir(out, "impression")  # same source OK
    with pytest.raises(RuntimeError):
        prepare_output_dir(out, "findings")  # different source refused


# --------------------------------------------------------------------------- #
# Safe output -- no identifier leakage (integration through run_chexpert)
# --------------------------------------------------------------------------- #
SENTINEL_PATIENT = "SENTINELPATIENTVALUE"


def _synthetic_dataset(tmp_path: Path) -> tuple[Path, Path]:
    paths = [
        "train/patient00001/study1/view1_frontal.jpg",
        "train/patient00001/study1/view2_frontal.jpg",  # 2nd frontal, same study
        "train/patient00001/study2/view1_frontal.jpg",
        "valid/patient00002/study1/view1_lateral.jpg",
    ]
    table = pd.DataFrame({
        "path_to_image": paths,
        "deid_patient_id": [SENTINEL_PATIENT, SENTINEL_PATIENT, SENTINEL_PATIENT, "PAT_B"],
        "split": ["train", "train", "train", "valid"],
        "frontal_lateral": ["Frontal", "Frontal", "Frontal", "Lateral"],
        "ap_pa": ["AP", "PA", "AP", None],
        "section_clinical_history": ["eval for edema", "eval for edema", "chest pain", ""],
        "section_history": ["", "", "", ""],
    })
    tpath = tmp_path / "table.parquet"
    table.to_parquet(tpath)

    labels = [
        {"path_to_image": paths[0], "Cardiomegaly": 1.0, "Edema": 1.0,
         "Pleural Effusion": 0.0, "Atelectasis": None, "Consolidation": 0.0},
        {"path_to_image": paths[1], "Cardiomegaly": 0.0, "Edema": 1.0,  # Cardiomegaly differs within study1
         "Pleural Effusion": 0.0, "Atelectasis": None, "Consolidation": 0.0},
        {"path_to_image": paths[2], "Cardiomegaly": 1.0, "Edema": 0.0,
         "Pleural Effusion": None, "Atelectasis": 1.0, "Consolidation": None},
        {"path_to_image": paths[3], "Cardiomegaly": None, "Edema": None,
         "Pleural Effusion": 1.0, "Atelectasis": None, "Consolidation": -1.0},
    ]
    lpath = tmp_path / "impression_fixed.json"
    _write_jsonl(lpath, labels)
    return tpath, lpath


def _synthetic_config(tmp_path: Path, tpath: Path, lpath: Path, out: Path) -> Path:
    base = yaml.safe_load(
        (CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    base["table_path"] = str(tpath)
    base["label_source"]["path"] = str(lpath)
    base["output_dir"] = str(out)
    cpath = tmp_path / "synthetic.yaml"
    cpath.write_text(yaml.safe_dump(base))
    return cpath


def test_full_run_no_identifier_leakage(tmp_path: Path):
    tpath, lpath = _synthetic_dataset(tmp_path)
    out = tmp_path / "out"
    cpath = _synthetic_config(tmp_path, tpath, lpath, out)

    report = run_chexpert(cpath, dry_run=False)
    assert report["derived_study_key"]["unique_studies"] == 3
    assert report["derived_study_key"]["parse_failures"] == 0
    assert report["join"]["cardinality"] == "one_to_one"
    assert report["join"]["unmatched_main_rows"] == 0
    assert report["join"]["unmatched_label_records"] == 0
    # only 1 multi-image frontal study (patient00001/study1)
    assert report["disagreement_summary"]["n_multi_image_frontal_studies"] == 1

    # Inspect EVERY produced file: no identifier value, no path, no internal key.
    produced = list(out.iterdir())
    assert produced, "expected safe outputs to be written"
    # Identifier / path / derived-key VALUES must never appear. Column names
    # (e.g. "path_to_image") are explicitly permitted in safe outputs, so they
    # are not forbidden here.
    forbidden_substrings = [
        SENTINEL_PATIENT, "PAT_B", "_c3e_study_key",
        "patient00001", "patient00002", "study1", "study2",
        "train/patient", "valid/patient", ".jpg",
    ]
    for f in produced:
        text = f.read_text(encoding="utf-8")
        for bad in forbidden_substrings:
            assert bad not in text, f"identifier/path {bad!r} leaked into {f.name}"


def test_dry_run_writes_only_validation_report(tmp_path: Path):
    tpath, lpath = _synthetic_dataset(tmp_path)
    out = tmp_path / "out_dry"
    cpath = _synthetic_config(tmp_path, tpath, lpath, out)
    report = run_chexpert(cpath, dry_run=True)
    assert report["mode"] == "dry_run"
    names = {f.name for f in out.iterdir()}
    # no manifest, no per-row csv; only the marker + validation report
    assert names == {"source_marker.json", "validation_report.json"}


# --------------------------------------------------------------------------- #
# Multiple-image analysis policy (preregistered)
# --------------------------------------------------------------------------- #
def _study_frame():
    # S1: 1 image, S2: 2 images, S3: 3 images
    return pd.DataFrame({
        STUDY_KEY_COL: ["S1", "S2", "S2", "S3", "S3", "S3"],
        "path_to_image": [
            "train/patient1/study1/view1_frontal.jpg",
            "train/patient2/study1/view1_frontal.jpg",
            "train/patient2/study1/view2_frontal.jpg",
            "train/patient3/study1/view2_frontal.jpg",
            "train/patient3/study1/view1_frontal.jpg",
            "train/patient3/study1/view3_frontal.jpg",
        ],
        "Cardiomegaly": [1.0, 1.0, 1.0, 1.0, 0.0, 1.0],  # S3 discordant
        "Edema": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],          # S3 concordant
    })


def test_primary_weights_sum_to_one_per_study():
    df = _study_frame()
    w = study_equal_weights(df)
    per_study = w.groupby(df[STUDY_KEY_COL]).sum()
    assert per_study.round(9).eq(1.0).all()


def test_single_image_study_weight_is_one():
    df = _study_frame()
    w = study_equal_weights(df)
    assert w[df[STUDY_KEY_COL] == "S1"].iloc[0] == 1.0


def test_three_image_study_weights_are_one_third():
    df = _study_frame()
    w = study_equal_weights(df)
    assert w[df[STUDY_KEY_COL] == "S3"].round(9).eq(round(1/3, 9)).all()


def test_weights_require_study_key():
    with pytest.raises(KeyError):
        study_equal_weights(pd.DataFrame({"x": [1]}))


def test_malformed_grouping_fails_closed():
    df = pd.DataFrame({"path_to_image": ["train/patient1/study1/v1.jpg", "MALFORMED"]})
    with pytest.raises(ValueError):
        attach_study_key(df, "path_to_image", fail_on_parse_error=True)


def test_parse_view_number():
    assert parse_view_number("train/patient1/study1/view3_frontal.jpg") == 3
    assert parse_view_number("train/patient1/study1/frontal.jpg") is None
    assert parse_view_number("bad/path") is None


def test_one_image_selection_deterministic():
    df = _study_frame()  # manual study keys S1/S2/S3; paths drive view-number order
    m1 = select_one_frontal_per_study(df)
    m2 = select_one_frontal_per_study(df)
    assert m1.equals(m2)
    # exactly one image per study selected
    assert int(m1.sum()) == df[STUDY_KEY_COL].nunique()
    # S3 selects view1 (lowest view number), not the first-listed view2 row
    s3 = df[df[STUDY_KEY_COL] == "S3"]
    chosen = s3[m1.loc[s3.index]]
    assert parse_view_number(chosen["path_to_image"].iloc[0]) == 1


def test_one_image_selection_label_independent():
    df = _study_frame()
    base = select_one_frontal_per_study(df)
    # permute / corrupt labels; selection must not change
    df2 = df.copy()
    df2["Cardiomegaly"] = df2["Cardiomegaly"].values[::-1]
    df2["Edema"] = 0.0
    perturbed = select_one_frontal_per_study(df2)
    assert base.equals(perturbed)


def test_target_specific_concordance():
    df = _study_frame()
    cfg = _cfg_min()
    card_mask, card_stats = concordant_study_mask(df, "Cardiomegaly", cfg)
    edema_mask, edema_stats = concordant_study_mask(df, "Edema", cfg)
    # S3 discordant for Cardiomegaly -> excluded for that target only
    assert card_stats["excluded_discordant_studies"] == 1
    assert edema_stats["excluded_discordant_studies"] == 0
    # S3 rows dropped from Cardiomegaly subset but kept for Edema
    assert not card_mask[df[STUDY_KEY_COL] == "S3"].any()
    assert edema_mask[df[STUDY_KEY_COL] == "S3"].all()
    # single-image + concordant multi-image studies retained for Cardiomegaly
    assert card_mask[df[STUDY_KEY_COL].isin(["S1", "S2"])].all()


def test_patient_cluster_bootstrap_keeps_whole_clusters():
    df = pd.DataFrame({
        "deid_patient_id": ["A", "A", "A", "B", "B"],
        "v": [1, 2, 3, 4, 5],
    })
    sizes = df.groupby("deid_patient_id").size().to_dict()
    reps = list(patient_clustered_bootstrap_indices(df, "deid_patient_id", seed=7, n_replicates=5))
    assert len(reps) == 5
    for idx in reps:
        sub = df.loc[idx]
        counts = sub["deid_patient_id"].value_counts().to_dict()
        for pat, c in counts.items():
            # each present patient contributes a whole-cluster multiple of its size
            assert c % sizes[pat] == 0
    # determinism: same seed reproduces the first replicate exactly
    again = next(patient_clustered_bootstrap_indices(df, "deid_patient_id", seed=7, n_replicates=1))
    assert list(again) == list(reps[0])


def test_safety_scan_flags_and_clears(tmp_path: Path):
    from c3e.safety_scan import scan_file, scan_tree
    # clean aggregate CSV: comma-joined column names must NOT trip the long-text rule
    clean = tmp_path / "label_prevalence.csv"
    clean.write_text("label,positive,negative,uncertain,unmentioned,positive_pct_of_known\n"
                     "Cardiomegaly,26281,11462,3376,149952,63.9145\n", encoding="utf-8")
    assert scan_file(clean) == []
    # planted identifier / path values must be caught
    bad = tmp_path / "leak.csv"
    bad.write_text("col\ntrain/patient00001/study1/view1_frontal.jpg\n", encoding="utf-8")
    problems = scan_file(bad)
    assert "patient_folder_value" in problems and "jpg_extension" in problems
    # scan_tree deletes the unsafe file and reports not-clean
    res = scan_tree(tmp_path, delete_unsafe=True)
    assert res["clean"] is False
    assert not bad.exists()      # unsafe output removed
    assert clean.exists()        # safe output retained


def test_identifier_columns_stripped():
    cfg = yaml.safe_load((CONFIG_DIR / "chexpert_plus_impression.yaml").read_text())
    df = pd.DataFrame({
        STUDY_KEY_COL: ["patient1/study1"],
        "path_to_image": ["train/patient1/study1/a.jpg"],
        "deid_patient_id": [SENTINEL_PATIENT],
        "section_clinical_history": ["text"],
        "Edema": [1.0],
        "label_prevalence_count": [5],
    })
    safe = strip_internal_columns(df, identifier_columns(cfg))
    assert STUDY_KEY_COL not in safe.columns
    assert "path_to_image" not in safe.columns
    assert "deid_patient_id" not in safe.columns
    assert "section_clinical_history" not in safe.columns
    # an aggregate count column survives
    assert "label_prevalence_count" in safe.columns
