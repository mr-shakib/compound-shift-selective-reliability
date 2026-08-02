#!/usr/bin/env bash
# C3-E6 Stage 5 - MIMIC-CXR-JPG frontal image acquisition.
#
# Downloads exactly the 193,282 frontal JPGs named in the Stage 3E manifest.
# Nothing else is fetched: the manifest is the authorization boundary.
#
# Source is the PhysioNet S3 access point, not the PhysioNet HTTP endpoint.
# HTTP was measured at 0.15 MB/s against a 27 MB/s link and blocked the account
# after an hour; S3 sustains ~8 MB/s at 32 workers with no ban risk. Access is
# granted per AWS account through the PhysioNet cloud verification flow.
#
# Transfer is requester-pays only in the sense that egress bills to the caller's
# AWS account; the access point does not require the --request-payer flag.
#
# Concurrency exists to hide per-request latency and AWS CLI start-up cost,
# which dominate: each image is ~1.8 MB, small enough that a single transfer
# finishes before TCP slow-start opens the window.
#
# Credentials come from the AWS CLI configuration (~/.aws/credentials). They are
# never accepted on the command line, echoed, or written to the log.
#
# Usage:  scripts/download_mimic_images.sh [--jobs N] [--dry-run]

set -uo pipefail

ACCESS_POINT="arn:aws:s3:us-east-1:724665945834:accesspoint/mimic-cxr-jpg-v2-1-0-01"
PREFIX="mimic-cxr-jpg/2.1.0"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/data/mimic/download_manifests/ALL_frontal_jpg_paths.txt"
DEST="$ROOT/data/mimic/images"
LOG="$ROOT/logs/stage5_image_download.log"
EXPECTED_TOTAL=193282
MIN_FREE_GB=25
JOBS=64
DRY_RUN=0

export AWS_REGION="${AWS_REGION:-us-east-1}"
BASE="s3://${ACCESS_POINT}/${PREFIX}"

while [ $# -gt 0 ]; do
  case "$1" in
    --jobs) JOBS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

command -v aws >/dev/null || { echo "FATAL: aws CLI not on PATH." >&2; exit 1; }

log() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }
hms() { printf '%d:%02d:%02d' $(($1 / 3600)) $((($1 % 3600) / 60)) $(($1 % 60)); }
free_gb() { df -BG --output=avail "$DEST" | tail -1 | tr -dc '0-9'; }

# --- preconditions -----------------------------------------------------------

[ -f "$MANIFEST" ] || { echo "FATAL: missing $MANIFEST" >&2; exit 1; }

# The manifest is the authorization boundary. A changed manifest is a protocol
# amendment, not a download-time decision.
TOTAL=$(wc -l < "$MANIFEST")
[ "$TOTAL" -eq "$EXPECTED_TOTAL" ] || {
  echo "FATAL: manifest lists $TOTAL images, expected $EXPECTED_TOTAL." >&2
  echo "Investigate; do not edit the manifest to make this pass." >&2
  exit 1; }

mkdir -p "$DEST" "$(dirname "$LOG")"

log "=== C3-E6 Stage 5 - frontal image acquisition ==="
log "source : S3 access point (us-east-1)"
log "scope  : $TOTAL frontal JPGs"
log "jobs   : $JOBS concurrent"
log "free   : $(free_gb) GB"

# Fail fast and legibly rather than grinding through doomed requests.
probe=$(head -1 "$MANIFEST")
if ! aws s3 ls "$BASE/$probe" >/dev/null 2>&1; then
  log "FATAL: cannot read the access point."
  log "  Check: aws sts get-caller-identity returns the verified IAM user,"
  log "  and that AWS access was granted on the MIMIC-CXR-JPG project page."
  exit 1
fi
log "probe  : access point readable"

# --- outstanding list --------------------------------------------------------

log "building outstanding list from what is already on disk ..."
remaining=$(mktemp)
while read -r p; do
  [ -n "$p" ] || continue
  [ -s "$DEST/$p" ] || printf '%s\n' "$p"
done < "$MANIFEST" > "$remaining"

