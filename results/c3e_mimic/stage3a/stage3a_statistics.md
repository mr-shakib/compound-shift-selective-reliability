# C3-E6 Stage 3A — Aggregate Dataset Statistics

Aggregation level: cohort only; no patient-level, study-level, or row-level values are emitted.

## Counts

| Quantity | Value |
| --- | ---: |
| patients | 65379 |
| studies | 227835 |
| records | 377110 |
| provider rows | 227835 |
| distinct providers any role | 2893 |
| reports available | 227835 |
| reports missing | 0 |
| reports unexpected | 0 |

Report coverage of listed studies: 100.0000%

## Distributions

| Distribution | min | p25 | median | mean | p75 | p95 | p99 | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| records per study | 1 | 1.0 | 2.0 | 1.6552 | 2.0 | 3.0 | 3.0 | 11 |
| studies per patient | 1 | 1.0 | 1.0 | 3.4848 | 3.0 | 13.0 | 28.0 | 158 |
| records per patient | 1 | 2.0 | 3.0 | 5.7681 | 6.0 | 20.0 | 41.0 | 174 |

## Records per study (histogram)

| records in study | studies |
| ---: | ---: |
| 1 | 102675 |
| 2 | 103481 |
| 3 | 19442 |
| 4 | 2097 |
| 5 | 99 |
| 6 | 33 |
| 7 | 2 |
| 8 | 4 |
| 9 | 1 |
| 11 | 1 |

## Provider coverage

| role | coverage | distinct providers | null rows |
| --- | ---: | ---: | ---: |
| ordering_provider_id | 99.8429% | 2755 | 358 |
| attending_provider_id | 100.0000% | 55 | 0 |
| resident_provider_id | 36.4496% | 115 | 144790 |

## Report archive

- Members: 227835
- Uncompressed bytes: 151686630
- Member size (bytes): {'min': 46, 'mean': 665.77, 'max': 3933}

### Patient-bucket distribution

| bucket | reports |
| --- | ---: |
| p10 | 22197 |
| p11 | 23358 |
| p12 | 22428 |
| p13 | 22945 |
| p14 | 22589 |
| p15 | 23713 |
| p16 | 22151 |
| p17 | 22695 |
| p18 | 22929 |
| p19 | 22830 |

No patient-level, study-level, or row-level values appear in this file.
