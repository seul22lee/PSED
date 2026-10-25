#!/usr/bin/env python3
"""P133: what the extraction passes share: the paper index, the held-out guard, the provider call, the cache and records/<pid>.jsonl.

Provider: google-genai (conda env psed310), the client and the tolerant JSON parse of ingest/figures.py (ported from psed_v1
pipeline/figures/figure_extract.py); MODEL fixed, temperature 0, provider-side structured output (response_json_schema). The
provider schema is the form with the keywords the provider does not take removed (PROVIDER_DROP); enums are kept.
Key: GOOGLE_API_KEY, from the environment or psed_v2/.env (figures.load_env; never printed, never written).
Cache: cache/<pid>/<pass>_<section>_<prompt_hash>_<model>.json (gitignored); a hit makes no call and appends nothing. The key is
the hash of the full request (prompt, response schema, thinking) whether or not a prefix is sent as cached content.
P148: a job may carry a fixed prefix (the start of its prompt): before the first call of a run the prefix is registered once as
Gemini cached content (caches.create, TTL CONTENT_TTL), every call of the run references it and sends only the rest of its prompt;
the cached content is deleted when the run ends. The line records cache_read_tokens (usage_metadata.cached_content_token_count).
Records: records/<pid>.jsonl (tracked), one line per call made, append-only.
One retry on a transport error; a second failure, or any other error, stops the run.
"""
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(V2 / "kb" / "pilot"))
sys.path.insert(0, str(V2 / "ingest"))
sys.path.insert(0, str(V2 / "ontology"))
import elements as E  # noqa: E402
import export as X  # noqa: E402
from figures import client_for, load_env, loads_json  # noqa: E402,F401

MODEL = "gemini-3.8-flash"                                                       # user, P133: pinned (gemini-2.5-flash 404s)
KEY_ENV = "GOOGLE_API_KEY"                                                     # user, P133: the repo key of psed_v2/.env
HELD_OUT = set()                                                                 # P157f (user, 2026-10-23): papers 1-12 (the pilot golds) are development papers; papers 13+ are held-out (none yet)
CONTENT_TTL = "3600s"                                                           # P148: the cached prefix lives at most an hour (deleted at the end of the run)
HELD_OUT |= {pid for pid, k in E.PAPERS.items() if k in HELD_OUT}
CACHE, RECORDS, SCHEMA = V2 / "kb" / "cache", V2 / "kb" / "records", V2 / "kb" / "schema"
FAILED = RECORDS / "failed_calls.csv"                                            # P196b (user): every failed call (a response that does not parse)
FAILED_FIELDS = ["pid", "pass", "section", "prompt_hash", "model", "form_version", "request_ts", "input_tokens", "output_tokens", "response_chars",
                 "attempt", "reason", "note"]
PROVIDER_DROP = {"additionalProperties", "pattern", "uniqueItems", "propertyNames", "minProperties", "dependentRequired", "allOf", "if", "then",
                 "else", "$schema", "$id", "$comment"}   # validation the compiler does against the full form.json (P134)


class Stop(Exception):
    """The run stops: the reason is printed and nothing more is called."""


def resolve(arg):
    """A paper key (yli18) or paper id -> (pid, key), from pilot/elements.py PAPERS; held-out papers are refused."""
    pid = next((p for p, k in E.PAPERS.items() if arg in (p, k)), None)
    if pid is None:
        raise Stop(f"{arg}: not in the paper index (pilot/elements.py PAPERS)")
    if pid in HELD_OUT or E.PAPERS[pid] in HELD_OUT:
        raise Stop(f"{arg}: held out, never run")
    return pid, E.PAPERS[pid]


def schema(name):
    return json.loads((SCHEMA / name).read_text(encoding="utf-8"))


def provider_schema(s, defs=None):
    """The schema without PROVIDER_DROP (a false schema left under properties is dropped too); enums kept. P133 (user, option 2,
    after a bare 400 on pass 1): every $ref inlined from defs (the schema's own $defs by default; $defs then removed) and a const
    written as a one-value enum; P133 (user, after a second bare 400): no union, an anyOf becomes a string (the compiler casts it);
    P133 (user, after the probe): an enum longer than export.PROVIDER_ENUM_MAX becomes a plain string (the prompt lists its ids)."""
    if defs is None and isinstance(s, dict):
        defs = s.get("$defs", {})
    if isinstance(s, dict):
        if "anyOf" in s:                                                        # P139: [X, null] -> X with null in its type (and enum); any other union a string
            other = [x for x in s["anyOf"] if not (isinstance(x, dict) and x.get("type") == "null")]
            out = provider_schema(other[0], defs) if len(other) == 1 else {"type": "string"}
            if len(other) < len(s["anyOf"]):
                out = dict(out)
                t = out.get("type", "string")
                out["type"] = (t if isinstance(t, list) else [t]) + ["null"]
                if "enum" in out:
                    out["enum"] = list(out["enum"]) + [None]
            return out
        if "$ref" in s:
            return provider_schema(defs[s["$ref"].split("/")[-1]], defs)
        if len(s.get("enum", [])) > X.PROVIDER_ENUM_MAX:
            return {"type": "string"}
        if "const" in s:
            s = {**{k: v for k, v in s.items() if k != "const"}, "enum": [s["const"]]}
        return {k: provider_schema(v, defs) for k, v in s.items() if k not in PROVIDER_DROP | {"$defs"} and v is not False}
    if isinstance(s, list):
        return [provider_schema(v, defs) for v in s]
    return s