todo=$(wc -l < "$remaining")
present=$((TOTAL - todo))
log "already present: $present    to fetch: $todo"
[ "$todo" -eq 0 ] && { log "nothing to do."; rm -f "$remaining"; exit 0; }

if [ "$DRY_RUN" = "1" ]; then
  log "dry run - measuring throughput at $JOBS jobs ..."
  probe_list=$(mktemp); head -n $((JOBS * 3)) "$remaining" > "$probe_list"
  n=$(wc -l < "$probe_list")
  t0=$(date +%s)
  xargs -a "$probe_list" -P "$JOBS" -I{} sh -c \
    'o="'"$DEST"'/{}"; mkdir -p "$(dirname "$o")"; aws s3 cp --quiet "'"$BASE"'/{}" "$o" 2>/dev/null'
  t1=$(date +%s); s=$((t1 - t0)); [ "$s" -lt 1 ] && s=1
  got=0
  while read -r p; do [ -s "$DEST/$p" ] && got=$((got + 1)); done < "$probe_list"
  log "fetched $got/$n in ${s}s = $(python3 -c "print(f'{$got/$s:.1f}')") img/s"
  log "projected for $todo remaining: $(python3 -c "print(f'{$todo/max($got/$s,0.01)/3600:.1f}')") h"
  rm -f "$probe_list" "$remaining"
  exit 0
fi

# --- transfer ----------------------------------------------------------------

started=$(date +%s)
CHUNK=$((JOBS * 25))
chunk_file=$(mktemp)
fetched=0
bytes=0
consecutive_empty=0

while true; do
  head -n "$CHUNK" "$remaining" > "$chunk_file"
  n=$(wc -l < "$chunk_file")
  [ "$n" -eq 0 ] && break

  if [ "$(free_gb)" -lt "$MIN_FREE_GB" ]; then
    log "ABORT: free space below ${MIN_FREE_GB} GB. Downloaded data is intact; rerun to resume."
    rm -f "$remaining" "$chunk_file"; exit 1
  fi

  xargs -a "$chunk_file" -P "$JOBS" -I{} sh -c \
    'o="'"$DEST"'/{}"; [ -s "$o" ] && exit 0
     mkdir -p "$(dirname "$o")"
     aws s3 cp --quiet "'"$BASE"'/{}" "$o" 2>/dev/null || rm -f "$o"'

  got=0
  while read -r p; do
    if [ -s "$DEST/$p" ]; then
      got=$((got + 1)); bytes=$((bytes + $(stat -c %s "$DEST/$p")))
    fi
  done < "$chunk_file"

  if [ "$got" -eq 0 ]; then
    consecutive_empty=$((consecutive_empty + 1))
    log "warning: chunk of $n produced nothing (strike $consecutive_empty/3)"
    [ "$consecutive_empty" -ge 3 ] && {
      log "ABORT: three empty chunks. Check credentials and project access."
      log "       Progress is saved; rerun to resume."
      rm -f "$remaining" "$chunk_file"; exit 1; }
    continue
  fi
  consecutive_empty=0

  fetched=$((fetched + got))
  elapsed=$(($(date +%s) - started)); [ "$elapsed" -lt 1 ] && elapsed=1
  printf '  %d/%d (%d%%)  %s GB  %s img/s  %s MB/s  elapsed %s  eta %s\n' \
    "$fetched" "$todo" "$((100 * fetched / todo))" \
    "$(python3 -c "print(f'{$bytes/1073741824:.1f}')")" \
    "$(python3 -c "print(f'{$fetched/$elapsed:.1f}')")" \
    "$(python3 -c "print(f'{$bytes/$elapsed/1048576:.1f}')")" \
    "$(hms $elapsed)" \
    "$(hms "$(python3 -c "print(int(($todo-$fetched)/max($fetched/$elapsed,0.01)))")")" \
    | tee -a "$LOG"

  sed -i "1,${n}d" "$remaining"
done

rm -f "$remaining" "$chunk_file"
elapsed=$(($(date +%s) - started))
log "=== done: $fetched images, $(python3 -c "print(f'{$bytes/1073741824:.1f}')") GB, $(hms $elapsed) ==="
log "images are in data/mimic/images (gitignored). No image content was decoded."
