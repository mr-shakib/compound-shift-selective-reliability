# C3-E6 Stage 3B-2 — C2 Pairing Feasibility by Context-Length Bin

The frozen C2 intervention applies a deterministic permutation under the constraints
`same_institution, same_split, different_patient, same_context_length_bin`. Pairing can only succeed if each context-length bin
contains at least two distinct patients and no single patient holds half or more of the
bin, otherwise some study cannot receive text from a different patient.

Assessed on the `indication_history` permitted set, across studies with non-empty context.

| length bin (effective tokens) | studies | distinct patients | largest patient | share | pairing feasible |
| --- | ---: | ---: | ---: | ---: | --- |
| 01-05 | 43667 | 26473 | 38 | 0.0870% | True |
| 06-10 | 77500 | 39175 | 51 | 0.0658% | True |
| 11-20 | 68672 | 29948 | 49 | 0.0714% | True |
| 21-40 | 20908 | 11991 | 24 | 0.1148% | True |
| 41-80 | 9429 | 6090 | 19 | 0.2015% | True |
| 81+ | 2563 | 1911 | 10 | 0.3902% | True |

## Interpretation

- All populated bins are feasible at corpus level.
- Corpus-level feasibility is necessary but not sufficient. The frozen constraint also
  requires pairing within split. No official split file is present, so split-level
  feasibility cannot be verified and must be re-checked once splits exist.
- Bin edges here are provisional. They are not a frozen decision and can be changed by
  the protocol amendment that fixes the N1 threshold.
