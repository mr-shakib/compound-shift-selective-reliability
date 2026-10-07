"""Controlled label-source analysis (post hoc; Revision R1).

The published S1 run changed four things at once relative to the primary:
(1) the label set, (2) the source evaluation cohort (14,766 -> 9,293 studies,
those with a findings section), (3) the classification thresholds and
abstention cutoffs, re-selected on findings calibration labels, and (4) the
C2 donor realisation at the source, because the C2 rotation is defined within
the cohort. Model parameters did not change (identical checkpoint digests) and
no calibration transform exists in the pipeline.

This module changes one factor at a time:

  A0  primary: impression cohort, impression thresholds, impression labels
  A1  label swap only: same studies, same probabilities, same thresholds and
      cutoffs (so identical decisions and identical accepted sets); findings
      labels joined by study identifier. Source studies without a findings
      section have no findings label and become unsupervised.
  A1c common-observed cells: A0 and A1 recomputed on cells labelled under
      both sources only. Selection caveat: these cells are the subset both
      report sections mention, which is not a random subset.
  A2x cohort only: findings cohort, impression thresholds, impression labels
  A2  cohort + labels: findings cohort, impression thresholds, findings labels
  A3  + thresholds: findings thresholds and cutoffs = the published S1
  B2  alternative order: impression cohort, findings labels, findings thresholds

Differences between consecutive steps are reported along both orders; when
they disagree the factors interact and no unique additive decomposition is
claimed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..calibration.policy import TARGETS
from .engine import Site, frozen_policy, labels_from_raw, load_site
from .estimators import ESTIMATORS
from .hypotheses import run_family


def _raw_on(target: Site, donor: Site, key: str) -> np.ndarray:
    """Raw labels of ``donor`` re-indexed onto ``target`` rows by study key."""
    d = donor.cohort.set_index(key)[TARGETS]
    return d.reindex(target.cohort[key]).to_numpy(dtype=float)


def _describe(raw_or_mask: tuple[np.ndarray, np.ndarray]) -> dict[str, float]:
    labels, mask = raw_or_mask
    n = len(mask)
    cells = mask.sum()
    return {"studies": int(n), "evaluable_studies": int((mask.sum(1) > 0).sum()),
            "evaluable_fraction": float((mask.sum(1) > 0).mean()) if n else float("nan"),
            "labelled_cell_density": float(cells / (5 * n)) if n else float("nan"),
            "positive_rate_labelled": float((labels * mask).sum() / cells) if cells else float("nan")}


def run(root: Path, *, replicates: int = 2000, estimators=ESTIMATORS) -> dict[str, Any]:
    root = Path(root)
    sI = load_site(root, "source", label_source="impression")
    sF = load_site(root, "source", label_source="findings")
    eI = load_site(root, "external", label_source="impression")
    eF = load_site(root, "external", label_source="findings")
    if not np.array_equal(eI.cohort["study_key"].to_numpy(), eF.cohort["study_key"].to_numpy()):
        raise RuntimeError("external cohorts differ between label sources")
    polI, polF = frozen_policy(root, "impression"), frozen_policy(root, "findings")

    lab = {
        "src_I_on_SI": labels_from_raw(sI.raw),
        "src_F_on_SI": labels_from_raw(_raw_on(sI, sF, "study_id")),
        "src_F_on_SF": labels_from_raw(sF.raw),
        "src_I_on_SF": labels_from_raw(_raw_on(sF, sI, "study_id")),
        "ext_I": labels_from_raw(eI.raw),
        "ext_F": labels_from_raw(eF.raw),
    }
    # Common-observed cells.
    m_src_c = lab["src_I_on_SI"][1] * lab["src_F_on_SI"][1]
    m_ext_c = lab["ext_I"][1] * lab["ext_F"][1]

    configs = {
        "A0_primary": dict(src=sI, ext=eI, pol=polI, ls=lab["src_I_on_SI"], le=lab["ext_I"]),
        "A1_label_swap_only": dict(src=sI, ext=eI, pol=polI, ls=lab["src_F_on_SI"], le=lab["ext_F"]),
        "A1c_common_cells_impression": dict(src=sI, ext=eI, pol=polI,
                                            ls=(lab["src_I_on_SI"][0], m_src_c),
                                            le=(lab["ext_I"][0], m_ext_c)),
        "A1c_common_cells_findings": dict(src=sI, ext=eI, pol=polI,
                                          ls=(lab["src_F_on_SI"][0], m_src_c),
                                          le=(lab["ext_F"][0], m_ext_c)),
        "A2x_cohort_only": dict(src=sF, ext=eI, pol=polI, ls=lab["src_I_on_SF"], le=lab["ext_I"]),
        "A2_cohort_and_labels": dict(src=sF, ext=eI, pol=polI, ls=lab["src_F_on_SF"], le=lab["ext_F"]),
        "A3_published_S1": dict(src=sF, ext=eF, pol=polF, ls=lab["src_F_on_SF"], le=lab["ext_F"]),
        "B2_labels_and_thresholds_on_primary_cohort": dict(src=sI, ext=eI, pol=polF,
                                                           ls=lab["src_F_on_SI"], le=lab["ext_F"]),
    }
    out: dict[str, Any] = {"configs": {}, "factors": {
        "model_parameters_changed": False,
        "calibration_transform_exists": False,
        "source_cohort_primary": sI.n, "source_cohort_findings": sF.n,
        "external_cohort": eI.n,
        "source_findings_cohort_subset_of_primary": bool(set(sF.cohort.study_id) <= set(sI.cohort.study_id)),
    }}
    # Decision identity across caches (external C0): probabilities agree to float32
    # rounding, but identical decisions must be checked, not assumed.
    dec_diff = {}
    for m in ("M1", "M2", "M3", "M4"):
        pa, pb = eI.probs[(m, "C0")], eF.probs[(m, "C0")]
        dpa = (pa >= polI.thresholds[m]).astype(int); dpb = (pb >= polI.thresholds[m]).astype(int)
        acc_a, acc_b = polI.accepted(m, pa), polI.accepted(m, pb)
        dec_diff[m] = {"max_abs_prob_diff": float(np.abs(pa - pb).max()),
                       "cells_with_different_decision_same_thresholds": int((dpa != dpb).sum()),
                       "studies_with_different_acceptance_same_cutoff": int((acc_a != acc_b).sum()),
                       "cells_with_different_decision_findings_vs_impression_thresholds":
                           int(((pb >= polF.thresholds[m]) != (pa >= polI.thresholds[m])).sum()),
                       "studies_with_different_acceptance_findings_vs_impression_cutoff":
                           int((polF.accepted(m, pb) != acc_a).sum())}
    out["external_decision_identity"] = dec_diff
    out["thresholds"] = {"impression": {m: polI.thresholds[m].tolist() for m in polI.thresholds},
                         "findings": {m: polF.thresholds[m].tolist() for m in polF.thresholds},
                         "cutoff_impression_0.80": polI.cutoffs, "cutoff_findings_0.80": polF.cutoffs,
                         "target_order": TARGETS}

    for name, c in configs.items():
        fam = run_family(c["src"], c["ext"], c["pol"], labels_src=c["ls"][0], mask_src=c["ls"][1],
                         labels_ext=c["le"][0], mask_ext=c["le"][1], replicates=replicates,
                         estimators=estimators)
        out["configs"][name] = {
            "source_labels": _describe(c["ls"]), "external_labels": _describe(c["le"]),
            "policy": c["pol"].name, "source_cohort_studies": c["src"].n,
            "external_cohort_studies": c["ext"].n,
            "contrasts": fam["contrasts"], "levels": fam["levels"],
            "coverage_gap": fam["coverage_gap"],
            "c2_realisation": ("findings-cohort rotation" if c["src"] is sF
                               else "primary-cohort rotation"),
        }
    return out
