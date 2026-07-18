#!/usr/bin/env bash
# Run the C3-E report-only, metadata-only audit against a local, authorized
# CheXpert Plus merged table. Never contains credentials.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLKIT="$WORKSPACE/c3e_audit_toolkit"
VENV="$TOOLKIT/.venv"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  --table PATH      merged CheXpert Plus table: CSV, CSV.GZ, or Parquet
                     (env: CHEXPERT_TABLE, default: data/chexpert_plus/chexpert_plus_merged.parquet)
  --config PATH     audit config YAML (env: CHEXPERT_CONFIG, default: toolkit configs/chexpert_plus.yaml)
  --terms PATH      target-term YAML (env: CHEXPERT_TERMS, default: toolkit configs/terms.yaml)
  --output PATH     output directory (env: CHEXPERT_OUTPUT, default: results/c3e_chexpert_plus)
  -h, --help        show this help text
EOF
}

TABLE="${CHEXPERT_TABLE:-$WORKSPACE/data/chexpert_plus/chexpert_plus_merged.parquet}"
CONFIG="${CHEXPERT_CONFIG:-$TOOLKIT/configs/chexpert_plus.yaml}"
TERMS="${CHEXPERT_TERMS:-$TOOLKIT/configs/terms.yaml}"
OUTPUT="${CHEXPERT_OUTPUT:-$WORKSPACE/results/c3e_chexpert_plus}"

while [ $# -gt 0 ]; do
  case "$1" in
    --table) TABLE="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    --terms) TERMS="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

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

case "$TABLE" in
  *.csv|*.csv.gz|*.parquet) ;;
  *)
    echo "ERROR: table must be a .csv, .csv.gz, or .parquet file: $TABLE" >&2
    exit 1
    ;;
esac

if [ ! -f "$TABLE" ]; then
  echo "ERROR: CheXpert Plus table does not exist: $TABLE" >&2
  exit 1
fi
if [ ! -f "$CONFIG" ]; then
  echo "ERROR: config file does not exist: $CONFIG" >&2
  echo "Copy $TOOLKIT/configs/chexpert_plus.example.yaml to $CONFIG and map real column names first." >&2
  exit 1
fi
if [ ! -f "$TERMS" ]; then
  echo "ERROR: terms file does not exist: $TERMS" >&2
  exit 1
fi

mkdir -p "$OUTPUT"

echo "Running CheXpert Plus audit..."
echo "  table:  $TABLE"
echo "  config: $CONFIG"
echo "  terms:  $TERMS"
echo "  output: $OUTPUT"
echo

c3e-audit table \
  --table "$TABLE" \
  --config "$CONFIG" \
  --terms "$TERMS" \
  --output "$OUTPUT"

echo
echo "WARNING: $OUTPUT/study_aggregate.csv contains row-level, near-raw study data"
echo "(identifiers and context text). It is SENSITIVE and must never be uploaded,"
echo "emailed, or pasted into any external tool. Only share the aggregate files"
echo "listed in docs/DATA_SAFETY.md (e.g. via scripts/collect_safe_outputs.sh)."
