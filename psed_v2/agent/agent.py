#!/usr/bin/env python3
"""The KB question-answering agent: a model calls the deterministic tools of tools.py step by step until it answers.
Every request, tool call, tool result and the final answer is logged to agent/runs/<case>_<timestamp>.json.

    python3 -m psed_v2.agent.agent "question" [--case NAME] [--model PROVIDER:MODEL] [--effort LEVEL]   # one question (batch)
    python3 -m psed_v2.agent.agent --interactive                                                        # follow-ups

The model is PSED_MODEL ('provider:model', from the environment or psed_v2/.env; --model overrides): deepseek:<model>
(the openai SDK on DeepSeek's OpenAI-compatible API, https://api.deepseek.com, key DEEPSEEK_API_KEY; thinking on, each turn's
reasoning_content passed back in every later request as the API requires with tools) or anthropic:<model> (the anthropic SDK,
key ANTHROPIC_API_KEY; adaptive thinking, summarized; the server-side refusal fallback on, a turn served by another model is
logged as fallback_ran). psed_v2/.env is read from this checkout, else the main checkout (a linked worktree has none); its
values are never logged and are scrubbed from logged errors. Both providers stream; the loop is one: the model calls tools,
reads the results, calls again, until it answers. Cap: MAX_TOOL_CALLS tool calls per question; past it every call returns an
error asking for the answer. Each tool result is sent as tools.model_view(result) (curve points summarized, statements cut);
the log keeps the full result and the text sent, the provider, the model and the token usage of every request.
Runs with conda env psed310 (anthropic and openai SDKs).
"""
import argparse, datetime, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

from . import tools as T

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
DEFAULT_MODEL = "anthropic:claude-sonnet-5-5"
EFFORT = {"anthropic": "medium", "deepseek": "high"}          # deepseek: the model's default level (low / high / max)
MAX_TOKENS = 64000
MAX_TOOL_CALLS = 15
EXTRA_REQUESTS = 2                     # requests allowed after the cap before the question ends without an answer
FALLBACK_BETA = "server-side-fallback-2026-07-01"
DEEPSEEK_URL = "https://api.deepseek.com"
# $ per million tokens; deepseek-flash at its peak rates (an upper bound; off-peak is half), api-docs.deepseek.com, 2026-10-25
PRICES = {"claude-sonnet-5-5": {"input": 2.00, "cache_write": 2.50, "cache_read": 0.20, "output": 10.00},
          "deepseek-flash": {"input": 0.30, "cache_write": 0.30, "cache_read": 0.006, "output": 1.20}}
ENV_FILES = [T.V2 / ".env", T.MAIN / "psed_v2" / ".env"]
SECRETS = set()


def load_env():
    """KEY=VALUE lines of the first psed_v2/.env found into os.environ where unset; returns its path (values are not logged)."""
    for p in ENV_FILES:
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
                if m and not line.strip().startswith("#"):
                    k, v = m.group(1), m.group(2).strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)
            break
    for k, v in os.environ.items():
        if k.endswith("_API_KEY") and v:
            SECRETS.add(v)
    return next((str(p) for p in ENV_FILES if p.is_file()), None)


def scrub(text):
    """A string with every known key value (and a masked key fragment as APIs print them) replaced by ***."""
    text = str(text)
    for s in SECRETS:
        text = text.replace(s, "***")
    return re.sub(r"\b(sk-[A-Za-z0-9]{0,6})[A-Za-z0-9*._-]{6,}", r"\1***", text)


def resolve_model(spec=None):
    """(provider, model) from 'provider:model' (--model, else PSED_MODEL, else DEFAULT_MODEL); a bare model id names its provider."""
    spec = spec or os.environ.get("PSED_MODEL") or DEFAULT_MODEL
    if ":" in spec:
        provider, model = spec.split(":", 1)
    else:
        provider, model = ("deepseek" if spec.startswith("deepseek") else "anthropic"), spec
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider '{provider}' in '{spec}' (known: {', '.join(PROVIDERS)})")
    return provider, model


def paper_list():
    return "\n".join(f"- {k} = {p['label']}: {p['title']}" for k, p in sorted(T.kb().papers.items(), key=lambda x: x[1]["label"]))


