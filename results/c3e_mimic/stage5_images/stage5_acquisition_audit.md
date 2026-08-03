# C3-E6 Stage 5 — Frontal Image Acquisition

Status: **PASS**

- **STAGE 5 ONLY**
- **FRONTAL IMAGE ACQUISITION**
- **NO IMAGE CONTENT DECODED**
- **NO MODEL TRAINING**
- **NO PREDICTION THRESHOLD SELECTION**
- **NO EVALUATION OR METRIC COMPUTATION**
- **NO LABELS GENERATED IN THIS RUN**
- **IMAGES CONFINED TO THE PROTECTED DATA TREE**
- **NO IDENTIFIERS EMITTED TO RESULTS**

## Source

| field | value |
| --- | --- |
| provider | PhysioNet, AWS S3 access point |
| region | us-east-1 |
| dataset | MIMIC-CXR-JPG v2.1.0 |

The PhysioNet HTTP endpoint was not used for bulk transfer. It sustained
0.15 MB/s against a 27 MB/s link and blocked the account after an hour; the
cause is a single origin at 331 ms round trip serving objects small enough
that each transfer ends before TCP slow-start opens the window.

## Acquisition

| tier | expected | present | GB | complete |
| --- | ---: | ---: | ---: | :---: |
| prespecified_eval | 16,456 | 16,456 | 27.1 | yes |
| threshold_calibration | 10,264 | 10,264 | 16.9 | yes |
| official_validate | 1,584 | 1,584 | 2.6 | yes |
| official_test | 2,155 | 2,155 | 3.6 | yes |
| model_train | 162,823 | 162,823 | 268.3 | yes |
| **total** | **193,282** | **193,282** | **318.5** | **yes** |

Mean image size 1,769,202 bytes.

## Integrity

Every acquired image was hashed and compared against the publisher's
`SHA256SUMS.txt`. Hashing operates on file bytes and does not decode image
content.

| check | value |
| --- | ---: |
| entries checked | 193,282 |
| entries matching | 193,282 |
| mismatches on first pass | 1 |
| unresolved mismatches | **0** |

One file failed on the first pass: a partial object left by an interrupted
transfer. The resume check tested whether a file was non-empty rather than
whether it was complete, so the truncated file was skipped on retry rather
than repaired. It was re-fetched and re-verified. A checksum pass is
therefore mandatory after any resumed transfer, not optional.

Image paths are restricted data and are not included here.
