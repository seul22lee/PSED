#!/usr/bin/env python3
"""The agent's local web app: ask questions, watch the tool calls, inspect the evidence.

    python -m psed_v2.agent.app [--port 8765] [--no-browser]       # run from the repository root, conda env psed310

FastAPI over agent.Conversation and one page (static/index.html, no build step). The page reads only the conversation log and
the tool results; the one thing it asks the server for besides the agent is a sample's unit tree (tools.unit_tree, a KB tool
the model is not offered), which is appended to the log as a UI tool call. Saved logs in agent/runs/ open read-only.
Crops are served from psed_v2/ingest/final/ only (not in git): this checkout's, else the main checkout's (tools.CROP_ROOT).
The model is PSED_MODEL from the environment or psed_v2/.env (agent.resolve_model).
"""
import argparse, json, queue, threading, uuid, webbrowser
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from . import agent as A
from . import run_cases as R
from . import tools as T

HERE = Path(__file__).resolve().parent
app = FastAPI(title="ALD KB agent")
CONVS = {}                                     # conversation id -> agent.Conversation
LOCK = threading.Lock()


class NewConv(BaseModel):
    case: str | None = None


class Ask(BaseModel):
    id: str
    text: str


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/status")
def status():
    import os
    provider, model = A.resolve_model()
    return {"provider": provider, "model": model, "api_key": bool(os.environ.get(A.PROVIDERS[provider].key_var)),
            "key_var": A.PROVIDERS[provider].key_var, "effort": A.EFFORT[provider], "max_tool_calls": A.MAX_TOOL_CALLS,
            "recipe_source": T.RECIPE_SOURCE, "presets": R.CASES, "papers": {k: p["label"] for k, p in T.kb().papers.items()}}


@app.post("/api/new")
def new(body: NewConv):
    try:
        conv = A.Conversation(case=body.case, mode="batch" if body.case else "interactive", origin="app")
    except Exception as e:  # noqa: BLE001 - no SDK or no credentials: say so on the page
        raise HTTPException(400, A.scrub(f"{type(e).__name__}: {e}"))
    cid = uuid.uuid4().hex[:12]
    CONVS[cid] = conv
    return {"id": cid, "log_path": conv.path.name, "mode": conv.mode, "case": body.case}


@app.post("/api/ask")
def ask(body: Ask):
    conv = CONVS.get(body.id)
    if conv is None:
        raise HTTPException(404, "unknown conversation")
    q = queue.Queue()

    def work():
        with LOCK:
            try:
                conv.ask(body.text, lambda kind, data: q.put((kind, data)))
            except Exception as e:  # noqa: BLE001
                q.put(("error", {"message": A.scrub(f"{type(e).__name__}: {e}")}))
        q.put(("done", {}))

    threading.Thread(target=work, daemon=True).start()

    def stream():
        while True:
            kind, data = q.get()
            yield f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
            if kind == "done":
                return

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/log/{cid}")
def log(cid: str):
    conv = CONVS.get(cid)
    if conv is None:
        raise HTTPException(404, "unknown conversation")
    return JSONResponse(conv.log)


@app.get("/api/runs")
def runs():
    out = []
    for p in sorted(A.RUNS.glob("*.json"), reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        out.append({"name": p.name, "case": d.get("case"), "started": d.get("started"), "turns": len(d.get("turns", [])),
                    "question": (d.get("turns") or [{}])[0].get("user", "")})
    return out


@app.get("/api/runs/{name}")
def run(name: str):
    p = (A.RUNS / name).resolve()
    if p.parent != A.RUNS.resolve() or not p.exists():
        raise HTTPException(404, "no such log")
    return JSONResponse(json.loads(p.read_text(encoding="utf-8")))


@app.get("/api/tree")
def tree(unit: str, cid: str | None = None):
    result = T.unit_tree(unit)
    conv = CONVS.get(cid or "")
    if conv is not None:
        conv.log.setdefault("ui_tool_calls", []).append({"name": "unit_tree", "input": {"unit_id": unit}, "result": result})
        conv.save()
    return result


@app.get("/api/crop")
def crop(path: str):
    p = (T.CROP_ROOT / path).resolve()
    if not p.is_relative_to(T.FINAL.resolve()) or not p.is_file():
        raise HTTPException(404, "crop not on this machine")
    return FileResponse(p)


def main():
    import uvicorn
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    A.load_env()                               # psed_v2/.env of this checkout, else of the main checkout
    T.kb()                                     # load the KB before the first request
    url = f"http://127.0.0.1:{a.port}/"
    if not a.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"ALD KB agent on {url}")
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
