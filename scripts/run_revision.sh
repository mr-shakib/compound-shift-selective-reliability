#!/usr/bin/env bash
# Revision R1 (2026-10-06): reproduce every CPU-side revision artifact, the
# manuscript tables/figures, and both PDFs from the verified prediction caches.
#
# Prerequisites: the Stage 8/9b caches in data/predictions/, the restricted
# label/metadata files in data/, and (for comparators, Stage 7 replay and
# calibration uncertainty) the calibration-tier revision caches written by
# step 1 of scripts/run_revision_gpu_queue.sh.
#
# Wall time: ~15 min on 12 CPU cores. Outputs: results/c3e_revision/,
# paper/revision/generated/, paper/revision/figures/, paper/revision/*.pdf.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=c3e_audit_toolkit/.venv/bin/python

$PY protocols/C3E6_stage2/scripts/validate_protocol.py
(cd c3e_audit_toolkit && .venv/bin/python -m pytest -q)
$PY -m c3e.revision.runner            # aborts if any Stage 10 estimate fails to replay exactly
$PY -m c3e.revision.report
(cd paper/revision && latexmk -pdf -interaction=nonstopmode main_revised.tex supplement_revised.tex)
echo "Revision R1 artifacts rebuilt."