def request_hash(prompt, rschema, thinking=None):
    """sha256 of the full request: the prompt, the response schema and the thinking setting when one is set (all decide the response)."""
    extra = "\n" + json.dumps(thinking, sort_keys=True) if thinking else ""
    return hashlib.sha256((prompt + "\n" + json.dumps(rschema, sort_keys=True, ensure_ascii=False) + extra).encode("utf-8")).hexdigest()


def cache_path(pid, pass_, section, h):
    return CACHE / pid / f"{pass_}_{section}_{h[:16]}_{MODEL}.json"


def cached(cp):
    """P196b rule 1: a cache file is a hit only when its response parses (else the request is to call)."""
    return cp.exists() and parses(json.loads(cp.read_text(encoding="utf-8")).get("response"))


def plan(pid, jobs, thinking=None):
    """jobs: [(pass, section, prompt, rschema, element_ids[, prefix])] -> prints the planned calls; stops when the key is missing."""
    todo = [j for j in jobs if not cached(cache_path(pid, j[0], j[1], request_hash(j[2], j[3], thinking)))]
    load_env()
    print(f"{pid}: {len(jobs)} planned calls ({len(jobs) - len(todo)} cached, {len(todo)} to call), model {MODEL}")
    if todo and not os.environ.get(KEY_ENV):
        raise Stop(f"{KEY_ENV} is not set: no call made")
    return todo


def _transport(e):
    return isinstance(e, (ConnectionError, TimeoutError, OSError)) or type(e).__name__ in ("ConnectError", "ReadTimeout", "ConnectTimeout",
                                                                                         "RemoteProtocolError", "ReadError")


def cached_prefix(client, pid, prefix):
    """P148: the prefix registered as Gemini cached content -> its name."""
    from google.genai import types
    try:
        c = client.caches.create(model=MODEL, config=types.CreateCachedContentConfig(
            contents=[types.Content(role="user", parts=[types.Part(text=prefix)])], ttl=CONTENT_TTL, display_name=f"psed-{E.PAPERS.get(pid, pid)}-prefix"))
    except Exception as e:
        raise Stop(f"cached content not created ({type(e).__name__}): {str(e)[:300]}")
    return c.name


def call(client, prompt, rschema, thinking=None, cached=None):
    """One structured call -> (raw text, usage, request_ts); one retry on a transport error. thinking: e.g. {"thinking_level": "MINIMAL"}.
    P148: cached = the name of the cached content holding the prompt's prefix (prompt is then the rest)."""
    from google.genai import types
    cfg = types.GenerateContentConfig(temperature=0, response_mime_type="application/json", response_json_schema=rschema,
                                      thinking_config=types.ThinkingConfig(**thinking) if thinking else None, cached_content=cached)
    for attempt in (1, 2):
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        try:
            r = client.models.generate_content(model=MODEL, contents=prompt, config=cfg)
        except Exception as e:
            if attempt == 1 and _transport(e):
                continue
            if getattr(e, "code", None) == 404:                                 # user, P133: never switch models; list them and stop
                names = sorted(m.name for m in client.models.list() if "generateContent" in (m.supported_actions or []))
                raise Stop(f"{MODEL}: 404; models supporting generateContent:\n  " + "\n  ".join(names))
            raise Stop(f"provider error ({type(e).__name__}): {str(e)[:300]}")
        u = r.usage_metadata
        return r.text or "", dict(input_tokens=u.prompt_token_count or 0,
                                  output_tokens=(u.candidates_token_count or 0) + (u.thoughts_token_count or 0),
                                  cache_read_tokens=u.cached_content_token_count or 0), ts


def parses(text):
    """P196b (user): a response parses when the tolerant JSON parse (figures.loads_json, the one compile uses) reads it."""
    try:
        loads_json(text)
        return True
    except (ValueError, TypeError):
        return False


