# C3-E Empirical Protocol

## Primary decision

Continue to a text-only modeling audit only when both hospitals satisfy the local gate and the cross-site comparison detects a meaningful context-availability or context-quality shift.

## Primary labels

1. Cardiomegaly
2. Edema
3. Pleural Effusion

Atelectasis and Consolidation are secondary.

## Context

Include only pre-diagnostic fields such as clinical history, history, indication, or reason for examination. Exclude findings, impression, summary, and diagnostic conclusion.

## Patient-level integrity

MIMIC uses the official split file. CheXpert Plus should be partitioned by patient only if internal target tuning becomes necessary; its main role remains untouched external evaluation.

## Leakage categories

- Direct target name
- Synonym
- Affirmed mention
- Negated mention
- Speculative or “rule-out” mention

The audit does not automatically remove text. It quantifies the threat.

## Phase decision logic

### GO to C3-E2: Text-only modeling audit

- ≥3 viable labels
- usable context ≥40% at each site
- missing or low-information context ≥5% at at least one site
- direct target mention among positive cases ≤70% for viable labels
- no patient overlap across source splits
- meaningful cross-site context shift

### MODIFY

- only 2 viable labels
- missingness is weak but context-quality shift is strong
- direct mentions are high but masked context remains potentially useful
- one institution requires a different context-field mapping

### REJECT route

- fewer than 2 viable labels
- context almost always absent or almost always label-revealing
- no meaningful cross-site context shift
- labels cannot be harmonized
- patient-level integrity cannot be guaranteed
