#!/usr/bin/env python3
"""One adapter per model vendor, each on an official Python SDK (conda env psed310: anthropic, openai, google-genai); xAI and
DeepSeek through the OpenAI SDK pointed at https://api.x.ai/v1 and https://api.deepseek.com, which their documentation describes
as their OpenAI-compatible endpoints.

Only what every vendor offers is used: a system prompt, messages, tool (function) calling and token counts. No citation, document,
search or file feature; prompt caching only where it changes nothing but cost: Anthropic's cache marks on the system prompt, the
tool list and the newest message; OpenAI's prompt_cache_key and xAI's x-grok-conv-id (one per session, so its turns reach the same
cache); Google and DeepSeek cache on their own. A rate-limit, quota or overload error is retried with exponential backoff, at most 5 tries in all;
the retries are counted in Turn.retries. Every model runs with its default settings; Anthropic requires max_tokens,
set to MAX_TOKENS, a cost guard only: the answer length is asked for in the prompt (P37), never cut by a token cap.

    s = session("anthropic:claude-opus-5-5", system, tools)    # tools: [dict(name, description, parameters=JSON schema)] or None
    t = s.send("question")                                     # -> Turn(text, calls=[dict(id, name, arguments)], usage)
    t = s.send(results=[dict(id, name, content, error)])      # the results of t.calls; repeat while t.calls

LLM API calls are allowed only here, in ask.py and in serve.py; extraction stays free of them.
"""
import json, os, time, uuid
from dataclasses import dataclass, field
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"
KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY", "xai": "XAI_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}
BASE_URL = {"xai": "https://api.x.ai/v1", "deepseek": "https://api.deepseek.com"}
TRIES, BACKOFF = 5, 2.0
DEFAULT_MODEL = "anthropic:claude-opus-5-5"
MAX_TOKENS = 16000


def load_env():
    """Read psed_v2/.env into os.environ (keys are never printed or logged)."""
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip() and not os.environ.get(k.strip()):
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def available():
    """The vendors whose key is set."""
    load_env()
    return [v for v, k in KEYS.items() if os.environ.get(k)]


def default_model():
    load_env()
    return os.environ.get("PSED_MODEL") or DEFAULT_MODEL


@dataclass
class Turn:
    text: str = ""
    calls: list = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    retries: int = 0


def retryable(e):
    """A rate-limit, quota or overload error (HTTP 429, 503, 529 or the SDK's class for it)."""
    code = getattr(e, "status_code", None) or getattr(e, "code", None) or getattr(getattr(e, "response", None), "status_code", None)
    name = type(e).__name__
    return code in (429, 503, 529) or name in ("RateLimitError", "OverloadedError", "ResourceExhausted", "InternalServerError") and code in (None, 429, 503, 529) \
        or "RESOURCE_EXHAUSTED" in str(e)


def with_retries(fn):
    """fn() with exponential backoff on retryable errors: (result, retries)."""
    for k in range(TRIES):
        try:
            return fn(), k
        except Exception as e:
            if k == TRIES - 1 or not retryable(e):
                raise
            time.sleep(BACKOFF * 2 ** k)


def session(model, system, tools=None):
    vendor, name = model.split(":", 1)
    if vendor not in KEYS:
        raise ValueError(f"unknown vendor {vendor}")
    load_env()
    if not os.environ.get(KEYS[vendor]):
        raise RuntimeError(f"{vendor} is unavailable: {KEYS[vendor]} is empty in .env")
    if vendor in BASE_URL:
        return OpenAISession(name, system, tools, key=os.environ[KEYS[vendor]], vendor=vendor)
    return {"anthropic": AnthropicSession, "openai": OpenAISession, "google": GoogleSession}[vendor](name, system, tools)


class AnthropicSession:
    def __init__(self, model, system, tools):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ[KEYS["anthropic"]], max_retries=0)
        self.model, self.messages = model, []
        self.system = [dict(type="text", text=system, cache_control=dict(type="ephemeral"))]
        self.tools = [dict(name=t["name"], description=t["description"], input_schema=t["parameters"]) for t in tools or []]
        if self.tools:
            self.tools[-1]["cache_control"] = dict(type="ephemeral")

    def send(self, text=None, results=None):
        if text is not None:
            self.messages.append(dict(role="user", content=text))
        else:
            self.messages.append(dict(role="user", content=[dict(type="tool_result", tool_use_id=r["id"], content=r["content"], is_error=bool(r.get("error")))
                                                           for r in results]))
        for m in self.messages:                                             # one cache mark, on the newest message (cost only)
            if m["role"] == "user" and isinstance(m["content"], list):
                for b in m["content"]:
                    b.pop("cache_control", None)
        last = self.messages[-1]
        if isinstance(last["content"], str):
            last["content"] = [dict(type="text", text=last["content"])]
        last["content"][-1]["cache_control"] = dict(type="ephemeral")
        kw = dict(model=self.model, max_tokens=MAX_TOKENS, system=self.system, messages=self.messages)
        if self.tools:
            kw["tools"] = self.tools
        r, n = with_retries(lambda: self.client.messages.create(**kw))
        self.messages.append(dict(role="assistant", content=[b.model_dump(exclude_none=True) for b in r.content]))
        u = r.usage
        cr, cw = getattr(u, "cache_read_input_tokens", 0) or 0, getattr(u, "cache_creation_input_tokens", 0) or 0
        return Turn(text="".join(b.text for b in r.content if b.type == "text"),
                    calls=[dict(id=b.id, name=b.name, arguments=b.input) for b in r.content if b.type == "tool_use"],
                    usage=dict(input=u.input_tokens + cr + cw, output=u.output_tokens, cache_read=cr, cache_write=cw), retries=n)


