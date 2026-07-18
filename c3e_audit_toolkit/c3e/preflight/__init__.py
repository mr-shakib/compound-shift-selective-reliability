"""Synthetic-only C3-E6 Stage 2B data-contract preflight.

This package never loads images, medical reports, or real patient records and
contains no training code.  It exists to exercise the frozen protocol with
deterministic fictional records before any real-data intake.
"""

from .contracts import (
    PATHOLOGIES,
    PRIMARY_LABEL_SOURCE,
    SENSITIVITY_LABEL_SOURCE,
    FORBIDDEN_LABEL_SOURCE,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    SOURCE_COVERAGES,
    ContractError,
)

__all__ = [
    "PATHOLOGIES",
    "PRIMARY_LABEL_SOURCE",
    "SENSITIVITY_LABEL_SOURCE",
    "FORBIDDEN_LABEL_SOURCE",
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_SEED",
    "SOURCE_COVERAGES",
    "ContractError",
]
