#!/usr/bin/env bash
# Collect only the approved, aggregate-only audit outputs into a single
# shareable directory. study_aggregate.csv and any other row-level file is
# explicitly excluded. Fails loudly if an expected safe output is missing
# for a site whose results directory already exists (i.e. an audit ran).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS="$WORKSPACE/results"
DEST="$RESULTS/shareable_aggregates"

# Approved per-site aggregate outputs (see docs/DATA_SAFETY.md).
AUDIT_SITES=("c3e_mimic" "c3e_chexpert_plus")
AUDIT_FILES=("summary.json" "section_availability.csv" "label_prevalence.csv" "leakage_by_label.csv" "missingness_by_label.csv" "gate_report.json")

COMPARE_SITE="c3e_cross_site"
COMPARE_FILES=("cross_site_comparison.csv" "cross_site_gate.json")

UNSAFE_FILE="study_aggregate.csv"

mkdir -p "$DEST"

COPIED=()
ANY_SOURCE_RAN=0

for site in "${AUDIT_SITES[@]}"; do
  site_dir="$RESULTS/$site"
  # The results/<site> directories are pre-created as empty scaffolding by
  # the workspace setup, so an empty directory does not mean an audit ran.
  # Use the presence of summary.json (always written by write_outputs) as
  # the signal that this site's audit has actually been executed.
  if [ ! -f "$site_dir/summary.json" ]; then
    echo "SKIP: $site_dir/summary.json not found (audit has not been run for this site yet)."
    continue
  fi
  ANY_SOURCE_RAN=1
  for f in "${AUDIT_FILES[@]}"; do
    src="$site_dir/$f"
    if [ ! -f "$src" ]; then
      echo "ERROR: expected safe output missing: $src" >&2
      exit 1
    fi
    dest_name="${site}__${f}"
    cp "$src" "$DEST/$dest_name"
    COPIED+=("$dest_name")
  done
  if [ -f "$site_dir/$UNSAFE_FILE" ]; then
    echo "NOTE: $site_dir/$UNSAFE_FILE exists and was intentionally NOT copied (unsafe to share)."
  fi
done

compare_dir="$RESULTS/$COMPARE_SITE"
if [ -f "$compare_dir/${COMPARE_FILES[0]}" ]; then
  ANY_SOURCE_RAN=1
  for f in "${COMPARE_FILES[@]}"; do
    src="$compare_dir/$f"
    if [ ! -f "$src" ]; then
      echo "ERROR: expected safe output missing: $src" >&2
      exit 1
    fi
    dest_name="${COMPARE_SITE}__${f}"
    cp "$src" "$DEST/$dest_name"
    COPIED+=("$dest_name")
  done
else
  echo "SKIP: $compare_dir/${COMPARE_FILES[0]} not found (cross-site comparison has not been run yet)."
fi

if [ "$ANY_SOURCE_RAN" -eq 0 ]; then
  echo
  echo "No audit results exist yet under $RESULTS — nothing to collect."
  echo "This is expected in the pre-access phase. Re-run this script after an audit completes."
  exit 0
fi

echo
if [ "${#COPIED[@]}" -eq 0 ]; then
  echo "No safe outputs were copied."
  exit 0
fi

echo "Files safe to share (copied to $DEST):"
for f in "${COPIED[@]}"; do
  echo "  - $f"
done
echo
echo "$UNSAFE_FILE was NEVER copied. Do not manually copy it. See docs/DATA_SAFETY.md."
