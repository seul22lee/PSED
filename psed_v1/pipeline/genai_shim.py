#!/usr/bin/env python3
"""
_genai_shim.py — minimal, stdlib-only `google.genai`-compatible client backed by the
Gemini REST endpoint, PLUS the instrumentation the scoped re-extraction needs.

Why this exists: this sandbox has NO PyPI access (cannot `pip install google-genai`),
but the Gemini REST API IS reachable and the key works. This shim implements EXACTLY the
surface the current 04_extract.py / 05_figure_extract.py touch, so those scripts run
UNCHANGED (no extraction-rule change). Every model call is intercepted here to enforce the
scope allow-list and the hard call budget, preserve the raw response, and record a full
reproducibility log entry.

Interface reproduced (verbatim to what 04/05 use):
  from google import genai            -> genai.Client(api_key=...)
  client.models.generate_content(model=..., contents=<str|[Part,str]>, config=<Cfg>)
  from google.genai import types      -> types.GenerateContentConfig(...), types.Part.from_bytes(...)
  response: .text, .candidates[0].finish_reason, .usage_metadata.{prompt,candidates,thoughts}_token_count
"""
import base64, json, time, hashlib, urllib.request, urllib.error
from pathlib import Path

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

# instrumentation state — the orchestrator sets allow/max_calls/ctx/raw_root/hashes
STATE = {
    "allow": set(),        # scope guard: only these DOIs may be called
    "max_calls": 600,      # hard budget guard
    "calls": 0,            # billable model calls made so far
    "ctx": None,           # {"doi","unit","src_hash"} — set before each unit
    "attempts": {},        # (doi,unit) -> attempt count
    "log": [],             # per-call reproducibility records
    "raw_root": None,      # Path to extracted/  (raw responses saved under {doi}/raw/)
    "hashes": {},          # ontology / schema / prompt_version shas
    "pace_s": 0.6,         # inter-call pacing to respect RPM
}


class BudgetExceeded(Exception):
    pass


class ScopeViolation(Exception):
    pass


# ---- types.* ----------------------------------------------------------------
class Part:
    def __init__(self, data=None, mime_type=None, text=None):
        self.inline_data = {"mime_type": mime_type, "data": data} if data is not None else None
        self.text = text

    @classmethod
    def from_bytes(cls, data, mime_type):
        return cls(data=data, mime_type=mime_type)

    @classmethod
    def from_text(cls, text):
        return cls(text=text)


class GenerateContentConfig:
    def __init__(self, temperature=None, response_mime_type=None, max_output_tokens=None, **kw):
        self.temperature = temperature
        self.response_mime_type = response_mime_type
        self.max_output_tokens = max_output_tokens


# ---- response objects -------------------------------------------------------
class _Usage:
    def __init__(self, u):
        self.prompt_token_count = u.get("promptTokenCount")
        self.candidates_token_count = u.get("candidatesTokenCount")
        self.thoughts_token_count = u.get("thoughtsTokenCount")
        self.total_token_count = u.get("totalTokenCount")


class _Cand:
    def __init__(self, c):
        self.finish_reason = c.get("finishReason")


class _Resp:
    def __init__(self, text, cands, usage):
        self.text = text
        self.candidates = cands
        self.usage_metadata = usage


def _parts_to_rest(contents):
    if isinstance(contents, str):
        return [{"text": contents}]
    out = []
    for c in contents:
        if isinstance(c, str):
            out.append({"text": c})
        elif isinstance(c, Part):
            if c.inline_data is not None:
                out.append({"inline_data": {"mime_type": c.inline_data["mime_type"],
                                            "data": base64.b64encode(c.inline_data["data"]).decode()}})
            elif c.text is not None:
                out.append({"text": c.text})
        elif isinstance(c, dict):
            out.append(c)
    return out


def _looks_json(t):
    try:
        s = (t or "").strip()
        if s.startswith("```"):
            return True
        json.loads(s)
        return True
    except Exception:
        return False


