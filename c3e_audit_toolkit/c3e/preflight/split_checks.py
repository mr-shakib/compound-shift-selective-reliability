"""Patient split isolation and source-only selection governance."""

from __future__ import annotations

import pandas as pd

from .contracts import (
    ContractError,
    EXTERNAL_SITE_ID,
    EXTERNAL_SPLIT,
    SOURCE_SITE_ID,
    SOURCE_SPLITS,
)

PROHIBITED_EXTERNAL_ACTIONS = frozenset({
    "classification_threshold_selection",
    "abstention_threshold_selection",
    "temperature_selection",
    "architecture_selection",
    "context_rule_revision",
})


def validate_split_isolation(df: pd.DataFrame) -> None:
    source = df[df["site_id"].eq(SOURCE_SITE_ID)]
    external = df[df["site_id"].eq(EXTERNAL_SITE_ID)]
    if source.empty or external.empty:
        raise ContractError("both synthetic source and external sites are required")
    if not set(source["split_id"]).issubset(SOURCE_SPLITS):
        raise ContractError("unsupported source split")
    if set(source["split_id"]) != SOURCE_SPLITS:
        raise ContractError("source train/calibration/validation/test partitions are required")
    if set(external["split_id"]) != {EXTERNAL_SPLIT}:
        raise ContractError("external records must use only external_evaluation")

    per_patient = source.groupby("patient_id", observed=True)["split_id"].nunique()
    if (per_patient > 1).any():
        raise ContractError("patient overlap across source splits")


def require_source_calibration(df: pd.DataFrame, *, action: str) -> None:
    """Make fitting on target or non-calibration data impossible."""

    if df.empty:
        raise ContractError(f"{action} requires non-empty source calibration data")
    if set(df["site_id"]) != {SOURCE_SITE_ID} or set(df["split_id"]) != {"calibration"}:
        raise ContractError(
            f"{action} is source-calibration-only; target or other split fitting is forbidden"
        )


def assert_selection_allowed(*, site_id: str, action: str) -> None:
    if site_id != SOURCE_SITE_ID and action in PROHIBITED_EXTERNAL_ACTIONS:
        raise ContractError(f"target-site {action} is forbidden")
