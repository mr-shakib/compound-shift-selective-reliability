"""Fail-closed checks for post-diagnostic text and forbidden label sources."""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from .contracts import ContractError, FORBIDDEN_MODEL_INPUT_COLUMNS

_FORBIDDEN_SECTION_MARKERS = re.compile(
    r"(?:^|\n)\s*(?:FINDINGS|IMPRESSION|FULL REPORT|COMPLETE REPORT|SUMMARY)\s*:",
    re.IGNORECASE,
)


def validate_model_input_columns(columns: Iterable[str]) -> None:
    normalized = {str(c).strip().lower() for c in columns}
    forbidden = normalized & FORBIDDEN_MODEL_INPUT_COLUMNS
    if forbidden:
        raise ContractError(f"forbidden model-input columns: {sorted(forbidden)}")


def validate_context_payload(df: pd.DataFrame, *, text_column: str = "context_text") -> None:
    validate_model_input_columns(df.columns)
    if text_column not in df.columns:
        raise ContractError(f"missing permitted context payload column: {text_column}")
    contaminated = df[text_column].fillna("").astype(str).str.contains(
        _FORBIDDEN_SECTION_MARKERS, regex=True
    )
    if contaminated.any():
        raise ContractError("forbidden post-diagnostic section marker in context payload")
