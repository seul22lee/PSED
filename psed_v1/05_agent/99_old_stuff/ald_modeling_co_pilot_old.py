import os,re,json
from dataclasses import dataclass
from pathlib import Path
from typing import List,Dict,Any,Optional
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


# --------------------- Logging Mixin ---------------------
class AgentLoggerMixin:
    def log(self,agent_name,filename,data):
        out=Path("./outputs/agent_logs");out.mkdir(parents=True,exist_ok=True)
        fp=out/f"{agent_name}__{filename}.json"
        with open(fp,"w",encoding="utf8") as f:json.dump(data,f,indent=2,ensure_ascii=False)

# --------------------- Data Models -----------------------
@dataclass
class Equation: number:Optional[str];raw_text:str;normalized_text:str;context:str
@dataclass
class Variable: name:str;definition:Optional[str]=None;units:Optional[str]=None;role:Optional[str]=None;source_equations:Optional[List[str]]=None
@dataclass
class Relation: source:str;target:str;relation_type:str;description:str
@dataclass
class KnowledgeGraph: nodes:List[Dict[str,Any]];edges:List[Dict[str,Any]]

class Agent: 
    def run(self,ctx): raise NotImplementedError

# --------------------- Agents ----------------------------
class PDFLoaderAgent(Agent, AgentLoggerMixin):
    def __init__(self,pdf_dir):
        self.pdf_dir=Path(pdf_dir)
        Path("./outputs/txt").mkdir(parents=True,exist_ok=True)

    def extract_two_cols(self,pdf):
        import fitz
        doc=fitz.open(pdf); out=[]
        for pg in doc:
            mid=pg.rect.width/2; L=[]; R=[]
            for x0,y0,x1,y1,t,*_ in pg.get_text("blocks"):
                if not t.strip(): continue
                (L if x1<mid else R if x0>mid else (L if x0<mid else R)).append((y0,t))
            L.sort(key=lambda x:x[0]); R.sort(key=lambda x:x[0])
            out.append("\n".join(t for _,t in L)+"\n"+ "\n".join(t for _,t in R))
        doc.close()
        return "\n".join(out)

    def run(self,ctx):
        texts={}
        for f in self.pdf_dir.glob("*.pdf"):
            tx=self.extract_two_cols(f)
            texts[f.name]=tx
            open(f"outputs/txt/{f.stem}.txt","w",encoding="utf8").write(tx)
            self.log("1_PDFLoader",f.name,{"text_excerpt":tx[:8000]})
        ctx["pdf_texts"]=texts
        return ctx

class EquationBlockExtractionAgent(Agent, AgentLoggerMixin):

    # 매우 느슨한 수식 판단
    def looks_mathish(self, s):
        if len(s.strip()) == 0:
            return False
        if len(s) < 80:   # 긴 문장은 제외
            return True
        if any(x in s for x in ["¼", "", "−", "=", "/", "*", "^", "√", "∂", "ln", "exp"]):
            return True
        return False

    def extract_blocks(self, text):
        lines = text.splitlines()
        blocks = []

        for i, ln in enumerate(lines):
            m = re.fullmatch(r"\((\d+)\)", ln.strip())
            if not m:
                continue

            eq_num = m.group(1)

            # --- 위쪽 수식 라인 수집 ---
            up = []
            k = i - 1
            while k >= 0 and self.looks_mathish(lines[k]):
                up.append(lines[k].strip())
                k -= 1
            up.reverse()

            # --- 아래쪽 수식 라인 수집 ---
            down = []
            k = i + 1
            while k < len(lines) and self.looks_mathish(lines[k]):
                down.append(lines[k].strip())
                k += 1

            block = up + down
            raw = "\n".join(block)

            blocks.append({
                "number": eq_num,
                "raw_text": raw
            })

        return blocks

    def run(self, ctx):
        out = {}
        for fn, tx in ctx["pdf_texts"].items():
            b = self.extract_blocks(tx)
            self.log("2_EquationBlocks", fn, b)
            out[fn] = b
        ctx["equation_blocks"] = out
        return ctx


