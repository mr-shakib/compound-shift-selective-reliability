#!/usr/bin/env bash
# C3-E6 Stage 5 - MIMIC-CXR-JPG frontal image acquisition.
#
# Downloads exactly the 193,282 frontal JPGs named in the Stage 3E manifests.
# Nothing else is fetched: the manifests are the authorization boundary.
#
# Why this fetches in parallel. PhysioNet is a single origin host with no CDN,
# measured at 331 ms round trip. Each image is ~1.8 MB, which is small enough
# that a transfer completes before TCP slow-start has opened the window, so a
# sequential fetch spends most of its time waiting rather than moving data. The
# measured sequential rate was 0.15 MB/s against a 27 MB/s link. Concurrency
# overlaps that latency; it does not increase per-connection speed.
#
# Concurrency is deliberately capped. Saturating a fast link from this origin
# would need ~180 streams, which is abusive against shared academic
# infrastructure and will earn a ban. The default of 8 is ordinary client
# behaviour. Do not raise --jobs above 16.
#
# Credentials come from ~/.netrc (mode 600). They are never accepted on the
# command line, echoed, or written to the log.
#
# Usage:  scripts/download_mimic_images.sh [--jobs N] [--dry-run]

set -uo pipefail

BASE_URL="https://physionet.org/files/mimic-cxr-jpg/2.1.0/"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/data/mimic/download_manifests/ALL_frontal_jpg_paths.txt"
DEST="$ROOT/data/mimic/images"
LOG="$ROOT/logs/stage5_image_download.log"
EXPECTED_TOTAL=193282
MIN_FREE_GB=25
JOBS=8
MAX_JOBS=16
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --jobs) JOBS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if ! [ "$JOBS" -ge 1 ] 2>/dev/null || [ "$JOBS" -gt "$MAX_JOBS" ]; then
  echo "FATAL: --jobs must be between 1 and $MAX_JOBS." >&2
  echo "Higher concurrency against PhysioNet is abusive and will get you banned." >&2
  exit 2
fi

log() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }
hms() { printf '%d:%02d:%02d' $(($1 / 3600)) $((($1 % 3600) / 60)) $(($1 % 60)); }
free_gb() { df -BG --output=avail "$DEST" | tail -1 | tr -dc '0-9'; }

# --- preconditions -----------------------------------------------------------

[ -f "$HOME/.netrc" ] || {
  echo "FATAL: ~/.netrc not found. PhysioNet requires credentialed access." >&2
  echo "  printf 'machine physionet.org login USER password PASS\\n' > ~/.netrc" >&2
  echo "  chmod 600 ~/.netrc" >&2
  exit 1; }

[ "$(stat -c %a "$HOME/.netrc")" = "600" ] || {
  echo "FATAL: ~/.netrc must be mode 600." >&2; exit 1; }

grep -q 'physionet\.org' "$HOME/.netrc" || {
  echo "FATAL: ~/.netrc has no physionet.org entry." >&2; exit 1; }

[ -f "$MANIFEST" ] || { echo "FATAL: missing $MANIFEST" >&2; exit 1; }

# The manifest is the authorization boundary. A changed manifest is a protocol
# amendment, not a download-time decision.
TOTAL=$(wc -l < "$MANIFEST")
[ "$TOTAL" -eq "$EXPECTED_TOTAL" ] || {
  echo "FATAL: manifest lists $TOTAL images, expected $EXPECTED_TOTAL." >&2
  echo "Investigate before running; do not edit the manifest to make this pass." >&2
  exit 1; }

mkdir -p "$DEST" "$(dirname "$LOG")"

log "=== C3-E6 Stage 5 - frontal image acquisition ==="
log "source : $BASE_URL"
log "scope  : $TOTAL frontal JPGs"
log "jobs   : $JOBS concurrent"
log "free   : $(free_gb) GB"

# --- reachability probe ------------------------------------------------------
# Fail fast and clearly if the account is throttled or blocked, rather than
# grinding through thousands of doomed requests.
probe=$(head -1 "$MANIFEST")
code=$(curl -sS --netrc -o /dev/null -w '%{http_code}' --max-time 30 "${BASE_URL}${probe}" 2>/dev/null)
case "$code" in
  200) log "probe  : HTTP 200, access confirmed" ;;
  403) log "FATAL: HTTP 403. The account or IP is blocked, usually from bulk"
       log "       downloading. Wait at least 24h before retrying. Do not"
       log "       hammer it; repeated attempts extend the block."
       exit 1 ;;
  401) log "FATAL: HTTP 401. Credentials rejected - check ~/.netrc."; exit 1 ;;
  *)   log "FATAL: probe returned HTTP $code."; exit 1 ;;
