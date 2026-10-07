#!/usr/bin/env bash
# Revision R1 (2026-10-06) GPU queue. All steps are POST HOC and exploratory.
#
# Runs sequentially on the single 6 GB GPU; every step is cached and resumable
# (a rerun skips finished caches; training resumes from its last epoch).
#
#   1. Calibration-tier scores (C0) for the primary models and the existing
#      seed-20260719 replicate -- verifies Stage 7 reproduces; feeds the
#      exploratory selective-score comparators fitted on the source only.
#   2. Two additional C2 donor permutations at the source (M2, M3, M4).
#   3. M2 retrained under seed 20260719 (model-train tier only; frozen v0.4.2
#      settings; early stopping on the same internal validation split).
#   4. M2 and M3 under seed 20260719: calibration tier, source eval, external.
#   5. One additional C2 donor permutation at the external site (M2, M3, M4).
#
# Estimated wall time on the GTX 1660 SUPER: ~10 h (step 3 ~6 h).
# Usage:  bash scripts/run_revision_gpu_queue.sh  2>&1 | tee logs/revision_gpu_queue.log
set -euo pipefail
cd "$(dirname "$0")/.."
PY=c3e_audit_toolkit/.venv/bin/python
INF="$PY -m c3e.revision.inference"
stamp() { echo "[$(date -Is)] $*"; }

stamp "step 1: calibration-tier scores"
$INF --site source --tier threshold_calibration --models M1,M2,M3,M4 --conditions C0
$INF --site source --tier threshold_calibration --models M1,M4 --conditions C0 --train-seed 20260719

stamp "step 2: additional source C2 permutations"
for s in 20260719 20260720; do
  $INF --site source --tier prespecified_eval --models M2,M3,M4 --conditions C2 --c2-seed "$s"
done

stamp "step 3: M2 replicate training (seed 20260719)"
if [ ! -f data/models/c3e/m2_best_seed20260719.pt ] || [ -f data/models/c3e/m2_seed20260719_resume.pt ]; then
  $PY -m c3e.training.runner --models M2 --seed 20260719
fi

stamp "step 4: M2/M3 replicate scoring"
$INF --site source --tier threshold_calibration --models M2,M3 --conditions C0 --train-seed 20260719
$INF --site source --tier prespecified_eval --models M2,M3 --conditions C0,C1,C2 --train-seed 20260719
$INF --site external --tier external --models M2,M3 --conditions C0,C1,C2 --train-seed 20260719

stamp "step 5: additional external C2 permutation"
$INF --site external --tier external --models M2,M3,M4 --conditions C2 --c2-seed 20260719

stamp "queue complete"