class EquationReconstructionAgent(Agent, AgentLoggerMixin):
    def __init__(self):
        super().__init__()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def reconstruct(self, raw_block: str):

        prompt = f"""
    You are an expert in mathematical equation reconstruction.

    The following text block was extracted from a scientific PDF.
    It may be corrupted, split across lines, contain encoding errors (¼, ﬃ, , −, etc.),
    or include broken fractions or partial expressions.

    Your tasks:

    1. Extract only the mathematical content, ignore sentences or comments.
    2. Reconstruct ONE complete mathematical equation, merging broken lines.
    3. Repair corrupted characters (¼ → =, /− → -, ﬃ → ffi, etc.)
    4. Recover structural forms:
    - fractions → \\frac{{}}{{}}
    - exponents → ^{{ }}
    - subscripts → _{{ }}
    - roots → \\sqrt{{ }}
    - logs, ln, exp, etc.
    5. Remove the equation number like (15) if present.
    6. Ensure the final answer is valid LaTeX.
    7. Output ONLY the LaTeX equation. No explanation.

    Raw block:
    --------------------------------
    {raw_block}
    --------------------------------

    Return only the LaTeX equation.
    """
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0
        )
        return resp.choices[0].message.content.strip()



    def run(self, ctx):
        out = {}
        for fn, blocks in ctx["equation_blocks"].items():
            eqs = []
            for blk in blocks:
                num  = blk["number"]
                raw  = blk["raw_text"]
                latex = self.reconstruct(raw)

                eqs.append(Equation(
                    number=num,
                    raw_text=raw,
                    normalized_text=latex,
                    context=raw
                ))

            out[fn] = eqs
            self.log("3_Equation_Reconstructed_LaTeX", fn, [e.__dict__ for e in eqs])

        ctx["equations"] = out
        return ctx


import re

class VariableDefinitionAgent(Agent, AgentLoggerMixin):
    vp = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\b")

    def parse_nomenclature(self, text):
        lines = [l.strip() for l in text.splitlines()]
        try:
            i = next(i for i,l in enumerate(lines) if l.upper()=="NOMENCLATURE")
        except StopIteration:
            return {}

        entries, var, desc, units = {}, None, [], None

        def flush():
            nonlocal var, desc, units
            if var:
                entries[var] = {
                    "definition": " ".join(desc).strip() or None,
                    "units": units
                }
            var, desc, units = None, [], None

        for s in lines[i+1:]:
            if not s: continue
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", s):
                flush(); var = s; continue
            if re.fullmatch(r"\([^()]+\)", s):
                units = s[1:-1]; continue
            if var:
                desc.append(s)

        flush()
        return entries

    def run(self, ctx):
        out = {}
        for fn, eqs in ctx["equations"].items():
            nom = self.parse_nomenclature(ctx["pdf_texts"][fn])
            vm = {}

            for e in eqs:
                for tok in self.vp.findall(e.normalized_text):
                    if tok not in nom:     # <<< ★★★★★ 핵심 추가 부분
                        continue           # NOMENCLATURE에 없는 토큰 제거
                    if len(tok) > 20:
                        continue

                    v = vm.get(tok)
                    if not v:
                        info = nom.get(tok, {})
                        vm[tok] = Variable(
                            name=tok,
                            definition=info.get("definition"),
                            units=info.get("units"),
                            role=None,
                            source_equations=[e.number] if e.number else []
                        )
                    else:
                        if e.number and e.number not in v.source_equations:
                            v.source_equations.append(e.number)

            out[fn] = list(vm.values())
            self.log("3_VariableExtraction", fn, [v.__dict__ for v in out[fn]])

        ctx["variables"] = out
        return ctx


class RelationReasoningAgent(Agent, AgentLoggerMixin):

    def __init__(self):
        super().__init__()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def build_prompt(self, vars, eqs, text):
        var_list = "\n".join(f"- {v.name}: {v.definition or ''}" for v in vars)
        eq_list = "\n".join(f"({e.number}) {e.normalized_text}" for e in eqs)

        return f"""
You are an expert scientific reasoning model.

Your task is to infer **variable-to-variable relationships** from:

1. Variables and their definitions
2. Normalized equations
3. Scientific context text from the paper

Extract only meaningful relations between variables.

---

### Variables
{var_list}

### Equations
{eq_list}

### Context Text
{text}

---

### REQUIRED OUTPUT FORMAT
Return a JSON list of objects.  
Each object must be:

{{
  "x": "independent_variable",
  "y": "dependent_variable",
  "type": "<one of: eq_dependency, proportional, inverse, direct, qualitative, cooccurrence>",
  "evidence": "short text snippet or equation number"
}}

---

### RULES
- Only include relations between variables listed above.
- Use equations to infer explicit dependencies.
- Use text for qualitative relations.
- If the form is y = f(x): **x → y** with type = "eq_dependency".
- If y ∝ x: type = "proportional".
- If y increases with x: type = "direct".
- If y decreases with x: type = "inverse".
- If variables co-occur but relation is unclear: type = "cooccurrence".
- Keep JSON compact and machine-parseable.

Produce ONLY the JSON list. No explanations.
"""

    # -------------------------------
    # SAFE JSON PARSER
    # -------------------------------
    def _safe_json_list(self, text: str):
        """LLM output에서 JSON list만 추출하고 parse."""
        if not text or not text.strip():
            return []

        t = text.strip()

        # ```json ... ``` 제거
        if t.startswith("```"):
            t = t.strip("`").strip()
            if t.lower().startswith("json"):
                t = t[4:].strip()

        # [ ... ] 부분만 추출
        m = re.search(r"\[.*\]", t, re.DOTALL)
        if m:
            t = m.group(0)

        # JSON parsing
        try:
            data = json.loads(t)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def parse_llm_response(self, response: str):
        items = self._safe_json_list(response)
        relations = []

        for obj in items:
            try:
                relations.append(
                    Relation(
                        x=obj["x"],
                        y=obj["y"],
                        relation_type=obj["type"],
                        description=obj.get("evidence")
                    )
                )
            except Exception:
                continue

        return relations

    def run(self, ctx):
        out = {}

        for fn in ctx["equations"]:
            vars = ctx["variables"][fn]
            eqs  = ctx["equations"][fn]
            text = ctx["pdf_texts"][fn]

            prompt = self.build_prompt(vars, eqs, text)

            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )

            raw = resp.choices[0].message.content
            relations = self.parse_llm_response(raw)

            out[fn] = relations
            self.log("4_RelationReasoning", fn,
                     [r.__dict__ for r in relations])

        ctx["relations"] = out
        return ctx



