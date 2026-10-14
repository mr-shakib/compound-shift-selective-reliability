"""Local, offline reading form for the blinded expert adjudication.

Serves one study at a time on 127.0.0.1 only. The page shows the study's
frontal images and the protocol's form (section 5) and nothing else: no site,
report text, context, report labels, model output, stratum or file name.
Images are addressed by a random item token. Every answer is appended to
``data/adjudication/reads_<reader>.csv`` at once, so a session can stop and
resume at any point; the analysis uses each reader's last answer per item.

    python -m c3e.adjudication.reader --reader A      # then open http://127.0.0.1:8765

``--allow-224`` serves the pipeline's 224-pixel copies when an original is
missing. It exists only to test the form; reads made with it are marked and
are not study data.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time
from urllib.parse import parse_qs

import pandas as pd

from ..calibration.policy import TARGETS
from ..external.dataset import IMAGE_DIR as EXT_224
from ..training.runner import IMAGE_DIR as SRC_224
from .fetch import full_path
from .sample import OUT_DATA

FINDINGS = [t.lower().replace(" ", "_") for t in TARGETS]
CHOICES = ("present", "absent", "indeterminate")
FIELDS = (["item_id", "saved_utc", "seconds", "quality", "projection"] + FINDINGS
          + [f"{f}_confidence" for f in FINDINGS] + ["support_devices", "comment", "test_mode"])


def validate(form: dict[str, str]) -> list[str]:
    """Return the names of missing or invalid fields (empty when complete)."""
    bad = []
    if form.get("quality") not in ("adequate", "limited", "inadequate"):
        bad.append("quality")
    if form.get("projection") not in ("AP", "PA", "other", "indeterminate"):
        bad.append("projection")
    for f in FINDINGS:
        if form.get(f) not in CHOICES:
            bad.append(f)
        if form.get(f"{f}_confidence") not in ("1", "2", "3", "4", "5"):
            bad.append(f"{f}_confidence")
    if form.get("support_devices") not in ("yes", "no"):
        bad.append("support_devices")
    return bad


def append_read(path: Path, row: dict[str, str]) -> None:
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})


def done_items(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(pd.read_csv(path, usecols=["item_id"]).item_id.astype(str))


def next_position(order: list[str], done: set[str]) -> int | None:
    for i, item in enumerate(order):
        if item not in done:
            return i
    return None


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Reading {pos} of {total}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}}
header{{padding:8px 14px;background:#222;display:flex;gap:18px;align-items:center;flex-wrap:wrap}}
.imgs{{display:flex;gap:8px;padding:8px;flex-wrap:wrap;justify-content:center}}
.imgs img{{max-height:78vh;max-width:96vw;cursor:zoom-in;filter:brightness(var(--b)) contrast(var(--c))}}
.imgs img.full{{max-height:none;max-width:none;cursor:zoom-out}}
form{{background:#1b1b1b;padding:12px 14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}}
fieldset{{border:1px solid #444;border-radius:6px}} legend{{font-weight:600}}
label{{margin-right:10px;white-space:nowrap}} .warn{{color:#f88}} .practice{{color:#fc6;font-weight:700}}
button{{font-size:1rem;padding:8px 18px}} textarea{{width:100%;background:#222;color:#eee}}
</style></head><body style="--b:1;--c:1">
<header><b>Item {pos} of {total}</b>{practice}
<label>Brightness <input type="range" min="0.4" max="2" step="0.05" value="1"
 oninput="document.body.style.setProperty('--b',this.value)"></label>
<label>Contrast <input type="range" min="0.4" max="3" step="0.05" value="1"
 oninput="document.body.style.setProperty('--c',this.value)"></label>
<span>Click an image to toggle full resolution.</span>{warn}</header>
<div class="imgs">{images}</div>
<form method="post" action="/save">
<input type="hidden" name="item_id" value="{item}"><input type="hidden" name="t0" value="{t0}">
<fieldset><legend>Image quality</legend>{quality}</fieldset>
<fieldset><legend>Projection</legend>{projection}</fieldset>
{findings}
<fieldset><legend>Support devices present</legend>{devices}</fieldset>
<fieldset><legend>Comment (no identifiers)</legend><textarea name="comment" rows="2"></textarea></fieldset>
<div><button type="submit">Save and next</button></div>
</form>
<script>document.querySelectorAll('.imgs img').forEach(i=>i.onclick=()=>i.classList.toggle('full'))</script>
</body></html>"""


