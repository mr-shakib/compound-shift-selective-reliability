#!/usr/bin/env bash
# C3-E6 Stage 5 - MIMIC-CXR-JPG frontal image acquisition.
#
# Downloads exactly the 193,282 frontal JPGs named in the Stage 3E manifests.
# Nothing else is fetched: the manifests are the authorization boundary.
#
# Confirmatory tiers download first so that evaluation-critical data is on disk
# long before the training bulk finishes. The script is resumable - rerunning it
# skips files already present and continues where it stopped.
#
# Credentials come from ~/.netrc (mode 600). They are never accepted on the
# command line, never echoed, and never written to the log.
#
# Usage:  scripts/download_mimic_images.sh [--dry-run]

set -uo pipefail

BASE_URL="https://physionet.org/files/mimic-cxr-jpg/2.1.0/"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST_DIR="$ROOT/data/mimic/download_manifests"
DEST="$ROOT/data/mimic/images"
LOG="$ROOT/logs/stage5_image_download.log"
CHUNK=500
MIN_FREE_GB=25

# Confirmatory tiers first; the 162k-image training bulk last.
TIERS=(
  prespecified_eval_frontal_jpg_paths.txt
  threshold_calibration_frontal_jpg_paths.txt
  official_validate_frontal_jpg_paths.txt
  official_test_frontal_jpg_paths.txt
  model_train_frontal_jpg_paths.txt
)

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }
hms() { printf '%d:%02d:%02d' $(($1 / 3600)) $((($1 % 3600) / 60)) $(($1 % 60)); }

free_gb() { df -BG --output=avail "$DEST" | tail -1 | tr -dc '0-9'; }

# --- preconditions -----------------------------------------------------------

if [ ! -f "$HOME/.netrc" ]; then
  echo "FATAL: ~/.netrc not found. PhysioNet requires credentialed access." >&2
  echo "Create it with:" >&2
  echo "  printf 'machine physionet.org login YOUR_USER password YOUR_PASS\\n' > ~/.netrc" >&2
  echo "  chmod 600 ~/.netrc" >&2
  exit 1
fi

perms=$(stat -c %a "$HOME/.netrc")
if [ "$perms" != "600" ]; then
  echo "FATAL: ~/.netrc has mode $perms; must be 600." >&2
  exit 1
fi

if ! grep -q 'physionet\.org' "$HOME/.netrc"; then
  echo "FATAL: ~/.netrc has no entry for physionet.org." >&2
  exit 1
fi

mkdir -p "$DEST" "$(dirname "$LOG")"

for t in "${TIERS[@]}"; do
  [ -f "$MANIFEST_DIR/$t" ] || { echo "FATAL: missing manifest $t" >&2; exit 1; }
done

# Authorization boundary: refuse to run if the manifests do not total the
# preregistered image count. A changed manifest is a protocol amendment, not a
# download-time decision.
TOTAL=$(cat "${TIERS[@]/#/$MANIFEST_DIR/}" | wc -l)
if [ "$TOTAL" -ne 193282 ]; then
  echo "FATAL: manifests total $TOTAL images, expected 193282." >&2
  echo "The manifests are the authorization boundary; investigate before running." >&2
  exit 1
fi

log "=== C3-E6 Stage 5 - frontal image acquisition ==="
log "source : $BASE_URL"
log "dest   : data/mimic/images (gitignored)"
log "scope  : $TOTAL frontal JPGs across ${#TIERS[@]} tiers"
log "free   : $(free_gb) GB"

if [ "$DRY_RUN" = "1" ]; then
  log "dry run - measuring true size from a 40-file sample ..."
  sample=$(head -40 "$MANIFEST_DIR/${TIERS[0]}")
  bytes=0
  while read -r p; do
    [ -n "$p" ] || continue
    sz=$(wget --netrc --spider --server-response "${BASE_URL}${p}" 2>&1 \
         | awk '/[Cc]ontent-[Ll]ength:/ {print $2}' | tail -1 | tr -dc '0-9')
    [ -n "$sz" ] && bytes=$((bytes + sz))
  done <<< "$sample"
  n=$(wc -l <<< "$sample")
  if [ "$bytes" -gt 0 ]; then
    avg=$((bytes / n))
    log "sampled $n files, mean $((avg / 1024)) KB"
    log "PROJECTED TOTAL: $((avg * TOTAL / 1073741824)) GB for $TOTAL images"
    log "free now: $(free_gb) GB"
  else
    log "could not read Content-Length - check credentials"
    exit 1
  fi
  exit 0
