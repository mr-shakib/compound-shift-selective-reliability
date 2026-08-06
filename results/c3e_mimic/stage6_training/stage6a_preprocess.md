# C3-E6 Stage 6a — Image Preprocessing

Status: **PASS**

- **STAGE 6a ONLY**
- **IMAGE DECODE AND RESIZE**
- **NO MODEL TRAINING IN THIS RUN**
- **NO LABELS READ**
- **NO PREDICTION THRESHOLD SELECTION**
- **NO EVALUATION OR METRIC COMPUTATION**
- **ORIGINALS LEFT UNMODIFIED**
- **PREPROCESSED IMAGES CONFINED TO THE PROTECTED DATA TREE**
- **NO IDENTIFIERS EMITTED TO RESULTS**

| field | value |
| --- | ---: |
| input resolution | 224px |
| images written | 193,282 |
| images failed | 0 |
| source size | 318.5 GB |
| output size | 2.43 GB |
| compression | 131.3x |
| elapsed | 829 s |

Resolution, channel handling, and the resample filter are fixed by
`models.exact_backbones` in protocol v0.4.0 and are not tunable at this stage.

Image paths are restricted data and are not included here.
