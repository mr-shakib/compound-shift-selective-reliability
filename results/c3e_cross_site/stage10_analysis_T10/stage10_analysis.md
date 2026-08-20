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
| H1 | M3 | external C0 - source C0 | +0.0221 | (+0.0129, +0.0310) | yes | yes | yes | **CONFIRMED** |
| H1 | M4 | external C0 - source C0 | +0.0232 | (+0.0159, +0.0302) | yes | yes | yes | **CONFIRMED** |
| H1 | M1 | external C0 - source C0 | +0.0559 | (+0.0461, +0.0649) | yes | yes | yes | **CONFIRMED** |
| H1 | M2 | external C0 - source C0 | +0.0202 | (+0.0082, +0.0314) | yes | yes | yes | **CONFIRMED** |
| H2 | M3 | interaction: (ext C1-C0) - (src C1-C0) | +0.0101 | (+0.0019, +0.0177) | yes | yes | no | **not confirmed** |
| H2 | M3 | interaction: (ext C2-C0) - (src C2-C0) | -0.0219 | (-0.0319, -0.0123) | yes | no | no | **REVERSED** |
| H2 | M4 | interaction: (ext C1-C0) - (src C1-C0) | +0.0057 | (-0.0023, +0.0128) | no | no | no | **not confirmed** |
| H2 | M4 | interaction: (ext C2-C0) - (src C2-C0) | -0.0161 | (-0.0239, -0.0088) | yes | no | no | **not confirmed** |
| H3 | M3 | transfer gap M3 - transfer gap M1 | -0.0338 | (-0.0425, -0.0257) | yes | no | no | **REVERSED** |
| H3 | M4 | transfer gap M4 - transfer gap M1 | -0.0327 | (-0.0416, -0.0234) | yes | no | no | **REVERSED** |
| H4 | M3 [source] | C2 - C1 | +0.0606 | (+0.0524, +0.0686) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [source] | C2 - C1 | +0.0199 | (+0.0137, +0.0265) | yes | yes | yes | **CONFIRMED** |
| H4 | M3 [external] | C2 - C1 | +0.0286 | (+0.0238, +0.0334) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [external] | C2 - C1 | -0.0020 | (-0.0067, +0.0023) | no | no | no | **not confirmed** |

## Coverage drift

A drift of 0.05 from target is prespecified as material.

| site | model | condition | realised | drift | material |
| --- | --- | --- | ---: | ---: | :---: |
| source | M1 | C0 | 78.9% | -0.0108 | no |
| source | M1 | C1 | 78.9% | -0.0108 | no |
| source | M1 | C2 | 78.9% | -0.0108 | no |
| source | M2 | C0 | 78.5% | -0.0154 | no |
| source | M2 | C1 | 100.0% | +0.2000 | **yes** |
| source | M2 | C2 | 77.3% | -0.0266 | no |
| source | M3 | C0 | 83.1% | +0.0309 | no |
| source | M3 | C1 | 83.4% | +0.0336 | no |
| source | M3 | C2 | 75.1% | -0.0489 | no |
| source | M4 | C0 | 80.8% | +0.0075 | no |
| source | M4 | C1 | 79.6% | -0.0039 | no |
| source | M4 | C2 | 79.9% | -0.0009 | no |
| external | M1 | C0 | 77.1% | -0.0286 | no |
| external | M1 | C1 | 77.1% | -0.0286 | no |
| external | M1 | C2 | 77.1% | -0.0286 | no |
| external | M2 | C0 | 85.3% | +0.0528 | **yes** |
| external | M2 | C1 | 100.0% | +0.2000 | **yes** |
| external | M2 | C2 | 85.1% | +0.0508 | **yes** |
| external | M3 | C0 | 77.7% | -0.0234 | no |
| external | M3 | C1 | 82.3% | +0.0230 | no |
| external | M3 | C2 | 73.5% | -0.0648 | **yes** |
| external | M4 | C0 | 79.0% | -0.0096 | no |
| external | M4 | C1 | 76.2% | -0.0381 | no |
| external | M4 | C2 | 78.8% | -0.0120 | no |