def _radios(name: str, values, labels=None) -> str:
    labels = labels or values
    return "".join(f'<label><input type="radio" name="{name}" value="{escape(v)}" required> {escape(l)}</label>'
                   for v, l in zip(values, labels))


class Session:
    def __init__(self, root: Path, reader: str, allow_224: bool):
        self.root, self.reader, self.allow_224 = Path(root), reader, allow_224
        d = self.root / OUT_DATA
        self.items = pd.read_csv(d / "sample_v1.csv").set_index("item_id")
        self.order = pd.read_csv(d / f"order_reader_{reader}.csv").sort_values("position").item_id.astype(str).tolist()
        self.reads = d / f"reads_{reader}.csv"
        if not allow_224:
            missing = [i for i in self.order for img in json.loads(self.items.loc[i, "images"])
                       if not full_path(self.root, self.items.loc[i, "site"], img).exists()]
            if missing:
                raise SystemExit(f"{len(missing)} original images are missing; run c3e.adjudication.fetch first")

    def image_file(self, item: str, k: int) -> Path:
        row = self.items.loc[item]
        img = json.loads(row["images"])[k]
        p = full_path(self.root, row["site"], img)
        if p.exists() or not self.allow_224:
            return p
        return self.root / (SRC_224 if row["site"] == "source" else EXT_224) / img

    def page(self, pos: int) -> str:
        item = self.order[pos]
        row = self.items.loc[item]
        n_img = len(json.loads(row["images"]))
        findings = "".join(
            f"<fieldset><legend>{escape(t)}</legend>{_radios(f, CHOICES)}<br>Confidence "
            f"{_radios(f + '_confidence', [str(i) for i in range(1, 6)])}</fieldset>"
            for t, f in zip(TARGETS, FINDINGS))
        return PAGE.format(
            pos=pos + 1, total=len(self.order), item=escape(item), t0=f"{time.time():.0f}",
            practice=' <span class="practice">Practice item (not study data)</span>'
            if row["item_set"] == "practice" else "",
            warn=' <span class="warn">TEST MODE: 224-pixel images</span>' if self.allow_224 else "",
            images="".join(f'<img src="/img/{escape(item)}/{k}" alt="">' for k in range(n_img)),
            quality=_radios("quality", ("adequate", "limited", "inadequate")),
            projection=_radios("projection", ("AP", "PA", "other", "indeterminate")),
            findings=findings, devices=_radios("support_devices", ("yes", "no")))


def make_handler(session: Session):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # no request logging: paths carry item tokens only
            pass

        def _send(self, code, body: bytes, ctype="text/html; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/img/"):
                _, _, item, k = self.path.split("/", 3)
                if item not in session.items.index:
                    return self._send(404, b"")
                p = session.image_file(item, int(k))
                ctype = "image/png" if p.suffix == ".png" else "image/jpeg"
                return self._send(200, p.read_bytes(), ctype)
            pos = next_position(session.order, done_items(session.reads))
            if pos is None:
                return self._send(200, b"<p style='font-family:sans-serif'>All items are read. Thank you.</p>")
            return self._send(200, session.page(pos).encode())

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            form = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
            if form.get("item_id") not in session.items.index or validate(form):
                return self._send(400, b"Incomplete form. Go back and answer every field.")
            form["saved_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            form["seconds"] = str(int(time.time() - float(form.get("t0", time.time()))))
            form["test_mode"] = "1" if session.allow_224 else "0"
            append_read(session.reads, form)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

    return Handler


def main(argv=None) -> int:
    default_root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Expert adjudication: local reading form")
    ap.add_argument("--project-root", type=Path, default=default_root)
    ap.add_argument("--reader", required=True, choices=["A", "B"])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--allow-224", action="store_true", help="test mode only; not study data")
    a = ap.parse_args(argv)
    session = Session(a.project_root.resolve(), a.reader, a.allow_224)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(session))
    print(f"Reader {a.reader}: open http://127.0.0.1:{a.port}  (Ctrl-C to stop; progress is saved)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
