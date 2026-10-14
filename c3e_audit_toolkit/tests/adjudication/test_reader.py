"""Local reading form: validation, resume, and one end-to-end save."""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
from PIL import Image

from c3e.adjudication.reader import FINDINGS, Session, make_handler, next_position, validate

COMPLETE = {"quality": "adequate", "projection": "AP", "support_devices": "no",
            **{f: "absent" for f in FINDINGS}, **{f"{f}_confidence": "4" for f in FINDINGS}}


def test_validate_requires_every_field():
    assert validate(COMPLETE) == []
    assert "edema" in validate({**COMPLETE, "edema": ""})
    assert "quality" in validate({k: v for k, v in COMPLETE.items() if k != "quality"})


def test_next_position_resumes_at_first_unread():
    assert next_position(["a", "b", "c"], {"a"}) == 1
    assert next_position(["a", "b"], {"a", "b"}) is None


def test_end_to_end_save_and_blinding(tmp_path):
    d = tmp_path / "data/adjudication"
    d.mkdir(parents=True)
    img = "files/p10/p1000/s1/x.jpg"
    (tmp_path / "data/mimic/images_224" / img).parent.mkdir(parents=True)
    Image.new("L", (8, 8)).save(tmp_path / "data/mimic/images_224" / img)
    pd.DataFrame([{"item_id": "tok1", "site": "source", "study": "s1", "patient": "p1000",
                   "stratum": "L1A1P1", "inclusion_prob": 0.1, "item_set": "estimation",
                   "images": json.dumps([img])}]).to_csv(d / "sample_v1.csv", index=False)
    pd.DataFrame({"position": [1], "item_id": ["tok1"]}).to_csv(d / "order_reader_A.csv", index=False)
    s = Session(tmp_path, "A", allow_224=True)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(s))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        page = urlopen(base + "/").read().decode()
        assert "Item 1 of 1" in page and "/img/tok1/0" in page
        for leak in ("source", "files/p10", "s1", "L1A1P1", "p1000"):
            assert leak not in page
        assert urlopen(base + "/img/tok1/0").read()[:3] == b"\xff\xd8\xff"   # JPEG bytes
        bad = Request(base + "/save", data=urlencode({"item_id": "tok1"}).encode(), method="POST")
        try:
            urlopen(bad)
            raise AssertionError("incomplete form was accepted")
        except Exception as exc:  # noqa: BLE001
            assert "400" in str(exc)
        ok = Request(base + "/save", data=urlencode({"item_id": "tok1", "t0": "0", **COMPLETE}).encode(),
                     method="POST")
        assert "All items are read" in urlopen(ok).read().decode()
    finally:
        srv.shutdown()
    reads = pd.read_csv(d / "reads_A.csv")
    assert reads.item_id.tolist() == ["tok1"] and reads.test_mode.tolist() == [1]