class KnowledgeGraphAgent(Agent, AgentLoggerMixin):
    def run(self, ctx):
        out = {}
        for fn in ctx["relations"]:
            rels = ctx["relations"][fn]
            nodes = set()
            edges = []

            for r in rels:
                nodes.add(r.x)
                nodes.add(r.y)
                edges.append({
                    "source": r.x,
                    "target": r.y,
                    "type": r.type,
                    "evidence": r.evidence
                })

            kg = KnowledgeGraph(
                nodes=[{"id": n} for n in nodes],
                edges=edges
            )

            out[fn] = kg
            self.log("5_KnowledgeGraph", fn, {"nodes": kg.nodes, "edges": kg.edges})

        ctx["knowledge_graphs"] = out
        return ctx



class ConsistencyCheckerAgent(Agent,AgentLoggerMixin):
    def run(self,ctx):
        out={}
        for fn,g in ctx["knowledge_graphs"].items():
            ids={n["id"] for n in g.nodes};iss=[]
            if len(ids)!=len(g.nodes):iss.append("duplicate node IDs")
            for e in g.edges:
                if e["source"] not in ids or e["target"] not in ids:iss.append("dangling edge")
            out[fn]=iss
            self.log("6_Consistency",fn,iss)
        ctx["consistency"]=out;return ctx

class InterpreterAgent(Agent,AgentLoggerMixin):
    def run(self,ctx):
        out={}
        for fn in ctx["knowledge_graphs"].keys():
            eqs,vs=ctx["equations"][fn],ctx["variables"][fn]
            s=[f"File: {fn}",f"{len(eqs)} equations, {len(vs)} variables."]
            if eqs:
                s.append("Examples:"); 
                for e in eqs[:3]:s.append(f"- ({e.number}) {e.normalized_text}")
            if vs:
                s.append("Vars:")
                for v in vs[:5]:s.append(f"- {v.name}: {v.definition or 'N/A'}")
            text="\n".join(s);out[fn]=text
            self.log("7_Interpreter",fn,{"summary":text})
        ctx["interpretations"]=out;return ctx

# ---------------------- Pipeline -------------------------
class ALDModelingCoPilot:
    def __init__(self, pdf_dir):
        self.agents = [
            PDFLoaderAgent(pdf_dir),
            EquationBlockExtractionAgent(),
            EquationReconstructionAgent(),
            VariableDefinitionAgent(),
            RelationReasoningAgent(),
            KnowledgeGraphAgent(), 
        ]

    def run(self):
        ctx = {}
        for a in self.agents:
            ctx = a.run(ctx)
        return ctx


# ---------------------- Main -----------------------------
if __name__ == "__main__":
    pdf_dir = "/home/ftk3187/github/PSED/aldmodeling_agent/pdfs"

    cop = ALDModelingCoPilot(pdf_dir)
    ctx = cop.run()

    out = Path("./outputs")
    out.mkdir(exist_ok=True)

    for fn, g in ctx["knowledge_graphs"].items():
        with open(out / f"{fn}.kg.json", "w", encoding="utf8") as f:
            json.dump(
                {"nodes": g.nodes, "edges": g.edges},
                f,
                indent=2,
                ensure_ascii=False
            )



    for fn, t in ctx.get("interpretations", {}).items():
        print("====", fn, "====")
        print(t)
