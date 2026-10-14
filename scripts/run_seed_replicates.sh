#!/usr/bin/env bash
# Additional training-seed replicates (POST HOC; added 2026-10-14).
#
# Three more seeds (20260720, 20260721, 20260722), so the transfer gap is
# reported over five training runs instead of two. For each seed, in order:
#   1. train M1, M2 and M4 on the model-train tier only, with the frozen v0.4.2
#      settings and early stopping on the same internal validation split;
#   2. score all four models (M3 is the M1/M2 probability average) on the
#      calibration tier (C0), the source evaluation tier and the external site
#      (C0, C1, C2; C2 with the frozen donor seed 20260718).
# Thresholds and cutoffs are re-selected afterwards on the calibration tier by
# the frozen Stage 7 rule (c3e.revision.seeds); nothing is fitted on external
# data.
#
# Estimated wall time on the GTX 1660 SUPER: about 22-26 h per seed (M1 ~2.5 h,
# M2 ~6 h, M4 ~7-12 h at ~103 min/epoch, scoring ~5 h), so about 3 days for
# all three. Each seed finishes completely before the next starts, so a
# finished seed is usable even if the queue is stopped. Every step is cached
# and resumable: rerun the same command after an interruption and finished
# work is skipped; training resumes from its last completed epoch.
#
# Usage:  bash scripts/run_seed_replicates.sh 2>&1 | tee -a logs/seed_replicates.log
# Subset: SEEDS="20260720" bash scripts/run_seed_replicates.sh ...
set -euo pipefail
cd "$(dirname "$0")/.."
PY=c3e_audit_toolkit/.venv/bin/python
INF="$PY -m c3e.revision.inference"
CK=data/models/c3e
SEEDS="${SEEDS:-20260720 20260721 20260722}"
stamp() { echo "[$(date -Is)] $*"; }

for s in $SEEDS; do
  for m in M1 M2 M4; do
    lc=$(echo "$m" | tr 'A-Z' 'a-z')
    # Train when there is no checkpoint, or resume an interrupted run. A
    # finished model is never retrained.
    if [ ! -f "$CK/${lc}_best_seed$s.pt" ] || [ -f "$CK/${lc}_seed${s}_resume.pt" ]; then
      stamp "seed $s: train $m"
      $PY -m c3e.training.runner --models "$m" --seed "$s"
    else
      stamp "seed $s: $m already trained"
    fi
  done
  stamp "seed $s: calibration tier"
  $INF --site source --tier threshold_calibration --models M1,M2,M3,M4 --conditions C0 --train-seed "$s"
  stamp "seed $s: source evaluation tier"
  $INF --site source --tier prespecified_eval --models M1,M2,M3,M4 --conditions C0,C1,C2 --train-seed "$s"
  stamp "seed $s: external site"
  $INF --site external --tier external --models M1,M2,M3,M4 --conditions C0,C1,C2 --train-seed "$s"
  stamp "seed $s: complete"
done
stamp "seed replicates complete"
