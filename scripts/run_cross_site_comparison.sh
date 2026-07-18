#!/usr/bin/env bash
# Compare the local MIMIC and CheXpert Plus audit outputs (study_aggregate.csv
# from each site) and write the cross-site comparison and gate report.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLKIT="$WORKSPACE/c3e_audit_toolkit"
VENV="$TOOLKIT/.venv"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  --source PATH   MIMIC study_aggregate.csv (env: SOURCE_AGGREGATE, default: results/c3e_mimic/study_aggregate.csv)
  --target PATH   CheXpert Plus study_aggregate.csv (env: TARGET_AGGREGATE, default: results/c3e_chexpert_plus/study_aggregate.csv)
  --output PATH   output directory (env: CROSS_SITE_OUTPUT, default: results/c3e_cross_site)
  -h, --help      show this help text
EOF
}

SOURCE="${SOURCE_AGGREGATE:-$WORKSPACE/results/c3e_mimic/study_aggregate.csv}"
TARGET="${TARGET_AGGREGATE:-$WORKSPACE/results/c3e_chexpert_plus/study_aggregate.csv}"
OUTPUT="${CROSS_SITE_OUTPUT:-$WORKSPACE/results/c3e_cross_site}"

while [ $# -gt 0 ]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: source study_aggregate.csv not found: $SOURCE" >&2
  echo "Run scripts/run_mimic_audit.sh first." >&2
  exit 1
fi
if [ ! -f "$TARGET" ]; then
  echo "ERROR: target study_aggregate.csv not found: $TARGET" >&2
  echo "Run scripts/run_chexpert_audit.sh first." >&2
  exit 1
fi

if [ ! -f "$VENV/bin/activate" ]; then
  echo "ERROR: virtual environment not found at $VENV. Run the toolkit setup first." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"

if ! command -v c3e-audit >/dev/null 2>&1; then
  echo "ERROR: c3e-audit is not installed in the active virtual environment." >&2
  exit 1
fi

mkdir -p "$OUTPUT"

echo "Running cross-site comparison..."
echo "  source: $SOURCE"
echo "  target: $TARGET"
echo "  output: $OUTPUT"
echo

c3e-audit compare \
  --source "$SOURCE" \
  --target "$TARGET" \
  --output "$OUTPUT"

echo
echo "Cross-site comparison written to $OUTPUT (cross_site_comparison.csv, cross_site_gate.json)."
echo "These outputs are aggregate-only and safe to share per docs/DATA_SAFETY.md."
