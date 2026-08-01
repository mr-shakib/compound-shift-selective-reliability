# C3-E6 Stage 3B — `context_text` Availability Against the Frozen Contract

The frozen C3E data policy requires a pre-diagnostic `context_text` column and
prohibits `findings`, `impression`, and `full_report` as model inputs. This file
records whether the MIMIC target site can satisfy that contract, and at what cost
in cohort size. It contains no report text.

## Candidate pre-diagnostic fields

| section | reports | coverage | median tokens | body is de-identification only |
| --- | ---: | ---: | ---: | ---: |
| comparison | 163853 | 71.9174% | 2 | 57005 |
| examination | 102460 | 44.9711% | 3 | 5 |
| history | 57019 | 25.0264% | 6 | 8 |
| indication | 165862 | 72.7992% | 13 | 6 |
| technique | 81365 | 35.7122% | 4 | 13 |

## Prohibited-as-input fields (label sources only)

| section | reports | coverage | median tokens |
| --- | ---: | ---: | ---: |
| findings | 149738 | 65.7221% | 45 |
| findings_impression_combined | 134 | 0.0588% | 43 |
| impression | 189444 | 83.1496% | 17 |

## Post-diagnostic sections that must be excluded from `context_text`

| section | reports | coverage |
| --- | ---: | ---: |
| addendum | 182 | 0.0799% |
| comment | 196 | 0.0860% |
| notification | 5755 | 2.5260% |
| provisional_impression | 199 | 0.0873% |
| recommendation | 1810 | 0.7944% |
| wet_read | 17551 | 7.7034% |

## Effective cohort ceiling

- Studies in archive: 227835
- With any pre-diagnostic context: 227288 (99.7599%)
- With context and an impression label source: 189326 (83.0979%)
- With context and a findings label source: 149484 (65.6106%)

These are ceilings measured at the study level before any view filter is applied.
The frozen policy restricts eligible views to frontal, and view position is still
unavailable in this download, so the realised cohort will be strictly smaller.

### Caveat: presence is not substance

The pre-diagnostic availability figure counts a study as covered if ANY pre-diagnostic
header is present, including near-boilerplate ones. Judged by median body length,
`comparison` (2 tokens),
`examination` (3 tokens), and
`technique` (4 tokens) carry almost no
clinical content. The substantive context fields are
`indication` (72.80% coverage,
median 13 tokens) and
`history` (25.03% coverage,
median 6 tokens).

Stage 3C must therefore define `context_state` against a substantive-content rule, not
against header presence. Using header presence alone would classify near-empty
boilerplate as available context and would inflate the C0 stratum.

## Construction constraints implied by this audit

- Extraction must be header-driven. Section order is not a safe rule: some reports
  place pre-diagnostic text after the first diagnostic section.
- WET READ and PROVISIONAL FINDINGS IMPRESSION are preliminary interpretations. They
  are post-diagnostic and must never enter `context_text`.
- Reports merging findings and impression cannot supply the frozen primary/sensitivity
  label-source separation and need an explicit inclusion rule.
- De-identification placeholders can empty a section body. Presence of a header is not
  evidence of usable context; effective emptiness must be checked after placeholder removal.
