"""Audit of the C2 misaligned-context assignment (post hoc; Revision R1).

Stage 8/9b reported "studies retaining their own context under C2": 6 at the
source and 34 at the external site. The invariant behind that count compared
C2 and C0 *context strings* on rows whose patient column C2 never changes, so
it counted rows with identical text, whatever the donor. It could not tell a
genuine same-patient assignment from identical boilerplate donated by another
patient, and it counted image rows, not studies.

This module replays ``apply_c2`` with the donor of every row recorded,
verifies that the replay reproduces ``apply_c2``'s output exactly, and then
classifies every recipient. Aggregates only.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..evaluation.interventions import (C2_SEED, _tiebreak_column, apply_c2, check_invariants,
                                        apply_c1, effective_tokens, length_bin)

TARGET_TERMS = {
    "Cardiomegaly": ("cardiomegaly", "enlarged heart", "cardiac enlargement"),
    "Edema": ("edema", "chf", "heart failure", "fluid overload", "volume overload"),
    "Consolidation": ("consolidation", "pneumonia", "infiltrate"),
    "Atelectasis": ("atelectasis", "collapse"),
    "Pleural Effusion": ("effusion",),
}


def c2_with_donors(frame: pd.DataFrame, *, seed: int = C2_SEED) -> tuple[pd.DataFrame, np.ndarray]:
    """Replica of ``apply_c2`` that also returns each row's donor position."""
    out = frame.copy()
    out["_bin"] = out["context"].map(length_bin)
    tiebreak = _tiebreak_column(out)
    split_col = "split" if "split" in out.columns else None
    new_context = out["context"].to_numpy(dtype=object).copy()
    donor_pos = np.arange(len(out))
    group_cols = ["_bin"] + ([split_col] if split_col else [])
    rng = np.random.default_rng(seed)
    for _, idx in out.groupby(group_cols, sort=True).groups.items():
        rows = np.asarray(idx)
        if len(rows) < 2:
            continue
        order = out.loc[rows].sort_values(["subject_id", tiebreak]).index.to_numpy()
        patients = out.loc[order, "subject_id"].to_numpy()
        n = len(order)
        offset = int(rng.integers(1, n)) if n > 1 else 0
        for k in range(n):
            donor = order[(k + offset) % n]
            step = 1
            while patients[(k + offset + step - 1) % n] == patients[k] and step <= n:
                donor = order[(k + offset + step) % n]
                step += 1
            pos = out.index.get_loc(order[k])
            new_context[pos] = out.at[donor, "context"]
            donor_pos[pos] = out.index.get_loc(donor)
    out["context"] = new_context
    return out.drop(columns=["_bin"]), donor_pos


def audit(c0: pd.DataFrame, *, site: str, seed: int = C2_SEED) -> dict[str, Any]:
    c0 = c0.reset_index(drop=True)
    replica, donor = c2_with_donors(c0, seed=seed)
    official = apply_c2(c0, seed=seed)
    faithful = bool((replica["context"].to_numpy() == official["context"].to_numpy()).all())
    if not faithful:
        raise RuntimeError("C2 replica does not reproduce apply_c2")
    inv = check_invariants(c0, apply_c1(c0), official)

    rec_pat = c0["subject_id"].astype(str).to_numpy()
    don_pat = rec_pat[donor]
    rec_study = c0["study_id"].astype(str).to_numpy()
    don_study = rec_study[donor]
    rec_ctx = c0["context"].to_numpy(dtype=object)
    new_ctx = official["context"].to_numpy(dtype=object)
    same_patient = rec_pat == don_pat
    self_row = donor == np.arange(len(c0))
    identical_text = rec_ctx == new_ctx

    frame = pd.DataFrame({"study": rec_study, "same_patient": same_patient,
                          "identical_text": identical_text, "donor_study": don_study,
                          "new_ctx": new_ctx})
    g = frame.groupby("study")
    n_donor_studies = g["donor_study"].nunique()
    n_distinct_ctx = g["new_ctx"].nunique()
    study_same_patient = g["same_patient"].any()
    study_identical = g["identical_text"].any()
    study_identical_diff_patient = (frame.assign(x=identical_text & ~same_patient)
                                    .groupby("study")["x"].any())

    # Crude lexical signal of clinical (in)compatibility: does the donor's text
    # name a target finding that the recipient's text does not, or vice versa?
    def mentions(texts):
        low = pd.Series(texts).astype(str).str.lower()
        return np.column_stack([low.str.contains("|".join(v)).to_numpy()
                                for v in TARGET_TERMS.values()])
    m_rec, m_new = mentions(rec_ctx), mentions(new_ctx)
    rows_any_target_discordant = (m_rec != m_new).any(1)

    return {
        "site": site, "c2_seed": seed, "replica_reproduces_apply_c2": faithful,
        "image_rows": int(len(c0)), "studies": int(frame["study"].nunique()),
        "patients": int(len(set(rec_pat))),
        "stage_invariant_count_reproduced": inv["c2_studies_retaining_own_context"],
        "rows_identical_text": int(identical_text.sum()),
        "rows_identical_text_from_different_patient": int((identical_text & ~same_patient).sum()),
        "rows_same_patient_donor": int(same_patient.sum()),
        "rows_self_donor": int(self_row.sum()),
        "studies_with_same_patient_donor_any_image": int(study_same_patient.sum()),
        "studies_with_identical_text_any_image": int(study_identical.sum()),
        "studies_with_identical_text_from_different_patient": int(study_identical_diff_patient.sum()),
        "studies_whose_images_received_multiple_donor_studies": int((n_donor_studies > 1).sum()),
        "studies_whose_images_received_different_context_strings": int((n_distinct_ctx > 1).sum()),
        "multi_image_studies": int((g.size() > 1).sum()),
        "rows_donor_target_term_profile_differs": int(rows_any_target_discordant.sum()),
        "fraction_rows_donor_target_term_profile_differs": float(rows_any_target_discordant.mean()),
        "recipient_rows_mentioning_any_target_term": int(m_rec.any(1).sum()),
        "mean_effective_tokens_recipient": float(np.mean([effective_tokens(t) for t in rec_ctx])),
        "mean_effective_tokens_donor": float(np.mean([effective_tokens(t) for t in new_ctx])),
    }
