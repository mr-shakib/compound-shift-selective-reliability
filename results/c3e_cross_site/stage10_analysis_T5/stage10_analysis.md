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
| H1 | M3 | external C0 - source C0 | +0.0381 | (+0.0316, +0.0449) | yes | yes | yes | **CONFIRMED** |
| H1 | M4 | external C0 - source C0 | +0.0330 | (+0.0279, +0.0381) | yes | yes | yes | **CONFIRMED** |
| H1 | M1 | external C0 - source C0 | +0.0696 | (+0.0624, +0.0766) | yes | yes | yes | **CONFIRMED** |
| H1 | M2 | external C0 - source C0 | +0.0661 | (+0.0581, +0.0742) | yes | yes | yes | **CONFIRMED** |
| H2 | M3 | interaction: (ext C1-C0) - (src C1-C0) | +0.0081 | (+0.0027, +0.0135) | yes | yes | no | **not confirmed** |
| H2 | M3 | interaction: (ext C2-C0) - (src C2-C0) | -0.0242 | (-0.0310, -0.0174) | yes | no | no | **REVERSED** |
| H2 | M4 | interaction: (ext C1-C0) - (src C1-C0) | +0.0121 | (+0.0069, +0.0173) | yes | yes | no | **not confirmed** |
| H2 | M4 | interaction: (ext C2-C0) - (src C2-C0) | -0.0131 | (-0.0182, -0.0077) | yes | no | no | **not confirmed** |
| H3 | M3 | transfer gap M3 - transfer gap M1 | -0.0314 | (-0.0371, -0.0257) | yes | no | no | **REVERSED** |
| H3 | M4 | transfer gap M4 - transfer gap M1 | -0.0366 | (-0.0426, -0.0301) | yes | no | no | **REVERSED** |
| H4 | M3 [source] | C2 - C1 | +0.0517 | (+0.0457, +0.0576) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [source] | C2 - C1 | +0.0204 | (+0.0157, +0.0251) | yes | yes | yes | **CONFIRMED** |
| H4 | M3 [external] | C2 - C1 | +0.0194 | (+0.0173, +0.0215) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [external] | C2 - C1 | -0.0048 | (-0.0068, -0.0027) | yes | no | no | **not confirmed** |

## Coverage drift

A drift of 0.05 from target is prespecified as material.

| site | model | condition | realised | drift | material |
| --- | --- | --- | ---: | ---: | :---: |
| source | M1 | C0 | 79.5% | -0.0046 | no |
| source | M1 | C1 | 79.5% | -0.0046 | no |
| source | M1 | C2 | 79.5% | -0.0046 | no |
| source | M2 | C0 | 80.1% | +0.0006 | no |
| source | M2 | C1 | 100.0% | +0.2000 | **yes** |
| source | M2 | C2 | 78.9% | -0.0110 | no |
| source | M3 | C0 | 80.3% | +0.0026 | no |
| source | M3 | C1 | 82.4% | +0.0243 | no |
| source | M3 | C2 | 73.6% | -0.0644 | **yes** |
| source | M4 | C0 | 80.2% | +0.0018 | no |
| source | M4 | C1 | 80.6% | +0.0059 | no |
| source | M4 | C2 | 79.2% | -0.0081 | no |
| external | M1 | C0 | 77.2% | -0.0280 | no |
| external | M1 | C1 | 77.2% | -0.0280 | no |
| external | M1 | C2 | 77.2% | -0.0280 | no |
| external | M2 | C0 | 85.4% | +0.0542 | **yes** |
| external | M2 | C1 | 100.0% | +0.2000 | **yes** |
| external | M2 | C2 | 85.3% | +0.0532 | **yes** |
| external | M3 | C0 | 77.2% | -0.0275 | no |
| external | M3 | C1 | 82.8% | +0.0279 | no |
| external | M3 | C2 | 73.9% | -0.0606 | **yes** |
| external | M4 | C0 | 79.5% | -0.0046 | no |
| external | M4 | C1 | 76.4% | -0.0358 | no |
| external | M4 | C2 | 78.9% | -0.0114 | no |
