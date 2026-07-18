#!/usr/bin/env bash
# Verify the local C3-E pre-access workspace is ready to run the audit toolkit.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLKIT="$WORKSPACE/c3e_audit_toolkit"
VENV="$TOOLKIT/.venv"

PASS=1
note() { printf '  [ok]   %s\n' "$1"; }
warn() { printf '  [warn] %s\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1"; PASS=0; }

echo "C3-E environment check"
echo "Workspace: $WORKSPACE"
echo

# --- Python version ---------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PY_VERSION="$(python3 --version 2>&1)"
  note "python3 available: $PY_VERSION"
else
  fail "python3 not found on PATH"
fi

# --- Disk space --------------------------------------------------------------
AVAIL_KB="$(df -Pk "$WORKSPACE" | awk 'NR==2 {print $4}')"
if [ -n "${AVAIL_KB:-}" ]; then
  AVAIL_GB=$((AVAIL_KB / 1024 / 1024))
  note "available disk space on workspace volume: ${AVAIL_GB} GB"
  if [ "$AVAIL_GB" -lt 5 ]; then
    warn "less than 5 GB free — may be tight once real audit outputs are generated"
  fi
else
  warn "could not determine available disk space"
fi

# --- Toolkit presence ----------------------------------------------------
if [ -d "$TOOLKIT" ] && [ -f "$TOOLKIT/pyproject.toml" ]; then
  note "toolkit found at $TOOLKIT"
else
  fail "toolkit not found at $TOOLKIT (expected pyproject.toml)"
fi

# --- Virtual environment -----------------------------------------------
if [ -x "$VENV/bin/python" ]; then
  note "virtual environment found at $VENV"
else
  fail "virtual environment not found at $VENV (expected $VENV/bin/python)"
fi

# --- c3e-audit installed -------------------------------------------------
if [ -x "$VENV/bin/c3e-audit" ]; then
  note "c3e-audit console script installed"
else
  fail "c3e-audit console script not found in venv"
fi

# --- Tests -----------------------------------------------------------------
if [ -x "$VENV/bin/pytest" ] && [ -d "$TOOLKIT/tests" ]; then
  echo
  echo "Running toolkit test suite..."
  if (cd "$TOOLKIT" && "$VENV/bin/pytest" -q); then
    note "pytest passed"
  else
    fail "pytest failed"
  fi
  echo
else
  warn "pytest or tests directory not available; skipping test run"
fi

# --- Expected data directories ------------------------------------------
for d in "data/mimic" "data/chexpert_plus" "results/c3e_mimic" "results/c3e_chexpert_plus" "results/c3e_cross_site" "docs" "logs" "scripts"; do
  if [ -d "$WORKSPACE/$d" ]; then
    note "directory present: $d"
  else
    fail "missing expected directory: $d"
  fi
done

echo
if [ "$PASS" -eq 1 ]; then
  echo "READINESS SUMMARY: environment looks ready for report-only, metadata-only audits."
  echo "No credentialed data has been checked for presence — this script does not verify PHI."
else
  echo "READINESS SUMMARY: one or more checks FAILED. Resolve the [FAIL] items above before running an audit."
  exit 1
fi
