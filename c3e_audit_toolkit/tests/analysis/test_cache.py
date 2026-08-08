"""Guards on the prediction cache. Fixtures are synthetic."""

from __future__ import annotations

import numpy as np

from c3e.analysis.cache import cache_path, load, save


def _arrays(n=7):
    rng = np.random.default_rng(0)
    return dict(probabilities=rng.random((n, 5)),
                labels=rng.integers(0, 2, (n, 5)).astype(float),
                mask=np.ones((n, 5)),
                patients=np.array([f"pt{i//2}" for i in range(n)]))


def test_roundtrip_preserves_arrays(tmp_path):
    a = _arrays()
    save(tmp_path, "external", "M4", "C1", checkpoint_sha="abc123", **a)
    got = load(tmp_path, "external", "M4", "C1", checkpoint_sha="abc123")
    assert np.allclose(got["probabilities"], a["probabilities"])
    assert list(got["patients"]) == list(a["patients"])


def test_cache_from_other_weights_is_rejected(tmp_path):
    """Reusing a cache built by different weights would silently mix models."""
    save(tmp_path, "external", "M4", "C1", checkpoint_sha="abc123", **_arrays())
    assert load(tmp_path, "external", "M4", "C1", checkpoint_sha="different") is None


def test_missing_cache_returns_none(tmp_path):
    assert load(tmp_path, "source", "M1", "C0", checkpoint_sha="abc123") is None


def test_conditions_and_sites_do_not_collide(tmp_path):
    for site in ("source", "external"):
        for cond in ("C0", "C1", "C2"):
            save(tmp_path, site, "M1", cond, checkpoint_sha="s", **_arrays())
    paths = {cache_path(tmp_path, s, "M1", c)
             for s in ("source", "external") for c in ("C0", "C1", "C2")}
    assert len(paths) == 6
    assert all(p.exists() for p in paths)


def test_label_source_is_part_of_the_key(tmp_path):
    """The findings sensitivity analysis must not overwrite the primary."""
    save(tmp_path, "external", "M1", "C0", checkpoint_sha="s",
         label_source="impression", **_arrays())
    assert load(tmp_path, "external", "M1", "C0", checkpoint_sha="s",
                label_source="findings") is None


def test_threshold_is_part_of_the_cache_key(tmp_path):
    """A cache built at one informativeness threshold must not be reused at
    another. The threshold decides which studies are N1 and therefore which
    studies are in the cohort at all, so a silent reuse would describe the wrong
    population while looking like a hit."""
    save(tmp_path, "source", "M4", "C0", checkpoint_sha="s", threshold=3, **_arrays())
    assert load(tmp_path, "source", "M4", "C0", checkpoint_sha="s", threshold=3) is not None
    assert load(tmp_path, "source", "M4", "C0", checkpoint_sha="s", threshold=5) is None


def test_primary_threshold_keeps_the_unsuffixed_path(tmp_path):
    """The preregistered T=3 caches keep their existing names, so adding the key
    does not invalidate work already done."""
    p3 = cache_path(tmp_path, "source", "M1", "C0", "impression", 3)
    p5 = cache_path(tmp_path, "source", "M1", "C0", "impression", 5)
    assert p3.name == "source__M1__C0__impression.npz"
    assert p5.name == "source__M1__C0__impression__T5.npz"
