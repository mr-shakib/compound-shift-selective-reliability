#!/usr/bin/env bash
# Run the C3-E report-only, metadata-only audit against a local, authorized
# MIMIC-CXR download. Never contains credentials. All paths must point to
# files you already have local, authorized access to.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLKIT="$WORKSPACE/c3e_audit_toolkit"
VENV="$TOOLKIT/.venv"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Inputs may be supplied as flags or environment variables. Example filenames
below (mimic-cxr-reports.zip, mimic-cxr-2.0.0-chexpert.csv.gz, etc.) are
defaults only — pass your real local paths.

  --reports PATH    Extracted report directory or reports ZIP archive
                     (env: MIMIC_REPORTS, default: data/mimic/mimic-cxr-reports.zip)
  --labels PATH     mimic-cxr-2.0.0-chexpert.csv.gz (env: MIMIC_LABELS)
  --metadata PATH   mimic-cxr-2.0.0-metadata.csv.gz (env: MIMIC_METADATA)
  --splits PATH     mimic-cxr-2.0.0-split.csv.gz (env: MIMIC_SPLITS)
  --config PATH     audit config YAML (env: MIMIC_CONFIG, default: toolkit configs/mimic.yaml)
  --terms PATH      target-term YAML (env: MIMIC_TERMS, default: toolkit configs/terms.yaml)
  --output PATH     output directory (env: MIMIC_OUTPUT, default: results/c3e_mimic)
  -h, --help        show this help text
EOF
}

REPORTS="${MIMIC_REPORTS:-$WORKSPACE/data/mimic/mimic-cxr-reports.zip}"
LABELS="${MIMIC_LABELS:-$WORKSPACE/data/mimic/mimic-cxr-2.0.0-chexpert.csv.gz}"
METADATA="${MIMIC_METADATA:-$WORKSPACE/data/mimic/mimic-cxr-2.0.0-metadata.csv.gz}"
SPLITS="${MIMIC_SPLITS:-$WORKSPACE/data/mimic/mimic-cxr-2.0.0-split.csv.gz}"
CONFIG="${MIMIC_CONFIG:-$TOOLKIT/configs/mimic.yaml}"
TERMS="${MIMIC_TERMS:-$TOOLKIT/configs/terms.yaml}"
OUTPUT="${MIMIC_OUTPUT:-$WORKSPACE/results/c3e_mimic}"

while [ $# -gt 0 ]; do
  case "$1" in
    --reports) REPORTS="$2"; shift 2 ;;
    --labels) LABELS="$2"; shift 2 ;;
    --metadata) METADATA="$2"; shift 2 ;;
    --splits) SPLITS="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    --terms) TERMS="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [ ! -x "$VENV/bin/activate" ] && [ ! -f "$VENV/bin/activate" ]; then
  echo "ERROR: virtual environment not found at $VENV. Run the toolkit setup first." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$VENV/bin/activate"

if ! command -v c3e-audit >/dev/null 2>&1; then
  echo "ERROR: c3e-audit is not installed in the active virtual environment." >&2
  exit 1
fi

# --- Validate every input file/path exists before running anything ---------
if [ ! -e "$REPORTS" ]; then
  echo "ERROR: reports path does not exist: $REPORTS" >&2
  echo "Expected an extracted report directory or a ZIP archive (e.g. mimic-cxr-reports.zip)." >&2
  exit 1
fi
if [ -f "$REPORTS" ] && [[ "$REPORTS" != *.zip ]]; then
  echo "ERROR: reports path is a file but not a .zip archive: $REPORTS" >&2
  exit 1
fi
for pair in "labels:$LABELS" "metadata:$METADATA" "splits:$SPLITS" "config:$CONFIG" "terms:$TERMS"; do
  name="${pair%%:*}"
  path="${pair#*:}"
  if [ ! -f "$path" ]; then
    echo "ERROR: $name file does not exist: $path" >&2
    exit 1
  fi
done

mkdir -p "$OUTPUT"

echo "Running MIMIC-CXR audit..."
echo "  reports:  $REPORTS"
echo "  labels:   $LABELS"
echo "  metadata: $METADATA"
echo "  splits:   $SPLITS"
echo "  config:   $CONFIG"
echo "  terms:    $TERMS"
echo "  output:   $OUTPUT"
echo

c3e-audit mimic \
  --reports "$REPORTS" \
  --labels "$LABELS" \
  --metadata "$METADATA" \
  --splits "$SPLITS" \
  --config "$CONFIG" \
  --terms "$TERMS" \
  --output "$OUTPUT"

echo
echo "WARNING: $OUTPUT/study_aggregate.csv contains row-level, near-raw study data"
echo "(identifiers and context text). It is SENSITIVE and must never be uploaded,"
echo "emailed, or pasted into any external tool. Only share the aggregate files"
echo "listed in docs/DATA_SAFETY.md (e.g. via scripts/collect_safe_outputs.sh)."
