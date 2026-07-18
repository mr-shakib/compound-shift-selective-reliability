"""Deterministic fictional records for Stage 2B.

The generated strings are administrative fantasy phrases, not imitations of
medical reports.  Probabilities are arithmetic fixtures, not model outputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .contracts import (
    EXTERNAL_SITE_ID,
    EXTERNAL_SPLIT,
    IMAGE_PROBABILITY_COLUMNS,
    MULTIMODAL_PROBABILITY_COLUMNS,
    PATHOLOGIES,
    PRIMARY_LABEL_SOURCE,
    SENSITIVITY_LABEL_SOURCE,
    SOURCE_SITE_ID,
    validate_data_contract,
)

_SOURCE_SPLIT_ORDER = ("train", "calibration", "validation", "test")


def _context_for(patient_number: int, study_number: int) -> tuple[str, str]:
    if study_number == 0:
        colors = ("amber", "violet", "silver", "teal", "coral", "indigo", "gold", "azure")
        text = (
            f"fictional orchard schedule marker {colors[patient_number % len(colors)]} "
            f"group {patient_number % 3}"
        )
        return text, "informative"
    if patient_number % 2 == 0:
        return "routine fictional note", "low_information"
    return "", "absent"


def _label(patient_number: int, study_number: int, pathology_number: int,
           site_number: int, source_offset: int) -> int:
    return int((patient_number + study_number + pathology_number + site_number + source_offset) % 2)


def _image_probability(label: int, *, signature: int, external: bool) -> float:
    base = (0.70 if label else 0.30) if external else (0.78 if label else 0.22)
    error_modulus = 5 if external else 7
    if signature % error_modulus == 0:
        base = 0.36 if label else 0.64
    jitter = ((signature % 5) - 2) * 0.025
    return float(np.clip(base + jitter, 0.02, 0.98))


def _multimodal_probability(image_probability: float, label: int, context_state: str,
                            *, external: bool, signature: int) -> float:
    if context_state == "informative":
        shift = 0.09 if not external else 0.05
    elif context_state == "low_information":
        shift = 0.02
    else:
        shift = 0.0
    direction = 1.0 if label else -1.0
    # A few deterministic context-sensitive failures ensure failure metrics are executable.
    if signature % (8 if external else 11) == 0:
        direction *= -1.0
    return float(np.clip(image_probability + direction * shift, 0.01, 0.99))


def generate_synthetic_records(
    *,
    seed: int = 20260718,
    label_source: str = PRIMARY_LABEL_SOURCE,
) -> pd.DataFrame:
    """Return a deterministic image-level synthetic contract table.

    ``seed`` is recorded and mixed into arithmetic signatures; no randomness is
    used to create identifiers or text.  Both allowed label sources can be
    generated as separate tables.  They are never merged on image ID.
    """

    if label_source not in {PRIMARY_LABEL_SOURCE, SENSITIVITY_LABEL_SOURCE}:
        raise ValueError("synthetic generator supports only the two locked label sources")
    source_offset = 0 if label_source == PRIMARY_LABEL_SOURCE else 1
    seed_offset = seed % 97
    rows: list[dict] = []

    site_specs = [
        (SOURCE_SITE_ID, _SOURCE_SPLIT_ORDER, 6, 0, "SRC"),
        (EXTERNAL_SITE_ID, (EXTERNAL_SPLIT,), 8, 1, "EXT"),
    ]
    for site_id, splits, patients_per_split, site_number, site_code in site_specs:
        for split_number, split_id in enumerate(splits):
            for patient_number in range(patients_per_split):
                patient_id = f"SYN-{site_code}-{split_id.upper()}-P{patient_number:02d}"
                for study_number in range(2):
                    study_id = f"SYN-{site_code}-{split_id.upper()}-S{patient_number:02d}-{study_number}"
                    context_text, context_state = _context_for(patient_number, study_number)
                    # Alternate one-image and three-image studies within every context
                    # state.  Three-image studies contain two eligible frontal fixtures
                    # and one explicitly excluded lateral fixture.
                    image_count = 1 if (patient_number + study_number) % 2 == 0 else 3
                    labels = {
                        pathology: _label(
                            patient_number,
                            study_number,
                            pathology_number,
                            site_number,
                            source_offset,
                        )
                        for pathology_number, pathology in enumerate(PATHOLOGIES)
                    }
                    for image_number in range(image_count):
                        view = "lateral" if image_count == 3 and image_number == 2 else "frontal"
                        row: dict[str, object] = {
                            "site_id": site_id,
                            "split_id": split_id,
                            "patient_id": patient_id,
                            "study_id": study_id,
                            "image_id": f"SYN-{site_code}-{split_id.upper()}-I{patient_number:02d}-{study_number}-{image_number}",
                            "view": view,
                            "context_text": context_text,
                            "context_state": context_state,
                            "label_source": label_source,
                            **labels,
                        }
                        for pathology_number, pathology in enumerate(PATHOLOGIES):
                            signature = (
                                seed_offset
                                + site_number * 41
                                + split_number * 17
                                + patient_number * 13
                                + study_number * 7
                                + image_number * 3
                                + pathology_number
                            )
                            image_probability = _image_probability(
                                labels[pathology],
                                signature=signature,
                                external=site_id == EXTERNAL_SITE_ID,
                            )
                            row[IMAGE_PROBABILITY_COLUMNS[pathology_number]] = image_probability
                            row[MULTIMODAL_PROBABILITY_COLUMNS[pathology_number]] = (
                                _multimodal_probability(
                                    image_probability,
                                    labels[pathology],
                                    context_state,
                                    external=site_id == EXTERNAL_SITE_ID,
                                    signature=signature,
                                )
                            )
                        rows.append(row)

    frame = pd.DataFrame(rows)
    validate_data_contract(frame)
    return frame


def synthetic_counts(df: pd.DataFrame) -> dict[str, int]:
    return {
        "patients": int(df["patient_id"].nunique()),
        "studies": int(df["study_id"].nunique()),
        "images": int(df["image_id"].nunique()),
    }
