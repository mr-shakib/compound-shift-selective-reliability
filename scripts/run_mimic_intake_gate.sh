#!/usr/bin/env bash
# C3-E6 Stage 3A: MIMIC access, file inventory, and metadata-readiness only.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLKIT="$PROJECT_ROOT/c3e_audit_toolkit"
PROTOCOL="$PROJECT_ROOT/protocols/C3E6_stage2"
CONFIG="$TOOLKIT/configs/mimic_intake.yaml"
PYTHON="$TOOLKIT/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "ERROR: project Python is unavailable" >&2
  exit 2
fi

echo "C3-E6 Stage 3A MIMIC intake gate"
echo "STAGE 3A ONLY"
echo "METADATA AND ACCESS INVENTORY"
echo "NO MEDICAL IMAGES OPENED"
echo "NO REPORT TEXT EXPORTED"
echo "NO MODEL TRAINING"
echo "NO CHEXBERT EXECUTION"
echo "NO EXTERNAL DATA ACCESSED"
echo "NO TARGET-SITE TUNING"

(
  cd "$PROTOCOL"
  sha256sum -c MANIFEST.sha256
)

cd "$PROJECT_ROOT"
"$PYTHON" protocols/C3E6_stage2/scripts/validate_protocol.py
git check-ignore --quiet -- data/mimic
git check-ignore --quiet -- data/mimic/.stage3a-ignore-probe

cd "$TOOLKIT"
"$PYTHON" -m pytest tests/mimic_intake -q

cd "$PROJECT_ROOT"
PYTHONPATH="$TOOLKIT${PYTHONPATH:+:$PYTHONPATH}" \
  "$PYTHON" -m c3e.mimic_intake.runner \
    --project-root "$PROJECT_ROOT" \
    --config "$CONFIG" \
    --protocol-root "$PROTOCOL"
