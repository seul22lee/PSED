#!/usr/bin/env python3
"""Serve reports/pilot.html and answer questions on it, on 127.0.0.1 only; the API keys stay in this process.

    ~/miniconda3/envs/psed310/bin/python psed_v2/pilot/serve.py [--port 8787]

GET /            the page (build it first: python3 psed_v2/pilot/report.py)
GET /status      the models that can be asked: PSED_MODEL and, for each vendor with a key, its rows of prices.csv
POST /ask        {question, model, run}: the last records of this question and model from runs/asks.jsonl, or (run, or none yet)
                 the three arms run now (ask.ask) and appended there
"""
import argparse, csv, json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ask  # noqa: E402
import providers as P  # noqa: E402

HOST = "127.0.0.1"
PAGE = HERE / "reports/pilot.html"


def models():
    vend = P.available()
    out = [P.default_model()] if P.default_model().split(":")[0] in vend else []
    f = HERE / "prices.csv"
    if f.exists():
        out += [f"{r['vendor']}:{r['model']}" for r in csv.DictReader(f.open(encoding="utf-8")) if r.get("vendor") in vend and r.get("model")]
    return dict(vendors=vend, models=list(dict.fromkeys(out)), default=out[0] if out else "")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith(("text", "application/json")) else ""))
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/pilot.html"):
            if not PAGE.exists():
                return self._send(404, b"build the page first: python3 psed_v2/pilot/report.py", "text/plain")
            return self._send(200, PAGE.read_bytes(), "text/html")
        if self.path == "/status":
            return self._send(200, models())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/ask":
            return self._send(404, {"error": "not found"})
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            q, m = (req.get("question") or "").strip(), req.get("model") or models()["default"]
            if not q:
                return self._send(400, {"error": "empty question"})
            if m not in models()["models"]:
                return self._send(400, {"error": f"model not available: {m}"})
            recs = [] if req.get("run") else ask.last_records(q, m)
            asked_before = len(recs) == len(ask.ARMS)
            if not asked_before:
                recs = ask.ask(q, m)
            self._send(200, dict(records=recs, asked_before=asked_before))
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):                                         # the request line only, never a header or a body
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args()
    st = models()
    print(f"http://{HOST}:{a.port}/  models: {', '.join(st['models']) or 'none (fill the keys in psed_v2/.env)'}")
    ThreadingHTTPServer((HOST, a.port), Handler).serve_forever()
