"""Image-to-study aggregation for eligible synthetic frontal fixtures."""

from __future__ import annotations

import pandas as pd

from .contracts import (
    ContractError,
    IMAGE_PROBABILITY_COLUMNS,
    MULTIMODAL_PROBABILITY_COLUMNS,
    PATHOLOGIES,
)

SUPPORTED_VIEWS = frozenset({"frontal", "lateral"})
ELIGIBLE_VIEW = "frontal"


def aggregate_images_to_studies(df: pd.DataFrame) -> pd.DataFrame:
    """Mean probabilities over eligible frontal images, one row per study.

    The explicit view rule is: ``frontal`` is eligible, ``lateral`` is
    excluded, and every other value is rejected.  A study with no eligible
    frontal image is rejected rather than silently dropped.
    """

    required = {
        "site_id", "split_id", "patient_id", "study_id", "image_id", "view",
        "context_text", "context_state", "label_source", "intervention",
        *PATHOLOGIES,
        *IMAGE_PROBABILITY_COLUMNS,
        *MULTIMODAL_PROBABILITY_COLUMNS,
    }
    missing = required - set(df.columns)
    if missing:
        raise ContractError(f"study aggregation missing columns: {sorted(missing)}")
    views = set(df["view"].astype(str).str.lower())
    if not views.issubset(SUPPORTED_VIEWS):
        raise ContractError(f"unsupported views for aggregation: {sorted(views - SUPPORTED_VIEWS)}")

    study_map = df.groupby("study_id", observed=True).agg(
        patients=("patient_id", "nunique"),
        sites=("site_id", "nunique"),
        splits=("split_id", "nunique"),
    )
    if (study_map > 1).any().any():
        raise ContractError("study hierarchy is inconsistent during aggregation")

    for pathology in PATHOLOGIES:
        if (df.groupby("study_id", observed=True)[pathology].nunique(dropna=False) > 1).any():
            raise ContractError(f"study labels are inconsistent for {pathology}")

    context_columns = ["context_text", "context_state", "label_source"]
    for column in context_columns:
        if (
            df.groupby(["study_id", "intervention"], observed=True)[column]
            .nunique(dropna=False)
            .gt(1)
            .any()
        ):
            raise ContractError(f"study field is inconsistent: {column}")

    eligible = df[df["view"].astype(str).str.lower().eq(ELIGIBLE_VIEW)].copy()
    all_studies = set(df["study_id"])
    eligible_studies = set(eligible["study_id"])
    missing_frontal = all_studies - eligible_studies
    if missing_frontal:
        raise ContractError(f"studies without eligible frontal images: {len(missing_frontal)}")

    keys = ["site_id", "split_id", "patient_id", "study_id", "intervention"]
    probability_columns = list(IMAGE_PROBABILITY_COLUMNS + MULTIMODAL_PROBABILITY_COLUMNS)
    aggregated = eligible.groupby(keys, observed=True, sort=True)[probability_columns].mean().reset_index()

    first_columns = ["context_text", "context_state", "label_source", *PATHOLOGIES]
    optional_columns = [
        "controlled_context_state", "context_donor_patient_id", "context_donor_site_id",
        "context_donor_split_id", "context_length_bin", "context_donor_length_bin",
    ]
    first_columns += [c for c in optional_columns if c in eligible.columns]
    first = eligible.groupby(keys, observed=True, sort=True)[first_columns].first().reset_index()
    counts = eligible.groupby(keys, observed=True, sort=True).size().rename("eligible_image_count").reset_index()
    out = aggregated.merge(first, on=keys, validate="one_to_one").merge(
        counts, on=keys, validate="one_to_one"
    )
    if out.duplicated(["study_id", "intervention"]).any():
        raise ContractError("aggregation did not produce exactly one row per study/intervention")
    return out
