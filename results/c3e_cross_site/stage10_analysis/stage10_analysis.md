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
| H1 | M3 | external C0 - source C0 | +0.0469 | (+0.0408, +0.0531) | yes | yes | yes | **CONFIRMED** |
| H1 | M4 | external C0 - source C0 | +0.0384 | (+0.0336, +0.0430) | yes | yes | yes | **CONFIRMED** |
| H1 | M1 | external C0 - source C0 | +0.0734 | (+0.0668, +0.0802) | yes | yes | yes | **CONFIRMED** |
| H1 | M2 | external C0 - source C0 | +0.0763 | (+0.0687, +0.0838) | yes | yes | yes | **CONFIRMED** |
| H2 | M3 | interaction: (ext C1-C0) - (src C1-C0) | +0.0024 | (-0.0027, +0.0076) | no | no | no | **not confirmed** |
| H2 | M3 | interaction: (ext C2-C0) - (src C2-C0) | -0.0219 | (-0.0279, -0.0160) | yes | no | no | **REVERSED** |
| H2 | M4 | interaction: (ext C1-C0) - (src C1-C0) | +0.0096 | (+0.0048, +0.0144) | yes | yes | no | **not confirmed** |
| H2 | M4 | interaction: (ext C2-C0) - (src C2-C0) | -0.0137 | (-0.0185, -0.0087) | yes | no | no | **not confirmed** |
| H3 | M3 | transfer gap M3 - transfer gap M1 | -0.0265 | (-0.0321, -0.0212) | yes | no | no | **REVERSED** |
| H3 | M4 | transfer gap M4 - transfer gap M1 | -0.0350 | (-0.0408, -0.0292) | yes | no | no | **REVERSED** |
| H4 | M3 [source] | C2 - C1 | +0.0475 | (+0.0422, +0.0524) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [source] | C2 - C1 | +0.0173 | (+0.0125, +0.0217) | yes | yes | yes | **CONFIRMED** |
| H4 | M3 [external] | C2 - C1 | +0.0231 | (+0.0211, +0.0250) | yes | yes | yes | **CONFIRMED** |
| H4 | M4 [external] | C2 - C1 | -0.0060 | (-0.0080, -0.0041) | yes | no | no | **not confirmed** |

## Coverage drift

A drift of 0.05 from target is prespecified as material.

| site | model | condition | realised | drift | material |
| --- | --- | --- | ---: | ---: | :---: |
| source | M1 | C0 | 79.6% | -0.0044 | no |
| source | M1 | C1 | 79.6% | -0.0044 | no |
| source | M1 | C2 | 79.6% | -0.0044 | no |
| source | M2 | C0 | 80.3% | +0.0028 | no |
| source | M2 | C1 | 100.0% | +0.2000 | **yes** |
| source | M2 | C2 | 79.0% | -0.0100 | no |
| source | M3 | C0 | 79.8% | -0.0020 | no |
| source | M3 | C1 | 82.1% | +0.0215 | no |
| source | M3 | C2 | 72.8% | -0.0718 | **yes** |
| source | M4 | C0 | 80.0% | -0.0002 | no |
| source | M4 | C1 | 80.5% | +0.0052 | no |
| source | M4 | C2 | 78.9% | -0.0108 | no |
| external | M1 | C0 | 77.2% | -0.0284 | no |
| external | M1 | C1 | 77.2% | -0.0284 | no |
| external | M1 | C2 | 77.2% | -0.0284 | no |
| external | M2 | C0 | 84.7% | +0.0469 | no |
| external | M2 | C1 | 100.0% | +0.2000 | **yes** |
| external | M2 | C2 | 84.6% | +0.0459 | no |
| external | M3 | C0 | 77.4% | -0.0258 | no |
| external | M3 | C1 | 82.8% | +0.0277 | no |
| external | M3 | C2 | 74.6% | -0.0537 | **yes** |
| external | M4 | C0 | 79.5% | -0.0051 | no |
| external | M4 | C1 | 76.4% | -0.0359 | no |
| external | M4 | C2 | 78.8% | -0.0123 | no |