class OpenAISession:
    """OpenAI, and xAI and DeepSeek through the same SDK at their base URLs (Chat Completions with function calling)."""
    def __init__(self, model, system, tools, key=None, vendor="openai"):
        import openai
        sid = uuid.uuid4().hex
        self.vendor = vendor
        self.client = openai.OpenAI(api_key=key or os.environ[KEYS["openai"]], base_url=BASE_URL.get(vendor), max_retries=0, timeout=900,
                                    default_headers={"x-grok-conv-id": sid} if vendor == "xai" else None)
        self.model, self.sid, self.messages = model, sid, [dict(role="system", content=system)]
        self.tools = [dict(type="function", function=dict(name=t["name"], description=t["description"], parameters=t["parameters"])) for t in tools or []]

    def send(self, text=None, results=None):
        if text is not None:
            self.messages.append(dict(role="user", content=text))
        else:
            self.messages += [dict(role="tool", tool_call_id=r["id"], content=r["content"]) for r in results]
        kw = dict(model=self.model, messages=self.messages)
        if self.tools:
            kw["tools"] = self.tools
        if self.vendor == "openai":
            kw["prompt_cache_key"] = self.sid
        r, n = with_retries(lambda: self.client.chat.completions.create(**kw))
        m = r.choices[0].message
        self.messages.append(dict(role="assistant", content=m.content or "", **({"tool_calls": [c.model_dump(exclude_none=True) for c in m.tool_calls]} if m.tool_calls else {})))
        u = r.usage
        cr = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or getattr(u, "prompt_cache_hit_tokens", 0) or 0   # DeepSeek names it so
        rt = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", 0) or 0
        out = u.completion_tokens + (rt if rt and (u.total_tokens or 0) >= u.prompt_tokens + u.completion_tokens + rt else 0)   # reasoning counted once
        return Turn(text=m.content or "", calls=[dict(id=c.id, name=c.function.name, arguments=json.loads(c.function.arguments or "{}")) for c in m.tool_calls or []],
                    usage=dict(input=u.prompt_tokens, output=out, cache_read=cr, cache_write=0, reasoning=rt), retries=n)


def _open(schema):
    """A copy of a schema without additionalProperties, which Gemini's function declarations do not take (the tool layer still
    rejects unknown arguments)."""
    if isinstance(schema, dict):
        return {k: _open(v) for k, v in schema.items() if k != "additionalProperties"}
    if isinstance(schema, list):
        return [_open(v) for v in schema]
    return schema


class GoogleSession:
    def __init__(self, model, system, tools):
        from google import genai
        from google.genai import types
        self.types, self.client = types, genai.Client(api_key=os.environ[KEYS["google"]])
        self.model, self.contents = model, []
        decl = [types.FunctionDeclaration(name=t["name"], description=t["description"], parameters_json_schema=_open(t["parameters"])) for t in tools or []]
        self.config = types.GenerateContentConfig(system_instruction=system, tools=[types.Tool(function_declarations=decl)] if decl else None,
                                                  automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True) if decl else None)

    def send(self, text=None, results=None):
        T = self.types
        if text is not None:
            self.contents.append(T.Content(role="user", parts=[T.Part.from_text(text=text)]))
        else:
            self.contents.append(T.Content(role="user", parts=[T.Part.from_function_response(name=r["name"], response={"error" if r.get("error") else "result": r["content"]})
                                                               for r in results]))
        r, n_ = with_retries(lambda: self.client.models.generate_content(model=self.model, contents=self.contents, config=self.config))
        c = r.candidates[0].content if r.candidates and r.candidates[0].content else T.Content(role="model", parts=[])
        self.contents.append(c)
        parts = c.parts or []
        u = r.usage_metadata
        n = lambda x: getattr(u, x, 0) or 0
        return Turn(text="".join(p.text for p in parts if p.text and not getattr(p, "thought", False)),
                    calls=[dict(id=p.function_call.id or f"call{i}", name=p.function_call.name, arguments=dict(p.function_call.args or {}))
                           for i, p in enumerate(parts) if p.function_call],
                    usage=dict(input=n("prompt_token_count"), output=n("candidates_token_count") + n("thoughts_token_count"),
                               cache_read=n("cached_content_token_count"), cache_write=0), retries=n_)
