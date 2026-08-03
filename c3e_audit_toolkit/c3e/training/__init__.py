"""C3-E6 Stage 6: source-site model training.

Trains M1 through M4 on the model-train tier only. The threshold-calibration
and prespecified-eval tiers are reserved for later stages and are never read
here; internal validation for early stopping is carved from model train itself.
"""