SYSTEM = """You answer questions about atomic layer deposition (ALD) conformality from a knowledge base (KB) compiled from 13 \
papers. You work only through the tools; they are deterministic and read the KB. Fact ids start with the paper's key.

Papers in the KB (key = Author Year: title):
{papers}

How the KB is organized: a recipe holds deposition runs; a run holds samples (specimens, or the run's film); a sample holds \
measurements. A simulation holds model runs. A sample inherits the conditions of its run and recipe; the tools say where each \
value comes from (this sample, its run, its recipe), and flag conflicts between a sample's own value and an inherited one.

How to work:
- Before your first tool call, state your plan in one or two sentences.
- Resolve the terms of the question to KB concepts (resolve), find the samples whose conditions match (find_samples), get their \
records (get_records), compare them (compare), and look up the claims the papers make (claims) or the source of a cited value \
(trace_citation), as the question needs. At most {max_calls} tool calls.

Rules for the answer:
- Every number in the answer comes from a tool result. Cite the fact_id of each value in square brackets right after it, \
e.g. "99 µm [yim20:tab1.r16c11#1]". A count you report (samples, papers, images, values) comes from a tool's counts or lists.
- Use only the 13 papers in the KB. A value a paper cites from another work is reported as cited, never as evidence; when \
trace_citation finds the cited paper among the 13, report that paper's own value instead and say the two agree or differ.
- Say "not recorded" when the KB has no record. Do not infer or guess causes. Report recorded differences between samples and \
the claims the KB holds, not speculation.
- Report what the tools flag: a conflict between a sample's own value and an inherited one (prefer the sample's own value and \
say so), values excluded or rejected and why, samples the KB leaves undecided.
- Use plain names: samples, runs, papers, measurements, images, values, curves. Say "measured", "read from a figure", \
"computed by the authors", "computed by the KB from figure data", "cited", "model input" or "simulated" for how a value was \
obtained. Name papers as Author Year. Do not use the KB's internal terms (entity, activity, unit, fact, binding, data_kind, \
level, qualifier).
- Keep the answer short: the direct answer first, then the evidence (a compact list or table), then what is not recorded or open.

{mode}"""

MODES = {
    "batch": "Mode: batch. Do not ask a clarifying question. If the question can be read in more than one way, take the most "
             "reasonable reading and state it in one sentence at the start of the answer.",
    "interactive": "Mode: interactive. If the question can be read in more than one way and the reading changes the answer, ask "
                   "one short clarifying question before any tool call; otherwise go ahead. The user may ask follow-up questions.",
}

