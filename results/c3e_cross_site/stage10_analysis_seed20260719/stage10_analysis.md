# C3-E6 Stage 10 — Confirmatory Analysis

Status: **PASS**

- **STAGE 10 ONLY**
- **CONFIRMATORY ANALYSIS**
- **CONTRASTS AND DECISION RULE PRESPECIFIED BEFORE THESE NUMBERS EXISTED**
- **THRESHOLDS CONSUMED FROZEN FROM STAGE 7**
- **NO MODEL TRAINING**
- **NO THRESHOLD SELECTION OR REVISION**
- **PATIENT-CLUSTERED BOOTSTRAP, 2000 REPLICATES, SEED 20260718**
- **NO IDENTIFIERS EMITTED TO RESULTS**

Patient-clustered bootstrap, 2,000 replicates, seed 20260718, 95% percentile intervals, coverage 80%. A hypothesis is confirmed only when its interval excludes zero **and** the point estimate reaches 0.02.

| H | model | contrast | estimate | 95% CI | excl. 0 | supports dir. | material | verdict |
| --- | --- | --- | ---: | :---: | :---: | :---: | :---: | :---: |
| H1 | M4 | external C0 - source C0 | +0.0246 | (+0.0182, +0.0315) | yes | yes | yes | **CONFIRMED** |
| H1 | M1 | external C0 - source C0 | +0.0511 | (+0.0450, +0.0568) | yes | yes | yes | **CONFIRMED** |
| H2 | M4 | interaction: (ext C1-C0) - (src C1-C0) | +0.0088 | (+0.0042, +0.0137) | yes | yes | no | **not confirmed** |
| H2 | M4 | interaction: (ext C2-C0) - (src C2-C0) | -0.0062 | (-0.0109, -0.0015) | yes | no | no | **not confirmed** |
| H3 | M4 | transfer gap M4 - transfer gap M1 | -0.0265 | (-0.0316, -0.0216) | yes | no | no | **REVERSED** |
| H4 | M4 [source] | C2 - C1 | +0.0060 | (+0.0019, +0.0102) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [external] | C2 - C1 | -0.0090 | (-0.0108, -0.0072) | yes | no | no | **not confirmed** |

## Coverage drift

A drift of 0.05 from target is prespecified as material.

| site | model | condition | realised | drift | material |
| --- | --- | --- | ---: | ---: | :---: |
| source | M1 | C0 | 80.6% | +0.0056 | no |
| source | M1 | C1 | 80.6% | +0.0056 | no |
| source | M1 | C2 | 80.6% | +0.0056 | no |
| source | M4 | C0 | 80.8% | +0.0077 | no |
| source | M4 | C1 | 82.0% | +0.0200 | no |
| source | M4 | C2 | 79.7% | -0.0026 | no |
| external | M1 | C0 | 76.5% | -0.0348 | no |
| external | M1 | C1 | 76.5% | -0.0348 | no |
| external | M1 | C2 | 76.5% | -0.0348 | no |
| external | M4 | C0 | 77.4% | -0.0259 | no |
| external | M4 | C1 | 77.8% | -0.0222 | no |
| external | M4 | C2 | 76.7% | -0.0329 | no |
