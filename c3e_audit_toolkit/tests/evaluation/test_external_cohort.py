"""Guards on the external-site cohort construction. Fixtures are synthetic."""

from __future__ import annotations

import pandas as pd
import pytest

from c3e.external.dataset import PERMITTED_COLUMNS
from c3e.evaluation.interventions import natural_state


def test_permitted_columns_match_the_frozen_policy():
    """These are named in text_policy.permitted_sections_external and are the
    only external context the protocol allows as model input."""
    assert PERMITTED_COLUMNS == ("section_clinical_history", "section_history")


def test_forbidden_sections_are_not_permitted_columns():
    for forbidden in ("section_findings", "section_impression", "report",
                      "section_summary"):
        assert forbidden not in PERMITTED_COLUMNS


def test_informativeness_rule_is_the_source_site_rule():
    """The rule transfers frozen. Refitting a threshold on external text would
    be external-site tuning, which the registry prohibits."""
    assert natural_state("") == "N3"
    assert natural_state("___ ___") == "N3"
    assert natural_state("chest pain") == "N2"
    assert natural_state("acute onset chest pain today") == "N1"


def test_empty_context_columns_concatenate_to_absent():
    parts = [pd.Series(["", None]).fillna("").astype(str),
             pd.Series([None, ""]).fillna("").astype(str)]
    ctx = (parts[0] + " " + parts[1]).str.strip()
    assert all(natural_state(c) == "N3" for c in ctx)