_STR_LIST = {"type": "array", "items": {"type": "string"}}
TOOL_SCHEMAS = [
    {"name": "resolve",
     "description": "Find the KB's ontology concepts for a term (a quantity, method, structure, species or setting). Returns "
                    "matches with how they matched (exact name or alias, partial, in a definition, printed so on KB records); "
                    "for a method the methods of the same class; for a structure class its subclasses and structures; for a "
                    "quantity its unit and dimension, the labels it is printed as in the papers, the qualifiers it carries in "
                    "the KB (e.g. level=50%), and other concepts of the same category (different concepts, keep them apart).",
     "input_schema": {"type": "object", "properties": {
         "term": {"type": "string", "description": "the term as the user wrote it, e.g. 'SEM', 'high aspect ratio', 'sticking coefficient'"},
         "kind": {"type": "string", "enum": ["quantity", "method", "structure", "species", "categorical", "mechanism", "model"],
                  "description": "optional: only concepts of this kind"}},
         "required": ["term"]}},
    {"name": "find_samples",
     "description": "Find coated samples (specimens and run films; model runs only with include_models) whose conditions match "
                    "every filter. A sample's conditions include those inherited from its run and recipe, and the run's "
                    "reactants, carrier gas, process mode and material from the recipe fill. Filter kinds: a quantity with a "
                    "value and unit or a min/max range (deposition_temperature, feature_width, cycle_number, ...); a categorical "
                    "or species setting with one or more ids (reactant_A, reactant_B, material, process_mode, carrier_gas, "
                    "reactor); concept 'structure' with structure classes or structures (a class matches its subclasses); "
                    "concept 'method' with measurement methods (the sample was measured by one of them). Returns per sample the "
                    "matched conditions as 'value [fact_id] (where from)', the values of the vary concepts, and conflicts; the "
                    "counts (scanned, matched, per paper), how many failed each filter and why, and samples the KB leaves "
                    "undecided (a value not recorded, recorded only as a range, or several values on its run or recipe).",
     "input_schema": {"type": "object", "properties": {
         "filters": {"type": "array", "items": {"type": "object", "properties": {
             "concept": {"type": "string", "description": "a concept id from resolve, or 'structure' / 'method'"},
             "value": {"description": "a number, an id, or a list of ids",
                       "anyOf": [{"type": "number"}, {"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
             "unit": {"type": "string", "description": "the unit of a numeric value or range, e.g. '°C', 'nm'"},
             "min": {"type": "number"}, "max": {"type": "number"},
             "qualifiers": {"type": "object", "description": "e.g. {\"step\": \"reactant_A\"}", "additionalProperties": {"type": "string"}}},
             "required": ["concept"]}},
         "vary": dict(_STR_LIST, description="concept ids left free; their values are returned per sample, e.g. ['cycle_number']"),
         "include_models": {"type": "boolean", "description": "also scan model runs (simulations); default false"},
         "papers": dict(_STR_LIST, description="optional: paper keys to scan")},
         "required": ["filters"]}},
    {"name": "get_records",
     "description": "Records of samples (their own and their measurements'): values (each with fact_id, value, unit, how it was "
                    "obtained, the statement as printed, the sample's key conditions), curves (digitized figure series: axes, "
                    "series label, number and range of points, values the KB read from the curve such as a plateau or a 50% "
                    "crossing) and images (id, method, description, crop path). With no sample_ids, searches every record of the "
                    "KB for the quantity (quantity required): own values, cited values and model inputs, grouped in that order. "
                    "qualifiers filter values exactly (e.g. {\"level\": \"50%\"}; a value without that qualifier is excluded and "
                    "listed). A species qualifier keeps values of that species; an own value with no species takes its run's "
                    "reactant A (marked species_filled); a value whose species is a film material is excluded. Values whose unit "
                    "does not fit the quantity's dimension are rejected and listed. normalize applies ontology transforms to "
                    "curves (normalize_thickness: thickness over the curve's plateau; x_over_width: distance over the sample's "
                    "feature width) and says which reference was used.",
     "input_schema": {"type": "object", "properties": {
         "sample_ids": dict(_STR_LIST, description="sample ids from find_samples (any unit id works); omit to search the whole KB"),
         "quantity": {"type": "string", "description": "a quantity id from resolve; values and curves of this quantity only"},
         "qualifiers": {"type": "object", "additionalProperties": {"type": "string"}},
         "include": {"type": "array", "items": {"type": "string", "enum": ["values", "curves", "images"]},
                     "description": "default all three"},
         "normalize": {"type": "array", "items": {"type": "string", "enum": ["normalize_thickness", "x_over_width"]}},
         "methods": dict(_STR_LIST, description="optional: keep only images taken with these methods"),
         "papers": dict(_STR_LIST, description="optional: paper keys (whole-KB search)")}}},
    {"name": "compare",
     "description": "Compare the conditions of samples: for every recorded condition, same (one value), different (the value per "
                    "sample), or recorded for some samples only; each value as 'value [fact_id] (where from)'. Also the conflicts "
                    "per sample and the comparison sets of the KB that contain these samples (series, grids, replicates, and "
                    "figure series), with the members not in your list.",
     "input_schema": {"type": "object", "properties": {"sample_ids": _STR_LIST}, "required": ["sample_ids"]}},
    {"name": "claims",
     "description": "Claims the papers make, filtered by cause and/or effect concept ids (as from resolve), papers and relation: "
                    "cause, relation (increases, decreases, limits, causes, no_effect, ...), effect, stance (asserted, hedged), "
                    "the statement, and the records each claim rests on, resolved to their samples and the conditions that "
                    "differ among those samples.",
     "input_schema": {"type": "object", "properties": {
         "cause": dict(_STR_LIST, description="cause concept ids"), "effect": dict(_STR_LIST, description="effect concept ids"),
         "papers": _STR_LIST, "relation": _STR_LIST}}},
    {"name": "trace_citation",
     "description": "For a cited value (how obtained: cited): find the cited paper among the KB's 13 papers by its first author "
                    "and year in the citing text; if found, that paper's own values of the quantity, whether the value matches, "
                    "and their recorded conditions next to the cited value's; else 'not found'.",
     "input_schema": {"type": "object", "properties": {"fact_id": {"type": "string"}}, "required": ["fact_id"]}},
]


OPENAI_TOOLS = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
                for t in TOOL_SCHEMAS]


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _sha(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _git():
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip()
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=HERE, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", str(T.KBDIR), str(T.ONTOLOGY)], cwd=HERE,
                               capture_output=True, text=True).stdout.strip()
        return {"commit": head, "branch": branch, "kb_or_ontology_modified": bool(dirty)}
    except OSError:
        return {}


def cost(usage, model):
    """Estimated dollars of one response's normalized usage (PRICES); None for a model without a price."""
    p, u = PRICES.get(model), usage or {}
    if not p:
        return None
    return round((u.get("input_tokens", 0) * p["input"] + u.get("cache_creation_input_tokens", 0) * p["cache_write"]
                  + u.get("cache_read_input_tokens", 0) * p["cache_read"] + u.get("output_tokens", 0) * p["output"]) / 1e6, 6)


# ------------------------------------------------------------------------------------------------------------ providers
class AnthropicProvider:
    """Claude through the anthropic SDK: beta streaming messages, adaptive thinking (summarized), prompt caching, fallback."""
    name, key_var = "anthropic", "ANTHROPIC_API_KEY"

    def __init__(self, model, effort=None, client=None):
        import anthropic
        self.model, self.effort = model, effort or EFFORT["anthropic"]
        self.client = client or anthropic.Anthropic()
        self.sdk = f"anthropic {getattr(anthropic, '__version__', '')}"

    def user(self, text):
        return [{"role": "user", "content": text}]

    def request(self, system, messages, emit):
        params = dict(model=self.model, max_tokens=MAX_TOKENS, system=system, tools=TOOL_SCHEMAS, messages=messages,
                      thinking={"type": "adaptive", "display": "summarized"}, output_config={"effort": self.effort},
                      cache_control={"type": "ephemeral"}, betas=[FALLBACK_BETA], fallbacks="default")
        with self.client.beta.messages.stream(**params) as stream:
            for ev in stream:
                if ev.type == "content_block_start" and getattr(ev.content_block, "type", "") == "tool_use":
                    emit("tool_start", {"name": ev.content_block.name})
                elif ev.type == "content_block_delta":
                    if ev.delta.type == "text_delta":
                        emit("text", {"text": ev.delta.text})
                    elif ev.delta.type == "thinking_delta":
                        emit("thinking", {"text": ev.delta.thinking})
            resp = stream.get_final_message()
        raw = resp.usage.to_dict() if resp.usage else {}
        out = {"text": "", "thinking": [], "tool_calls": [], "model": resp.model, "request_id": getattr(resp, "_request_id", None),
               "stop_raw": resp.stop_reason, "stop": resp.stop_reason, "usage_raw": raw,
               "usage": {k: raw.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")},
               "fallback_ran": resp.model != self.model or any(b.type == "fallback" for b in resp.content),
               "message": {"role": "assistant", "content": resp.content}}
        for b in resp.content:
            if b.type == "thinking":
                out["thinking"].append(b.thinking)
            elif b.type == "text":
                out["text"] += b.text
            elif b.type == "tool_use":
                out["tool_calls"].append({"id": b.id, "name": b.name, "input": b.input})
        return out

    def tool_results(self, results):
        return [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": r["id"], "content": r["content"],
                                              **({"is_error": True} if r["is_error"] else {})} for r in results]}]


