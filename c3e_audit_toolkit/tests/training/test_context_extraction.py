"""Guards on pre-diagnostic context extraction.

These exist because a real defect shipped: SECTION_MAP returns
(canonical_name, class) pairs, the extractor compared the pair against a bare
name, and every study silently received empty context. M2 then trained to
exactly chance and would have been reported as evidence that pre-diagnostic
text carries no signal.

The lesson generalises. A context extractor that returns nothing looks like a
scientific finding rather than a bug, so emptiness has to be asserted, not
eyeballed.

All fixtures below are synthetic and contain no patient data.
"""

from __future__ import annotations

import pytest

from c3e.training.dataset import PERMITTED_SECTIONS, extract_permitted_context

SYNTHETIC_REPORT = """                                 FINAL REPORT
 EXAMINATION:  CHEST (PA AND LAT)

 INDICATION:  ___-year-old man with shortness of breath.

 HISTORY:  Prior smoker, evaluate for effusion.

 TECHNIQUE:  Chest PA and lateral

 COMPARISON:  Prior study from ___

 FINDINGS:
 The heart size is enlarged. There is a small left pleural effusion.

 IMPRESSION:
 Cardiomegaly with small left pleural effusion.
"""


def test_extracts_permitted_sections():
    out = extract_permitted_context(SYNTHETIC_REPORT)
    assert out.strip(), "permitted context must not be empty for a report that has it"
    assert "shortness of breath" in out
    assert "Prior smoker" in out


def test_excludes_label_sources():
    """Findings and impression are forbidden model input, not merely unused."""
    out = extract_permitted_context(SYNTHETIC_REPORT).lower()
    assert "heart size is enlarged" not in out
    assert "cardiomegaly" not in out


def test_excludes_other_pre_diagnostic_sections():
    """Only indication and history are permitted; technique and comparison are not."""
    out = extract_permitted_context(SYNTHETIC_REPORT).lower()
    assert "pa and lateral" not in out
    assert "prior study" not in out


def test_excludes_wet_read():
    """A WET READ is a preliminary interpretation and is post-diagnostic."""
    report = SYNTHETIC_REPORT.replace(
        " TECHNIQUE:  Chest PA and lateral",
        " WET READ:  Probable effusion, please correlate.")
    out = extract_permitted_context(report).lower()
    assert "probable effusion" not in out


def test_empty_when_no_permitted_sections():
    report = " FINDINGS:\n Normal.\n\n IMPRESSION:\n No acute process.\n"
    assert extract_permitted_context(report).strip() == ""


def test_no_recognised_header_returns_empty():
    assert extract_permitted_context("no headers here at all").strip() == ""


@pytest.mark.parametrize("section", PERMITTED_SECTIONS)
def test_each_permitted_section_alone_is_extracted(section):
    header = {"indication": "INDICATION", "history": "HISTORY"}[section]
    report = f" {header}:  distinctive marker text\n\n FINDINGS:\n Normal.\n"
    assert "distinctive marker text" in extract_permitted_context(report)


def test_section_map_values_are_pairs_not_names():
    """Pins the shape that caused the original defect.

    If SECTION_MAP ever becomes a plain name map, the extractor's unpacking must
    be revisited, and this test is the tripwire.
    """
    from c3e.mimic_intake.stage3b_reports import SECTION_MAP

    mapped = SECTION_MAP["INDICATION"]
    assert isinstance(mapped, tuple), "extractor unpacks mapped[0]; shape changed"
    assert mapped[0] == "indication"
