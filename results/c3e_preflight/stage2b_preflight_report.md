# C3-E6 Stage 2B Synthetic Preflight Report

Status: **PASS**

- **SYNTHETIC DATA ONLY**
- **NO MEDICAL IMAGES LOADED**
- **NO MODEL TRAINING PERFORMED**
- **EXTERNAL TUNING DISABLED**

## Protocol and cohort

- Protocol: `C3E6-STAGE2` version `0.1.0`
- Deterministic seed: `20260718`
- Synthetic patients: 32
- Synthetic studies: 64
- Synthetic images: 128

## Context interventions

- C0: 32 studies / 64 images
- C1: 32 studies / 64 images
- C2: 32 studies / 64 images

## Frozen source-only thresholds

```json
{
  "classification_thresholds": {
    "Cardiomegaly": 0.635,
    "Edema": 0.64,
    "Pleural Effusion": 0.6475,
    "Atelectasis": 0.87,
    "Consolidation": 0.6599999999999999
  },
  "abstention_thresholds": {
    "0.80": 0.20000000000000018,
    "0.90": 0.050000000000000044,
    "0.70": 0.20000000000000018
  },
  "fit_site_id": "SYNTH_SOURCE",
  "fit_split_id": "calibration",
  "criterion": "balanced_accuracy",
  "confidence_definition": "minimum_abs_2p_minus_1",
  "frozen": true
}
```

## Execution status

- Metrics executed: 15
- Positive checks passed: 12
- Deliberate negative cases rejected: 20
- protocol tests: PASS (3 passed)
- audit toolkit and Stage 2B tests: PASS (81 passed)
- Stage 2B tests: PASS (42 passed)

## Failed checks

- None

## Unresolved pending fields

- exact MIMIC pre-diagnostic section mapping
- exact image backbone
- exact text backbone
- actual dataset counts
- real-data batch-size feasibility
- three-seed ensemble feasibility
- verified AUGRC implementation

## Exact commands

```bash
cd protocols/C3E6_stage2 && sha256sum -c MANIFEST.sha256 && cd ../..
c3e_audit_toolkit/.venv/bin/python protocols/C3E6_stage2/scripts/validate_protocol.py
c3e_audit_toolkit/.venv/bin/python -m unittest discover -s protocols/C3E6_stage2/tests -v
cd c3e_audit_toolkit && .venv/bin/python -m pytest tests -q && cd ..
cd c3e_audit_toolkit && .venv/bin/python -m pytest tests/preflight -q && cd ..
scripts/run_stage2b_preflight.sh
```
