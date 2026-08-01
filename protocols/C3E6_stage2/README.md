# C3E6 Stage 2 — Machine-Readable Protocol

This bundle freezes the machine-readable specification for the C3E compound-shift selective-reliability study.

## Current authorization

- Documentation and configuration validation: **authorized**
- Metadata audit after MIMIC access: **authorized**
- Medical-image loading: **not authorized**
- Model training: **not authorized**
- CheXpert tuning: **forbidden**

## Files

- `config/experiment_registry.yaml`: main experimental and governance registry.
- `config/context_interventions.yaml`: N1-N3 and C0-C2 definitions.
- `config/metric_registry.yaml`: primary and secondary metrics.
- `config/hypothesis_registry.yaml`: H1-H4 and label-source sensitivity.
- `config/data_policy.yaml`: identifiers, harmonized columns, and leakage restrictions.
- `schema/*.schema.json`: machine validation schemas.
- `scripts/validate_protocol.py`: schema and cross-registry validation.
- `tests/test_protocol.py`: protocol-lock unit tests.
- `reports/validation_report.json`: generated validation result.

## Validate

```bash
python scripts/validate_protocol.py
python -m unittest discover -s tests -v
```

## Amendment rule

Any change after external-result inspection must receive a new protocol version, be recorded in `AMENDMENT_LOG.md`, and be labeled post-hoc exploratory unless prespecified before target inspection.

## Intentionally pending

- ~~Exact MIMIC pre-diagnostic section mapping.~~ **Resolved in v0.2.0 (2026-07-28)**
  through MIMIC intake; see `AMENDMENT_LOG.md` and
  `docs/C3E6_SOURCE_TEXT_MAPPING_AND_INFORMATIVENESS_RULE.md`. No CheXpert result was
  inspected.
- Exact image and text backbones after the hardware gate.

These may be resolved only through the MIMIC intake and compute preflight, never by inspecting CheXpert results.