def failed_rows():
    import csv
    return list(csv.DictReader(FAILED.open(encoding="utf-8"))) if FAILED.exists() else []


def list_failed(row):
    """P196b (user) rule 1: a failed call is listed (records/failed_calls.csv, append-only), never stored as an answer."""
    import csv
    new = not FAILED.exists()
    RECORDS.mkdir(exist_ok=True)
    with FAILED.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FAILED_FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FAILED_FIELDS})


def run(pid, jobs, thinking=None, form_version=None):
    """Every job: from the cache, else one call (cached, then appended to records/<pid>.jsonl). Returns (lines, calls made).
    thinking (P133, pass 1): the provider's thinking setting, recorded in the line; None = the model's default (pass 0). P196 (user):
    form_version labels the new lines (P184-r1: P184's rules re-run on a later state); None = export.FORM_VERSION. P196b (user), every call:
    rule 1, a response that does not parse is a failed call: not stored as an answer (no records line), not cached (a cached one is a miss
    and is removed), listed in records/failed_calls.csv; rule 2, a failed call is retried once (a request listed as failed before has had
    its first attempt: no further retry)."""
    todo = plan(pid, jobs, thinking)
    client = client_for("google", os.environ[KEY_ENV]) if todo else None
    out, made, names = [], 0, {}                                                # P148: prefix hash -> cached content name
    try:
        for job in jobs:
            pass_, section, prompt, rschema, ids = job[:5]
            pre = job[5] if len(job) > 5 else ""
            assert prompt.startswith(pre)
            h = request_hash(prompt, rschema, thinking)
            cp = cache_path(pid, pass_, section, h)
            if cp.exists():
                hit = json.loads(cp.read_text(encoding="utf-8"))
                if parses(hit.get("response")):
                    out.append(hit)
                    continue
                cp.unlink()                                                     # P196b rule 1: a failed response is not cached
            ph = hashlib.sha256(pre.encode("utf-8")).hexdigest() if pre else ""
            if pre and ph not in names:
                names[ph] = cached_prefix(client, pid, pre)
            before, text = sum(1 for r in failed_rows() if r["prompt_hash"] == h), None
            for attempt in range(before + 1, 3):                                # P196b rule 2: the first attempt and one retry per request
                text, usage, ts = call(client, prompt[len(pre):] if pre else prompt, rschema, thinking, names.get(ph))
                made += 1
                if parses(text):
                    break
                try:
                    loads_json(text)
                except (ValueError, TypeError) as e:
                    why = f"{type(e).__name__}: {e}"[:200]
                list_failed(dict(pid=pid, section=section, prompt_hash=h, model=MODEL, form_version=form_version or X.FORM_VERSION, request_ts=ts,
                                 input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"], response_chars=len(text or ""), attempt=attempt,
                                 reason=why, note="", **{"pass": pass_}))
                print(f"{pid}: {section}: the response does not parse (attempt {attempt}): listed in records/failed_calls.csv, not stored")
                text = None
            if text is None:
                if before >= 2:
                    print(f"{pid}: {section}: failed twice before (records/failed_calls.csv): no attempt left, not called")
                continue
            line = dict(pid=pid, **{"pass": pass_}, section=section, element_ids=ids, model=MODEL, prompt_hash=h, ontology_hash=X.ontology_hash(),
                        form_version=form_version or X.FORM_VERSION,            # P158: compile.py applies the frozen form's rules to this line
                        request_ts=ts, usage=usage, **({"thinking": thinking} if thinking else {}), **({"prefix_hash": ph} if pre else {}), response=text)
            cp.parent.mkdir(parents=True, exist_ok=True)
            cp.write_text(json.dumps(line, ensure_ascii=False), encoding="utf-8")
            RECORDS.mkdir(exist_ok=True)
            with (RECORDS / f"{pid}.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
            out.append(line)
    finally:
        for name in names.values():                                             # P148: no stored prefix outlives the run
            try:
                client.caches.delete(name=name)
            except Exception as e:
                print(f"{pid}: cached content {name} not deleted ({type(e).__name__}); it expires after {CONTENT_TTL}")
    print(f"{pid}: {made} calls made, {len(jobs) - made} from the cache" + (f"; prefix cached once ({len(names)} cached content)" if names else ""))
    return out, made


def lines(pid, pass_=None):
    p = RECORDS / f"{pid}.jsonl"
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []
    return [r for r in rows if pass_ is None or r["pass"] == pass_]


def main(fn):
    try:
        return fn(sys.argv[1] if len(sys.argv) > 1 else "")
    except Stop as e:
        print("STOP:", e)
        return 1
