"""Locked C0/C1/C2 controlled context interventions."""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .contracts import (
    BOOTSTRAP_SEED,
    ContractError,
    IMAGE_PROBABILITY_COLUMNS,
    MULTIMODAL_PROBABILITY_COLUMNS,
    PATHOLOGIES,
)
from .leakage_checks import validate_context_payload


def context_length_bin(text: object) -> str:
    n = len(str(text or "").split())
    if n == 0:
        return "0"
    if n <= 4:
        return "1-4"
    if n <= 9:
        return "5-9"
    return "10+"


def _c2_probability(image_probability: float, donor_text: str, pathology: str) -> float:
    digest = hashlib.sha256(f"{donor_text}|{pathology}".encode("utf-8")).digest()
    offset = ((digest[0] / 255.0) - 0.5) * 0.08
    return float(np.clip(image_probability + offset, 0.01, 0.99))


def _study_donor_map(studies: pd.DataFrame, *, seed: int) -> dict[str, pd.Series]:
    donors: dict[str, pd.Series] = {}
    rng = np.random.default_rng(seed)
    group_columns = ["site_id", "split_id", "context_length_bin"]
    for _, group in studies.groupby(group_columns, observed=True, sort=True):
        group = group.sort_values(["patient_id", "study_id"], kind="stable").reset_index(drop=True)
        if group["patient_id"].nunique() < 2:
            raise ContractError("C2 requires at least two patients per site/split/length bin")
        n = len(group)
        start = int(rng.integers(1, n))
        chosen: list[int] | None = None
        for step in range(n - 1):
            offset = 1 + ((start - 1 + step) % (n - 1))
            candidate = [(i + offset) % n for i in range(n)]
            if all(group.iloc[i]["patient_id"] != group.iloc[j]["patient_id"] for i, j in enumerate(candidate)):
                chosen = candidate
                break
        if chosen is None:
            raise ContractError("no deterministic different-patient C2 permutation exists")
        for recipient_index, donor_index in enumerate(chosen):
            donors[str(group.iloc[recipient_index]["study_id"])] = group.iloc[donor_index]
    return donors


def create_context_interventions(df: pd.DataFrame, *, seed: int = BOOTSTRAP_SEED) -> pd.DataFrame:
    """Create C0/C1/C2 for naturally informative studies only."""

    if seed != BOOTSTRAP_SEED:
        raise ContractError(f"C2 seed is frozen at {BOOTSTRAP_SEED}")
    validate_context_payload(df)
    eligible = df[df["context_state"].eq("informative")].copy()
    if eligible.empty:
        raise ContractError("C0/C1/C2 require informative natural context")
    eligible["context_length_bin"] = eligible["context_text"].map(context_length_bin)

    study_columns = [
        "site_id", "split_id", "patient_id", "study_id", "context_text", "context_length_bin"
    ]
    studies = eligible[study_columns].drop_duplicates("study_id")
    donor_map = _study_donor_map(studies, seed=seed)

    c0 = eligible.copy()
    c0["intervention"] = "C0"
    c0["controlled_context_state"] = "original_context"
    c0["context_donor_patient_id"] = c0["patient_id"]
    c0["context_donor_site_id"] = c0["site_id"]
    c0["context_donor_split_id"] = c0["split_id"]
    c0["context_donor_length_bin"] = c0["context_length_bin"]

    c1 = eligible.copy()
    c1["intervention"] = "C1"
    c1["controlled_context_state"] = "no_context"
    c1["context_text"] = "[NO_CONTEXT]"
    c1["context_donor_patient_id"] = pd.NA
    c1["context_donor_site_id"] = c1["site_id"]
    c1["context_donor_split_id"] = c1["split_id"]
    c1["context_donor_length_bin"] = c1["context_length_bin"]
    for pathology, image_column, multimodal_column in zip(
        PATHOLOGIES, IMAGE_PROBABILITY_COLUMNS, MULTIMODAL_PROBABILITY_COLUMNS
    ):
        del pathology
        c1[multimodal_column] = c1[image_column].astype(float)

    c2 = eligible.copy()
    c2["intervention"] = "C2"
    c2["controlled_context_state"] = "misaligned_context"
    for index, row in c2.iterrows():
        donor = donor_map[str(row["study_id"])]
        c2.at[index, "context_text"] = donor["context_text"]
        c2.at[index, "context_donor_patient_id"] = donor["patient_id"]
        c2.at[index, "context_donor_site_id"] = donor["site_id"]
        c2.at[index, "context_donor_split_id"] = donor["split_id"]
        c2.at[index, "context_donor_length_bin"] = donor["context_length_bin"]
        for pathology, image_column, multimodal_column in zip(
            PATHOLOGIES, IMAGE_PROBABILITY_COLUMNS, MULTIMODAL_PROBABILITY_COLUMNS
        ):
            c2.at[index, multimodal_column] = _c2_probability(
                float(row[image_column]), str(donor["context_text"]), pathology
            )

    out = pd.concat([c0, c1, c2], ignore_index=True)
    validate_interventions(out)
    return out


def validate_interventions(df: pd.DataFrame) -> None:
    required = {
        "intervention", "study_id", "image_id", "patient_id", "site_id", "split_id",
        "context_donor_patient_id", "context_donor_site_id", "context_donor_split_id",
        "context_length_bin", "context_donor_length_bin",
    }
    missing = required - set(df.columns)
    if missing:
        raise ContractError(f"intervention table missing columns: {sorted(missing)}")
    groups = {name: part for name, part in df.groupby("intervention", observed=True)}
    if set(groups) != {"C0", "C1", "C2"}:
        raise ContractError("interventions must be exactly C0, C1, and C2")
    study_sets = [set(groups[name]["study_id"]) for name in ("C0", "C1", "C2")]
    if not (study_sets[0] == study_sets[1] == study_sets[2]):
        raise ContractError("C0, C1, and C2 must have identical study IDs")
    image_sets = [set(groups[name]["image_id"]) for name in ("C0", "C1", "C2")]
    if not (image_sets[0] == image_sets[1] == image_sets[2]):
        raise ContractError("C0, C1, and C2 must have identical image IDs")
    if not groups["C1"]["context_text"].eq("[NO_CONTEXT]").all():
        raise ContractError("C1 must replace context with exactly [NO_CONTEXT]")

    c2 = groups["C2"]
    if c2["patient_id"].eq(c2["context_donor_patient_id"]).any():
        raise ContractError("C2 donor must belong to a different patient")
    if not c2["site_id"].eq(c2["context_donor_site_id"]).all():
        raise ContractError("C2 donor crossed site")
    if not c2["split_id"].eq(c2["context_donor_split_id"]).all():
        raise ContractError("C2 donor crossed split")
    if not c2["context_length_bin"].eq(c2["context_donor_length_bin"]).all():
        raise ContractError("C2 donor crossed context-length bin")

    ordered = [groups[name].sort_values("image_id") for name in ("C0", "C1", "C2")]
    for column in IMAGE_PROBABILITY_COLUMNS:
        if not (
            np.array_equal(ordered[0][column].to_numpy(), ordered[1][column].to_numpy())
            and np.array_equal(ordered[0][column].to_numpy(), ordered[2][column].to_numpy())
        ):
            raise ContractError("image-only probabilities changed across C0/C1/C2")

    validate_context_payload(df)