fi

# --- download ----------------------------------------------------------------

started=$(date +%s)
done_files=0
done_bytes=0
grand_skipped=0

for tier in "${TIERS[@]}"; do
  name="${tier%_frontal_jpg_paths.txt}"
  manifest="$MANIFEST_DIR/$tier"
  tier_total=$(wc -l < "$manifest")

  # Build the remaining list: anything not already on disk with nonzero size.
  remaining=$(mktemp)
  while read -r p; do
    [ -n "$p" ] || continue
    [ -s "$DEST/$p" ] || printf '%s\n' "$p"
  done < "$manifest" > "$remaining"
  todo=$(wc -l < "$remaining")
  skipped=$((tier_total - todo))
  grand_skipped=$((grand_skipped + skipped))

  log ""
  log "--- tier '$name': $tier_total images, $skipped already present, $todo to fetch"
  if [ "$todo" -eq 0 ]; then
    rm -f "$remaining"
    continue
  fi

  chunk_file=$(mktemp)
  fetched=0
  while true; do
    head -n "$CHUNK" "$remaining" > "$chunk_file"
    n=$(wc -l < "$chunk_file")
    [ "$n" -eq 0 ] && break

    if [ "$(free_gb)" -lt "$MIN_FREE_GB" ]; then
      log "ABORT: free space below ${MIN_FREE_GB} GB. Downloaded so far is intact; rerun to resume."
      rm -f "$remaining" "$chunk_file"
      exit 1
    fi

    wget --netrc -q -c -x -nH --cut-dirs=3 -P "$DEST" \
         --tries=3 --timeout=30 --waitretry=5 \
         -B "$BASE_URL" -i "$chunk_file"
    rc=$?
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 8 ]; then
      log "ABORT: wget exited $rc (1=generic 4=network 5=ssl 6=auth). Rerun to resume."
      rm -f "$remaining" "$chunk_file"
      exit "$rc"
    fi

    # Account only for what actually landed.
    got=0; bytes=0
    while read -r p; do
      if [ -s "$DEST/$p" ]; then
        got=$((got + 1))
        bytes=$((bytes + $(stat -c %s "$DEST/$p")))
      fi
    done < "$chunk_file"
    fetched=$((fetched + got))
    done_files=$((done_files + got))
    done_bytes=$((done_bytes + bytes))

    if [ "$got" -eq 0 ]; then
      log "ABORT: a full chunk of $n files produced nothing. Check credentials and access approval."
      rm -f "$remaining" "$chunk_file"
      exit 1
    fi

    elapsed=$(($(date +%s) - started))
    rate=$((elapsed > 0 ? done_files / elapsed : 0))
    outstanding=$((TOTAL - grand_skipped - done_files))
    eta=$((rate > 0 ? outstanding / rate : 0))
    printf '  %s: %d/%d  |  total %d/%d (%d%%)  %d GB  %d img/s  elapsed %s  eta %s\n' \
      "$name" "$fetched" "$todo" \
      "$done_files" "$((TOTAL - grand_skipped))" \
      "$((outstanding >= 0 ? 100 * done_files / (TOTAL - grand_skipped + 1) : 100))" \
      "$((done_bytes / 1073741824))" "$rate" "$(hms $elapsed)" "$(hms $eta)" \
      | tee -a "$LOG"

    sed -i "1,${n}d" "$remaining"
  done

  rm -f "$chunk_file" "$remaining"
  log "tier '$name' complete: $fetched fetched"
done

elapsed=$(($(date +%s) - started))
log ""
log "=== done: $done_files images, $((done_bytes / 1073741824)) GB, $(hms $elapsed) ==="
log "images are in data/mimic/images (gitignored). No image content was decoded."
