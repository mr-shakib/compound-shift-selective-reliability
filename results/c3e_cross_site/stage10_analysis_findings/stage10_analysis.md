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
| H1 | M3 | external C0 - source C0 | -0.1324 | (-0.1399, -0.1246) | yes | no | no | **REVERSED** |
| H1 | M4 | external C0 - source C0 | -0.1079 | (-0.1141, -0.1014) | yes | no | no | **REVERSED** |
| H1 | M1 | external C0 - source C0 | -0.0672 | (-0.0736, -0.0607) | yes | no | no | **REVERSED** |
| H1 | M2 | external C0 - source C0 | -0.2385 | (-0.2470, -0.2303) | yes | no | no | **REVERSED** |
| H2 | M3 | interaction: (ext C1-C0) - (src C1-C0) | +0.0340 | (+0.0282, +0.0399) | yes | yes | yes | **CONFIRMED** |
| H2 | M3 | interaction: (ext C2-C0) - (src C2-C0) | -0.0178 | (-0.0250, -0.0110) | yes | no | no | **not confirmed** |
| H2 | M4 | interaction: (ext C1-C0) - (src C1-C0) | +0.0625 | (+0.0565, +0.0685) | yes | yes | yes | **CONFIRMED** |
| H2 | M4 | interaction: (ext C2-C0) - (src C2-C0) | +0.0041 | (-0.0024, +0.0107) | no | no | no | **not confirmed** |
| H3 | M3 | transfer gap M3 - transfer gap M1 | -0.0652 | (-0.0713, -0.0585) | yes | no | no | **REVERSED** |
| H3 | M4 | transfer gap M4 - transfer gap M1 | -0.0408 | (-0.0473, -0.0341) | yes | no | no | **REVERSED** |
| H4 | M3 [source] | C2 - C1 | +0.0606 | (+0.0540, +0.0671) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [source] | C2 - C1 | +0.0479 | (+0.0420, +0.0542) | yes | yes | yes | **CONFIRMED** |
| H4 | M3 [external] | C2 - C1 | +0.0089 | (+0.0078, +0.0100) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [external] | C2 - C1 | -0.0104 | (-0.0117, -0.0092) | yes | no | no | **not confirmed** |

## Coverage drift

A drift of 0.05 from target is prespecified as material.

| site | model | condition | realised | drift | material |
| --- | --- | --- | ---: | ---: | :---: |
| source | M1 | C0 | 79.7% | -0.0026 | no |
| source | M1 | C1 | 79.7% | -0.0026 | no |
| source | M1 | C2 | 79.7% | -0.0026 | no |
| source | M2 | C0 | 79.9% | -0.0009 | no |
| source | M2 | C1 | 100.0% | +0.2000 | **yes** |
| source | M2 | C2 | 78.6% | -0.0144 | no |
| source | M3 | C0 | 79.7% | -0.0032 | no |
| source | M3 | C1 | 84.2% | +0.0417 | no |
| source | M3 | C2 | 75.2% | -0.0485 | no |
| source | M4 | C0 | 79.4% | -0.0055 | no |
| source | M4 | C1 | 81.4% | +0.0136 | no |
| source | M4 | C2 | 78.0% | -0.0195 | no |
| external | M1 | C0 | 75.9% | -0.0407 | no |
| external | M1 | C1 | 75.9% | -0.0407 | no |
| external | M1 | C2 | 75.9% | -0.0407 | no |
| external | M2 | C0 | 81.3% | +0.0129 | no |
| external | M2 | C1 | 100.0% | +0.2000 | **yes** |
| external | M2 | C2 | 81.2% | +0.0118 | no |
| external | M3 | C0 | 80.5% | +0.0046 | no |
| external | M3 | C1 | 85.4% | +0.0539 | **yes** |
| external | M3 | C2 | 77.8% | -0.0216 | no |
| external | M4 | C0 | 79.6% | -0.0037 | no |
| external | M4 | C1 | 76.6% | -0.0343 | no |
| external | M4 | C2 | 78.9% | -0.0108 | no |