esac

if [ "$DRY_RUN" = "1" ]; then
  log "dry run - measuring throughput at $JOBS jobs over 60s ..."
  before=$(find "$DEST" -name '*.jpg' -type f | wc -l)
  t0=$(date +%s)
  grep -vxF -f <(cd "$DEST" && find . -name '*.jpg' | sed 's|^\./||') "$MANIFEST" 2>/dev/null \
    | head -300 \
    | timeout 60 xargs -P "$JOBS" -I{} sh -c \
        'mkdir -p "'"$DEST"'/$(dirname {})" && curl -sS --netrc --fail --max-time 120 \
         -o "'"$DEST"'/{}" "'"$BASE_URL"'{}" 2>/dev/null' || true
  t1=$(date +%s)
  after=$(find "$DEST" -name '*.jpg' -type f | wc -l)
  got=$((after - before)); secs=$((t1 - t0))
  if [ "$got" -gt 0 ]; then
    log "fetched $got files in ${secs}s = $(python3 -c "print(f'{$got/$secs:.2f}')") img/s"
    log "projected for $TOTAL images: $(python3 -c "print(f'{($TOTAL-$after)/($got/$secs)/3600:.1f}')") h"
  else
    log "fetched nothing - throttled or blocked"
  fi
  exit 0
fi

# --- download ----------------------------------------------------------------

started=$(date +%s)
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

CHUNK=$((JOBS * 50))
chunk_file=$(mktemp)
fetched=0
consecutive_empty=0

while true; do
  head -n "$CHUNK" "$remaining" > "$chunk_file"
  n=$(wc -l < "$chunk_file")
  [ "$n" -eq 0 ] && break

  if [ "$(free_gb)" -lt "$MIN_FREE_GB" ]; then
    log "ABORT: free space below ${MIN_FREE_GB} GB. What is downloaded is intact; rerun to resume."
    rm -f "$remaining" "$chunk_file"; exit 1
  fi

  xargs -a "$chunk_file" -P "$JOBS" -I{} sh -c \
    'out="'"$DEST"'/{}"; [ -s "$out" ] && exit 0
     mkdir -p "$(dirname "$out")"
     curl -sS --netrc --fail --max-time 180 --retry 2 --retry-delay 5 \
          -o "$out" "'"$BASE_URL"'{}" 2>/dev/null || rm -f "$out"'

  got=0; bytes=0
  while read -r p; do
    if [ -s "$DEST/$p" ]; then
      got=$((got + 1)); bytes=$((bytes + $(stat -c %s "$DEST/$p")))
    fi
  done < "$chunk_file"

  if [ "$got" -eq 0 ]; then
    consecutive_empty=$((consecutive_empty + 1))
    log "warning: chunk of $n produced nothing (strike $consecutive_empty/3)"
    if [ "$consecutive_empty" -ge 3 ]; then
      log "ABORT: three empty chunks. Almost certainly throttled or blocked."
      log "       Wait 24h before retrying. Progress is saved; rerun to resume."
      rm -f "$remaining" "$chunk_file"; exit 1
    fi
    continue
  fi
  consecutive_empty=0

  fetched=$((fetched + got))
  elapsed=$(($(date +%s) - started))
  rate=$(python3 -c "print(f'{$fetched/max($elapsed,1):.2f}')")
  eta=$(python3 -c "r=$fetched/max($elapsed,1); print(int(($todo-$fetched)/r) if r>0 else 0)")
  printf '  %d/%d (%d%%)  %.1f GB  %s img/s  elapsed %s  eta %s\n' \
    "$fetched" "$todo" "$((100 * fetched / todo))" \
    "$(python3 -c "print($bytes/1073741824)")" "$rate" "$(hms $elapsed)" "$(hms $eta)" \
    | tee -a "$LOG"

  sed -i "1,${n}d" "$remaining"
done

rm -f "$remaining" "$chunk_file"
elapsed=$(($(date +%s) - started))
log "=== done: $fetched images in $(hms $elapsed) ==="
log "images are in data/mimic/images (gitignored). No image content was decoded."
