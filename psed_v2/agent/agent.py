#!/usr/bin/env python3
"""The KB question-answering agent: a Claude model calls the deterministic tools of tools.py step by step until it answers.
Every request, tool call, tool result and the final answer is logged to agent/runs/<case>_<timestamp>.json.

    python3 -m psed_v2.agent.agent "question" [--case NAME] [--model ID] [--effort LEVEL]     # one question (batch mode)
    python3 -m psed_v2.agent.agent --interactive                                              # a conversation with follow-ups

Model: claude-sonnet-5-5 (pinned; --model overrides), adaptive thinking with summarized display, streamed. Key: ANTHROPIC_API_KEY.
Refusal fallback: the server-side default fallback (beta server-side-fallback-2026-07-01) is on; a turn served by another model is
logged (model, fallback_ran). Cap: MAX_TOOL_CALLS tool calls per question; past it every call returns an error asking for the answer.
Each tool result is sent to the model as tools.model_view(result) (curve points summarized, statements cut); the log keeps both the
full result and the text sent. Runs with conda env psed310 (anthropic SDK).
"""
import argparse, datetime, hashlib, json, subprocess, sys, time
from pathlib import Path

from . import tools as T

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
MAX_TOKENS = 64000
MAX_TOOL_CALLS = 15
EXTRA_REQUESTS = 2                     # requests allowed after the cap before the question ends without an answer
FALLBACK_BETA = "server-side-fallback-2026-07-01"
PRICE = {"input": 2.00, "cache_write": 2.50, "cache_read": 0.20, "output": 10.00}    # claude-sonnet-5-5, $ per million tokens


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
             "value": {"description": "a number, an id, or a list of ids"},
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


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _sha(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _git():
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", str(T.KBDIR), str(T.ONTOLOGY)], cwd=HERE,
                               capture_output=True, text=True).stdout.strip()
        return {"commit": head, "kb_or_ontology_modified": bool(dirty)}
    except OSError:
        return {}


def cost(usage):
    """Estimated dollars of one response's usage (PRICE; cache writes at the 5-minute rate)."""
    u = usage or {}
    return round((u.get("input_tokens", 0) * PRICE["input"] + u.get("cache_creation_input_tokens", 0) * PRICE["cache_write"]
                  + u.get("cache_read_input_tokens", 0) * PRICE["cache_read"] + u.get("output_tokens", 0) * PRICE["output"]) / 1e6, 6)


class Conversation:
    """One conversation: questions and follow-ups, the model's turns, the tool calls and their results, all logged."""

    def __init__(self, case=None, mode="batch", model=MODEL, effort=EFFORT, runs_dir=RUNS, client=None):
        import anthropic                                   # imported here so tools-only use needs no SDK
        self.client = client or anthropic.Anthropic()
        self.model, self.effort, self.mode = model, effort, mode
        self.system = SYSTEM.format(papers=paper_list(), max_calls=MAX_TOOL_CALLS, mode=MODES[mode])
        self.messages = []
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = Path(runs_dir) / f"{case or 'chat'}_{ts}.json"
        self.log = {"case": case, "mode": mode, "model": model, "effort": effort, "thinking": "adaptive, summarized",
                    "max_tool_calls": MAX_TOOL_CALLS, "started": _now(), "recipe_source": T.RECIPE_SOURCE, "git": _git(),
                    "sdk": getattr(anthropic, "__version__", ""), "system_prompt": self.system,
                    "system_sha": _sha(self.system), "tools_sha": _sha(TOOL_SCHEMAS), "turns": [], "usage_total": {},
                    "cost_usd_estimate": 0.0}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.log, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def _request(self, emit):
        params = dict(model=self.model, max_tokens=MAX_TOKENS, system=self.system, tools=TOOL_SCHEMAS, messages=self.messages,
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
            return stream.get_final_message()

    def ask(self, text, emit=None):
        """One user question (or follow-up) to its final answer; returns the answer text ('' when there is none)."""
        emit = emit or (lambda kind, data: None)
        turn = {"user": text, "started": _now(), "steps": [], "final_answer": "", "tool_calls": 0, "requests": 0,
                "stop": None, "cap_reached": False}
        self.log["turns"].append(turn)
        self.messages.append({"role": "user", "content": text})
        self.save()
        n_calls = 0
        while True:
            turn["requests"] += 1
            t0 = time.time()
            try:
                resp = self._request(emit)
            except Exception as e:  # noqa: BLE001 - an API failure ends the question and is logged
                turn["stop"] = f"error: {type(e).__name__}: {e}"
                emit("error", {"message": turn["stop"]})
                self.save()
                return ""
            usage = resp.usage.to_dict() if resp.usage else {}
            step = {"type": "assistant", "request": turn["requests"], "ms": int((time.time() - t0) * 1000), "model": resp.model,
                    "fallback_ran": resp.model != self.model or any(b.type == "fallback" for b in resp.content),
                    "request_id": getattr(resp, "_request_id", None), "stop_reason": resp.stop_reason, "usage": usage,
                    "cost_usd_estimate": cost(usage), "thinking": [], "text": "", "tool_calls": []}
            for b in resp.content:
                if b.type == "thinking":
                    step["thinking"].append(b.thinking)
                elif b.type == "text":
                    step["text"] += b.text
                elif b.type == "tool_use":
                    step["tool_calls"].append({"id": b.id, "name": b.name, "input": b.input})
            turn["steps"].append(step)
            for k, v in usage.items():
                if isinstance(v, (int, float)):
                    self.log["usage_total"][k] = self.log["usage_total"].get(k, 0) + v
            self.log["cost_usd_estimate"] = round(self.log["cost_usd_estimate"] + step["cost_usd_estimate"], 6)
            emit("assistant", step)
            self.messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "pause_turn":
                self.save()
                continue
            if resp.stop_reason != "tool_use" or not step["tool_calls"]:
                turn["stop"] = resp.stop_reason
                turn["final_answer"] = step["text"]
                turn["tool_calls"] = n_calls
                self.save()
                emit("final", {"text": step["text"], "stop_reason": resp.stop_reason, "path": str(self.path)})
                return step["text"]
            results = []
            for call in step["tool_calls"]:
                t1 = time.time()
                if n_calls >= MAX_TOOL_CALLS:
                    turn["cap_reached"] = True
                    result = {"error": f"tool-call cap of {MAX_TOOL_CALLS} reached; answer now from the results you have"}
                else:
                    n_calls += 1
                    result = T.run_tool(call["name"], call["input"])
                sent = T.model_view(result)
                rec = {"type": "tool_result", "tool_use_id": call["id"], "name": call["name"], "input": call["input"],
                       "call": n_calls, "ms": int((time.time() - t1) * 1000), "error": result.get("error"), "result": result,
                       "sent": sent, "sent_chars": len(sent)}
                turn["steps"].append(rec)
                emit("tool_result", rec)
                results.append({"type": "tool_result", "tool_use_id": call["id"], "content": sent,
                                **({"is_error": True} if "error" in result else {})})
            self.messages.append({"role": "user", "content": results})
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
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--effort", default=EFFORT, choices=["low", "medium", "high", "xhigh", "max"])
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
        print(f"\n\nlog: {conv.path}  (estimated ${conv.log['cost_usd_estimate']:.4f} so far)")
        if not a.interactive:
            break
        q = None


if __name__ == "__main__":
    main()
