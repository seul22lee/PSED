#!/usr/bin/env python3
"""One adapter per model vendor, each on the vendor's official Python SDK (conda env psed310: anthropic, openai, google-genai).

Only what every vendor offers is used: a system prompt, messages, tool (function) calling and token counts. No citation, document,
search or file feature; prompt caching only where it changes nothing but cost (Anthropic's cache marks on the system prompt and
the tool list; OpenAI and Google cache on their own). Every model runs with its default settings; Anthropic requires max_tokens,
set to MAX_TOKENS.

    s = session("anthropic:claude-opus-5-5", system, tools)    # tools: [dict(name, description, parameters=JSON schema)] or None
    t = s.send("question")                                     # -> Turn(text, calls=[dict(id, name, arguments)], usage)
    t = s.send(results=[dict(id, name, content, error)])      # the results of t.calls; repeat while t.calls

LLM API calls are allowed only here, in ask.py and in serve.py; extraction stays free of them.
"""
import json, os
from dataclasses import dataclass, field
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"
KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY"}
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


def session(model, system, tools=None):
    vendor, name = model.split(":", 1)
    if vendor not in KEYS:
        raise ValueError(f"unknown vendor {vendor}")
    load_env()
    if not os.environ.get(KEYS[vendor]):
        raise RuntimeError(f"{vendor} is unavailable: {KEYS[vendor]} is empty in .env")
    return {"anthropic": AnthropicSession, "openai": OpenAISession, "google": GoogleSession}[vendor](name, system, tools)


class AnthropicSession:
    def __init__(self, model, system, tools):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ[KEYS["anthropic"]], max_retries=4)
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
        r = self.client.messages.create(**kw)
        self.messages.append(dict(role="assistant", content=[b.model_dump(exclude_none=True) for b in r.content]))
        u = r.usage
        cr, cw = getattr(u, "cache_read_input_tokens", 0) or 0, getattr(u, "cache_creation_input_tokens", 0) or 0
        return Turn(text="".join(b.text for b in r.content if b.type == "text"),
                    calls=[dict(id=b.id, name=b.name, arguments=b.input) for b in r.content if b.type == "tool_use"],
                    usage=dict(input=u.input_tokens + cr + cw, output=u.output_tokens, cache_read=cr, cache_write=cw))


class OpenAISession:
    def __init__(self, model, system, tools):
        import openai
        self.client = openai.OpenAI(api_key=os.environ[KEYS["openai"]], max_retries=4)
        self.model, self.messages = model, [dict(role="system", content=system)]
        self.tools = [dict(type="function", function=dict(name=t["name"], description=t["description"], parameters=t["parameters"])) for t in tools or []]

    def send(self, text=None, results=None):
        if text is not None:
            self.messages.append(dict(role="user", content=text))
        else:
            self.messages += [dict(role="tool", tool_call_id=r["id"], content=r["content"]) for r in results]
        kw = dict(model=self.model, messages=self.messages)
        if self.tools:
            kw["tools"] = self.tools
        r = self.client.chat.completions.create(**kw)
        m = r.choices[0].message
        self.messages.append(m.model_dump(exclude_none=True))
        u = r.usage
        cr = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        return Turn(text=m.content or "", calls=[dict(id=c.id, name=c.function.name, arguments=json.loads(c.function.arguments or "{}")) for c in m.tool_calls or []],
                    usage=dict(input=u.prompt_tokens, output=u.completion_tokens, cache_read=cr, cache_write=0))


class GoogleSession:
    def __init__(self, model, system, tools):
        from google import genai
        from google.genai import types
        self.types, self.client = types, genai.Client(api_key=os.environ[KEYS["google"]])
        self.model, self.contents = model, []
        decl = [types.FunctionDeclaration(name=t["name"], description=t["description"], parameters_json_schema=t["parameters"]) for t in tools or []]
        self.config = types.GenerateContentConfig(system_instruction=system, tools=[types.Tool(function_declarations=decl)] if decl else None,
                                                  automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True) if decl else None)

    def send(self, text=None, results=None):
        T = self.types
        if text is not None:
            self.contents.append(T.Content(role="user", parts=[T.Part.from_text(text=text)]))
        else:
            self.contents.append(T.Content(role="user", parts=[T.Part.from_function_response(name=r["name"], response={"error" if r.get("error") else "result": r["content"]})
                                                               for r in results]))
        r = self.client.models.generate_content(model=self.model, contents=self.contents, config=self.config)
        c = r.candidates[0].content if r.candidates and r.candidates[0].content else T.Content(role="model", parts=[])
        self.contents.append(c)
        parts = c.parts or []
        u = r.usage_metadata
        n = lambda x: getattr(u, x, 0) or 0
        return Turn(text="".join(p.text for p in parts if p.text and not getattr(p, "thought", False)),
                    calls=[dict(id=p.function_call.id or f"call{i}", name=p.function_call.name, arguments=dict(p.function_call.args or {}))
                           for i, p in enumerate(parts) if p.function_call],
                    usage=dict(input=n("prompt_token_count"), output=n("candidates_token_count") + n("thoughts_token_count"),
                               cache_read=n("cached_content_token_count"), cache_write=0))
