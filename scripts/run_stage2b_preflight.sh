#!/usr/bin/env bash
# C3-E6 Stage 2B: synthetic-only data-contract and metric dry-run.
# No medical images, real records, model training, or external tuning.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLKIT="$PROJECT_ROOT/c3e_audit_toolkit"
PROTOCOL="$PROJECT_ROOT/protocols/C3E6_stage2"
OUTPUT="$PROJECT_ROOT/results/c3e_preflight"
PYTHON="$TOOLKIT/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "ERROR: project Python not found at c3e_audit_toolkit/.venv/bin/python" >&2
  exit 1
fi
if [ ! -f "$PROTOCOL/MANIFEST.sha256" ]; then
  echo "ERROR: frozen Stage 2 protocol bundle is missing" >&2
  exit 1
fi

echo "C3-E6 Stage 2B synthetic preflight"
echo "SYNTHETIC DATA ONLY"
echo "NO MEDICAL IMAGES LOADED"
echo "NO MODEL TRAINING PERFORMED"
echo "EXTERNAL TUNING DISABLED"
echo

(
  cd "$PROTOCOL"
  sha256sum -c MANIFEST.sha256
)

cd "$PROJECT_ROOT"
"$PYTHON" protocols/C3E6_stage2/scripts/validate_protocol.py
PYTHONPATH="$TOOLKIT${PYTHONPATH:+:$PYTHONPATH}" \
  "$PYTHON" -m c3e.preflight.runner \
    --protocol-root "$PROTOCOL" \
    --output "$OUTPUT" \
    --project-root "$PROJECT_ROOT" \
    --run-tests

echo
echo "Stage 2B reports written under results/c3e_preflight/"