class _Models:
    def __init__(self, key):
        self._key = key

    def generate_content(self, model=None, contents=None, config=None):
        st = STATE
        ctx = st["ctx"] or {"doi": "?", "unit": "?"}
        doi, unit = ctx["doi"], ctx["unit"]
        # --- hard guards ---
        if st["allow"] and doi not in st["allow"]:
            raise ScopeViolation(f"DOI {doi!r} is not in the approved 31-paper allow-list")
        if st["calls"] >= st["max_calls"]:
            raise BudgetExceeded(f"hard call budget {st['max_calls']} reached")
        key = (doi, unit)
        st["attempts"][key] = st["attempts"].get(key, 0) + 1
        attempt = st["attempts"][key]

        parts = _parts_to_rest(contents)
        prompt_text = "".join(p.get("text", "") for p in parts if "text" in p)
        prompt_sha = hashlib.sha256(prompt_text.encode()).hexdigest()
        gen = {}
        if config is not None:
            if config.temperature is not None:
                gen["temperature"] = config.temperature
            if config.response_mime_type:
                gen["responseMimeType"] = config.response_mime_type
            if config.max_output_tokens:
                gen["maxOutputTokens"] = config.max_output_tokens
        body = {"contents": [{"role": "user", "parts": parts}]}
        if gen:
            body["generationConfig"] = gen
        url = ENDPOINT.format(model=model, key=self._key)
        data = json.dumps(body).encode()

        st["calls"] += 1
        resp, http = None, None
        for net in range(4):                     # transient-network / rate-limit backoff
            try:
                req = urllib.request.Request(url, data=data,
                                             headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=240) as r:
                    resp, http = json.loads(r.read()), 200
                break
            except urllib.error.HTTPError as e:
                code, bodytxt = e.code, e.read().decode()[:400]
                if code in (429, 500, 503) and net < 3:
                    time.sleep(2 ** net + 1)
                    continue
                resp, http = {"_http_error": code, "_body": bodytxt}, code
                break
            except Exception as e:
                if net < 3:
                    time.sleep(2 ** net + 1)
                    continue
                resp, http = {"_net_error": str(e)[:300]}, None
                break

        cands = resp.get("candidates") or []
        text = ""
        if cands:
            for p in ((cands[0].get("content") or {}).get("parts") or []):
                if "text" in p:
                    text += p["text"]
        usage = _Usage(resp.get("usageMetadata") or {})
        finish = (cands[0].get("finishReason") if cands
                  else resp.get("_http_error") or resp.get("_net_error"))

        # preserve the FULL raw response (per attempt)
        raw_root = Path(st["raw_root"])
        raw_dir = raw_root / doi / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{unit}.a{attempt}.json"
        raw_path.write_text(json.dumps(resp, indent=1)[:4_000_000])

        st["log"].append({
            "doi": doi, "unit": unit, "attempt": attempt, "call_index": st["calls"],
            "model": model, "gen_params": gen,
            "prompt_sha256": prompt_sha, "prompt_chars": len(prompt_text),
            "ontology_sha256": st["hashes"].get("ontology"),
            "schema_sha256": st["hashes"].get("schema"),
            "prompt_version_sha256": st["hashes"].get("prompt_version"),
            "source_artifact_sha256": ctx.get("src_hash"),
            "raw_path": str(raw_path.relative_to(raw_root.parent)),
            "finish_reason": finish, "http_status": http,
            "usage": {"in": usage.prompt_token_count, "out": usage.candidates_token_count,
                      "thoughts": usage.thoughts_token_count, "total": usage.total_token_count},
            "response_is_json": _looks_json(text), "ts": time.time(),
        })
        if st["pace_s"]:
            time.sleep(st["pace_s"])
        return _Resp(text, [_Cand(c) for c in cands], usage)


class Client:
    def __init__(self, api_key=None):
        self._key = api_key
        self.models = _Models(api_key)


def install():
    """Register this shim as google.genai / google.genai.types in sys.modules so the
    existing `from google import genai` / `from google.genai import types` resolve to it."""
    import sys, types as _pytypes
    google_mod = sys.modules.get("google") or _pytypes.ModuleType("google")
    genai_mod = _pytypes.ModuleType("google.genai")
    types_mod = _pytypes.ModuleType("google.genai.types")
    types_mod.Part = Part
    types_mod.GenerateContentConfig = GenerateContentConfig
    genai_mod.Client = Client
    genai_mod.types = types_mod
    setattr(google_mod, "genai", genai_mod)
    sys.modules["google"] = google_mod
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.types"] = types_mod
    return genai_mod
