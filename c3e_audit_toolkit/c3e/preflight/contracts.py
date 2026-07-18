"""Frozen Stage 2B data and protocol contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from c3e.audit import load_yaml

PATHOLOGIES = (
    "Cardiomegaly",
    "Edema",
    "Pleural Effusion",
    "Atelectasis",
    "Consolidation",
)
PRIMARY_LABEL_SOURCE = "impression_fixed.json"
SENSITIVITY_LABEL_SOURCE = "findings_fixed.json"
FORBIDDEN_LABEL_SOURCE = "report_fixed.json"
ALLOWED_LABEL_SOURCES = frozenset({PRIMARY_LABEL_SOURCE, SENSITIVITY_LABEL_SOURCE})

BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20260718
BOOTSTRAP_UNIT = "patient"
SOURCE_COVERAGES = (0.80, 0.90, 0.70)

SOURCE_SITE_ID = "SYNTH_SOURCE"
EXTERNAL_SITE_ID = "SYNTH_EXTERNAL"
SOURCE_SPLITS = frozenset({"train", "calibration", "validation", "test"})
EXTERNAL_SPLIT = "external_evaluation"

ID_COLUMNS = ("site_id", "split_id", "patient_id", "study_id", "image_id")
BASE_COLUMNS = ID_COLUMNS + (
    "view",
    "context_text",
    "context_state",
    "label_source",
) + PATHOLOGIES
IMAGE_PROBABILITY_COLUMNS = tuple(f"image_prob__{p}" for p in PATHOLOGIES)
MULTIMODAL_PROBABILITY_COLUMNS = tuple(f"multimodal_prob__{p}" for p in PATHOLOGIES)
PROBABILITY_COLUMNS = IMAGE_PROBABILITY_COLUMNS + MULTIMODAL_PROBABILITY_COLUMNS
REQUIRED_COLUMNS = BASE_COLUMNS + PROBABILITY_COLUMNS

NATURAL_CONTEXT_STATES = frozenset({"informative", "low_information", "absent"})
KNOWN_VIEWS = frozenset({"frontal", "lateral"})
FORBIDDEN_MODEL_INPUT_COLUMNS = frozenset({
    "findings",
    "impression",
    "full_report",
    "complete_report",
    "report",
    "report_fixed",
    "post_diagnostic_summary",
})


class ContractError(ValueError):
    """Raised when a preflight input violates a frozen contract."""


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ContractError(f"missing required columns: {missing}")


def _require_nonempty_identifiers(df: pd.DataFrame) -> None:
    for column in ID_COLUMNS:
        values = df[column]
        if values.isna().any() or values.astype(str).str.strip().eq("").any():
            raise ContractError(f"missing required identifier values in {column}")


def _validate_hierarchy(df: pd.DataFrame) -> None:
    if df["image_id"].duplicated().any():
        duplicated = df.loc[df["image_id"].duplicated(False), "image_id"].nunique()
        raise ContractError(f"duplicate image IDs detected: {duplicated}")

    study_patient = df.groupby("study_id", observed=True)["patient_id"].nunique()
    if (study_patient > 1).any():
        raise ContractError("one study is assigned to multiple patients")

    study_site = df.groupby("study_id", observed=True)["site_id"].nunique()
    study_split = df.groupby("study_id", observed=True)["split_id"].nunique()
    if (study_site > 1).any() or (study_split > 1).any():
        raise ContractError("one study crosses site or split boundaries")


def _validate_label_values(df: pd.DataFrame) -> None:
    for pathology in PATHOLOGIES:
        values = df[pathology]
        if values.isna().any() or not values.isin([0, 1]).all():
            raise ContractError(
                f"invalid pathology values in {pathology}; expected only integer 0/1"
            )


def _validate_probabilities(df: pd.DataFrame) -> None:
    for column in PROBABILITY_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")
        if values.isna().any() or not values.between(0.0, 1.0, inclusive="both").all():
            raise ContractError(f"invalid probability values in {column}")


def _validate_context_states(df: pd.DataFrame) -> None:
    states = set(df["context_state"].astype(str))
    if not states.issubset(NATURAL_CONTEXT_STATES):
        raise ContractError(f"unsupported natural context states: {sorted(states - NATURAL_CONTEXT_STATES)}")

    text = df["context_text"].fillna("").astype(str)
    absent = df["context_state"].eq("absent")
    low = df["context_state"].eq("low_information")
    informative = df["context_state"].eq("informative")
    if not text[absent].str.strip().eq("").all():
        raise ContractError("absent context_state must have empty context_text")
    if text[low].str.strip().eq("").any():
        raise ContractError("low_information context_state must have non-empty context_text")
    if text[informative].str.split().str.len().lt(5).any():
        raise ContractError("informative context_state must contain at least five tokens")
    if text.eq("[NO_CONTEXT]").any():
        raise ContractError("natural records must not contain the controlled [NO_CONTEXT] token")

    context_per_study = df.groupby("study_id", observed=True)[
        ["context_text", "context_state"]
    ].nunique(dropna=False)
    if (context_per_study > 1).any().any():
        raise ContractError("natural context text/state is inconsistent within a study")


def _validate_label_sources(df: pd.DataFrame) -> None:
    sources = set(df["label_source"].astype(str))
    if FORBIDDEN_LABEL_SOURCE in sources:
        raise ContractError("report_fixed.json is forbidden")
    unsupported = sources - ALLOWED_LABEL_SOURCES
    if unsupported:
        raise ContractError(f"unsupported label sources: {sorted(unsupported)}")


def validate_data_contract(df: pd.DataFrame) -> None:
    """Validate one synthetic image-level table without correcting it."""

    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ContractError("synthetic table must be a non-empty DataFrame")
    _require_columns(df, REQUIRED_COLUMNS)
    _require_nonempty_identifiers(df)
    _validate_hierarchy(df)
    _validate_label_values(df)
    _validate_probabilities(df)
    _validate_label_sources(df)
    _validate_context_states(df)

    views = set(df["view"].astype(str).str.lower())
    unsupported = views - KNOWN_VIEWS
    if unsupported:
        raise ContractError(f"unsupported views: {sorted(unsupported)}")


def validate_frozen_protocol(protocol_root: str | Path) -> dict:
    """Assert the machine-readable bundle retains every Stage 2B lock."""

    root = Path(protocol_root)
    exp = load_yaml(root / "config" / "experiment_registry.yaml")
    ctx = load_yaml(root / "config" / "context_interventions.yaml")

    if tuple(exp["targets"]["pathologies"]) != PATHOLOGIES:
        raise ContractError("frozen pathology order/set changed")
    if exp["targets"]["primary_label_source"] != PRIMARY_LABEL_SOURCE:
        raise ContractError("primary label source changed")
    if exp["targets"]["sensitivity_label_source"] != SENSITIVITY_LABEL_SOURCE:
        raise ContractError("sensitivity label source changed")
    if exp["targets"]["forbidden_label_source"] != FORBIDDEN_LABEL_SOURCE:
        raise ContractError("forbidden label source changed")
    if exp["authorization"]["model_training"] is not False:
        raise ContractError("model training authorization must remain false")
    if exp["authorization"]["medical_image_loading"] is not False:
        raise ContractError("medical image loading authorization must remain false")
    if exp["datasets"]["external"]["tuning_allowed"] is not False:
        raise ContractError("external tuning must remain disabled")
    stats = exp["statistics"]
    if (
        stats["bootstrap_replicates"] != BOOTSTRAP_REPLICATES
        or stats["bootstrap_seed"] != BOOTSTRAP_SEED
        or stats["resampling_unit"] != BOOTSTRAP_UNIT
    ):
        raise ContractError("bootstrap policy changed")
    sel = exp["selective_policy"]
    if sel["primary_source_coverage"] != 0.80:
        raise ContractError("primary source coverage changed")
    if tuple(sel["sensitivity_source_coverages"]) != (0.90, 0.70):
        raise ContractError("sensitivity source coverages changed")
    if sel["frozen_threshold_transfer"] is not True:
        raise ContractError("frozen threshold transfer disabled")

    interventions = {item["id"]: item for item in ctx["controlled_interventions"]}
    if set(interventions) != {"C0", "C1", "C2"}:
        raise ContractError("controlled intervention set changed")
    if interventions["C0"]["operator"] != "identity":
        raise ContractError("C0 semantics changed")
    if interventions["C1"]["replacement_token"] != "[NO_CONTEXT]":
        raise ContractError("C1 semantics changed")
    c2 = interventions["C2"]
    required_c2 = {
        "same_institution": True,
        "same_split": True,
        "different_patient": True,
        "same_context_length_bin": True,
        "seed": BOOTSTRAP_SEED,
    }
    if c2["operator"] != "deterministic_permutation" or c2.get("constraints") != required_c2:
        raise ContractError("C2 semantics changed")
    return exp
