"""Blinded expert adjudication (docs/revision/EXPERT_ADJUDICATION_PROTOCOL.md).

``sample`` draws the stratified study sample, ``fetch`` retrieves the
full-resolution originals of the sampled images, and ``reader`` serves a local,
offline reading form. Row-level output (the sample list, images, reads) stays
in the gitignored ``data/adjudication/`` tree; only aggregate counts and
digests reach ``results/``.
"""