class DeepSeekProvider:
    """DeepSeek through the openai SDK (OpenAI-compatible chat completions): streamed, thinking on, tools as functions."""
    name, key_var = "deepseek", "DEEPSEEK_API_KEY"
    STOP = {"stop": "end_turn", "tool_calls": "tool_use", "length": "max_tokens", "content_filter": "refusal"}

    def __init__(self, model, effort=None, client=None):
        import openai
        self.model, self.effort = model, effort or EFFORT["deepseek"]
        self.client = client or openai.OpenAI(api_key=os.environ.get(self.key_var), base_url=DEEPSEEK_URL)
        self.sdk = f"openai {openai.__version__}"

    def user(self, text):
        return [{"role": "user", "content": text}]

    def request(self, system, messages, emit):
        stream = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "system", "content": system}] + messages, tools=OPENAI_TOOLS, stream=True,
            stream_options={"include_usage": True}, max_tokens=MAX_TOKENS, reasoning_effort=self.effort,
            extra_body={"thinking": {"type": "enabled"}})
        text, reasoning, calls, finish, raw, model, rid = [], [], {}, None, {}, self.model, None
        for ch in stream:
            model, rid = ch.model or model, ch.id or rid
            if ch.usage:
                raw = ch.usage.model_dump()
            for c in ch.choices:
                d = c.delta
                if d.content:
                    text.append(d.content)
                    emit("text", {"text": d.content})
                rc = getattr(d, "reasoning_content", None)
                if rc:
                    reasoning.append(rc)
                    emit("thinking", {"text": rc})
                for tc in d.tool_calls or []:
                    x = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    x["id"] = tc.id or x["id"]
                    if tc.function and tc.function.name:
                        if not x["name"]:
                            emit("tool_start", {"name": tc.function.name})
                        x["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        x["arguments"] += tc.function.arguments
                finish = c.finish_reason or finish
        tool_calls = []
        for i in sorted(calls):
            x = calls[i]
            try:
                args, err = json.loads(x["arguments"] or "{}"), None
            except ValueError as e:
                args, err = {}, f"arguments are not valid JSON ({e}): {x['arguments'][:300]}"
            tool_calls.append({"id": x["id"], "name": x["name"], "input": args, **({"parse_error": err} if err else {})})
        msg = {"role": "assistant", "content": "".join(text) or None, "reasoning_content": "".join(reasoning)}
        if calls:
            msg["tool_calls"] = [{"id": calls[i]["id"], "type": "function",
                                  "function": {"name": calls[i]["name"], "arguments": calls[i]["arguments"]}} for i in sorted(calls)]
        det = raw.get("completion_tokens_details") or {}
        hit = raw.get("prompt_cache_hit_tokens", (raw.get("prompt_tokens_details") or {}).get("cached_tokens", 0)) or 0
        usage = {"input_tokens": raw.get("prompt_cache_miss_tokens", (raw.get("prompt_tokens", 0) or 0) - hit) or 0,
                 "cache_creation_input_tokens": 0, "cache_read_input_tokens": hit, "output_tokens": raw.get("completion_tokens", 0) or 0,
                 "reasoning_tokens": det.get("reasoning_tokens") or 0}
        return {"text": "".join(text), "thinking": ["".join(reasoning)] if reasoning else [], "tool_calls": tool_calls, "model": model,
                "request_id": rid, "stop_raw": finish, "stop": self.STOP.get(finish, finish), "usage_raw": raw, "usage": usage,
                "fallback_ran": False, "message": msg}

    def tool_results(self, results):
        return [{"role": "tool", "tool_call_id": r["id"], "content": r["content"]} for r in results]


PROVIDERS = {"anthropic": AnthropicProvider, "deepseek": DeepSeekProvider}


# ------------------------------------------------------------------------------------------------------------ the conversation
class Conversation:
    """One conversation: questions and follow-ups, the model's turns, the tool calls and their results, all logged."""

    def __init__(self, case=None, mode="batch", model=None, effort=None, runs_dir=RUNS, client=None, origin="cli"):
        env_file = load_env()
        provider, model_id = resolve_model(model)
        self.provider = PROVIDERS[provider](model_id, effort, client)
        self.model, self.mode = model_id, mode
        self.system = SYSTEM.format(papers=paper_list(), max_calls=MAX_TOOL_CALLS, mode=MODES[mode])
        self.messages = []
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = Path(runs_dir) / f"{case or 'chat'}_{ts}.json"
        self.log = {"case": case, "mode": mode, "origin": origin, "provider": provider, "model": model_id, "effort": self.provider.effort,
                    "thinking": "adaptive, summarized" if provider == "anthropic" else "enabled (reasoning_content)",
                    "max_tool_calls": MAX_TOOL_CALLS, "started": _now(), "recipe_source": T.RECIPE_SOURCE, "git": _git(),
                    "sdk": self.provider.sdk, "env_file": env_file, "system_prompt": self.system, "system_sha": _sha(self.system),
                    "tools_sha": _sha(TOOL_SCHEMAS), "turns": [], "usage_total": {}, "cost_usd_estimate": 0.0,
                    "price_per_mtok": PRICES.get(model_id)}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.log, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def ask(self, text, emit=None):
        """One user question (or follow-up) to its final answer; returns the answer text ('' when there is none)."""
        emit = emit or (lambda kind, data: None)
        turn = {"user": text, "started": _now(), "steps": [], "final_answer": "", "tool_calls": 0, "requests": 0,
                "stop": None, "cap_reached": False}
        self.log["turns"].append(turn)
        self.messages += self.provider.user(text)
        self.save()
        n_calls = 0
        while True:
            turn["requests"] += 1
            t0 = time.time()
            try:
                reply = self.provider.request(self.system, self.messages, emit)
            except Exception as e:  # noqa: BLE001 - an API failure ends the question and is logged (key values scrubbed)
                turn["stop"] = scrub(f"error: {type(e).__name__}: {e}")
                emit("error", {"message": turn["stop"]})
                self.save()
                return ""
            step = {"type": "assistant", "request": turn["requests"], "ms": int((time.time() - t0) * 1000), "provider": self.provider.name,
                    "model": reply["model"], "fallback_ran": reply["fallback_ran"], "request_id": reply["request_id"],
                    "stop_reason": reply["stop"], "stop_raw": reply["stop_raw"], "usage": reply["usage"], "usage_raw": reply["usage_raw"],
                    "cost_usd_estimate": cost(reply["usage"], self.model), "thinking": reply["thinking"], "text": reply["text"],
                    "tool_calls": reply["tool_calls"]}
            turn["steps"].append(step)
            for k, v in reply["usage"].items():
                self.log["usage_total"][k] = self.log["usage_total"].get(k, 0) + v
            if step["cost_usd_estimate"] is not None:
                self.log["cost_usd_estimate"] = round(self.log["cost_usd_estimate"] + step["cost_usd_estimate"], 6)
            emit("assistant", step)
            self.messages.append(reply["message"])
            if reply["stop"] == "pause_turn":
                self.save()
                continue
            if reply["stop"] != "tool_use" or not reply["tool_calls"]:
                turn["stop"] = reply["stop"]
                turn["final_answer"] = reply["text"]
                turn["tool_calls"] = n_calls
                self.save()
                emit("final", {"text": reply["text"], "stop_reason": reply["stop"], "path": str(self.path)})
                return reply["text"]
            results = []
            for call in reply["tool_calls"]:
                t1 = time.time()
                if n_calls >= MAX_TOOL_CALLS:
                    turn["cap_reached"] = True
                    result = {"error": f"tool-call cap of {MAX_TOOL_CALLS} reached; answer now from the results you have"}
                elif call.get("parse_error"):
                    n_calls += 1
                    result = {"error": f"tool call not run: {call['parse_error']}"}
                else:
                    n_calls += 1
                    result = T.run_tool(call["name"], call["input"])
                sent = T.model_view(result)
                rec = {"type": "tool_result", "tool_use_id": call["id"], "name": call["name"], "input": call["input"],
                       "call": n_calls, "ms": int((time.time() - t1) * 1000), "error": result.get("error"), "result": result,
                       "sent": sent, "sent_chars": len(sent)}
                turn["steps"].append(rec)
                emit("tool_result", rec)
                results.append({"id": call["id"], "content": sent, "is_error": "error" in result})
            self.messages += self.provider.tool_results(results)
            turn["tool_calls"] = n_calls
            self.save()
            if turn["requests"] > MAX_TOOL_CALLS + EXTRA_REQUESTS:
                turn["stop"] = "request cap reached without an answer"
                self.save()
                emit("final", {"text": "", "stop_reason": turn["stop"], "path": str(self.path)})
                return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="?")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--case")
    ap.add_argument("--model", help="provider:model (default PSED_MODEL)")
    ap.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    a = ap.parse_args()

    def emit(kind, data):
        if kind == "text":
            print(data["text"], end="", flush=True)
        elif kind == "tool_result":
            print(f"\n  [{data['call']}] {data['name']}({json.dumps(data['input'], ensure_ascii=False)[:160]}) -> "
                  f"{'ERROR ' + data['error'] if data['error'] else str(data['sent_chars']) + ' chars'}", flush=True)
        elif kind == "error":
            print(f"\n{data['message']}", file=sys.stderr)

    conv = Conversation(case=a.case, mode="interactive" if a.interactive else "batch", model=a.model, effort=a.effort)
    print(f"{conv.log['provider']}:{conv.model} (effort {conv.provider.effort}), log {conv.path}")
    q = a.question
    while True:
        if not q:
            if not a.interactive:
                ap.error("give a question or --interactive")
            try:
                q = input("\n> ").strip()
            except EOFError:
                break
            if not q:
                break
        conv.ask(q, emit)
        c = conv.log["cost_usd_estimate"]
        print(f"\n\nlog: {conv.path}  (estimated ${c:.4f} so far)" if conv.log["price_per_mtok"] else f"\n\nlog: {conv.path}")
        if not a.interactive:
            break
        q = None


if __name__ == "__main__":
    main()
