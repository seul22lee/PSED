import os,re,json
from dataclasses import dataclass
from pathlib import Path
from typing import List,Dict,Any,Optional
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ===========================================================
# Minimal LLM Client for ALD CoPilot (text + JSON only)
# No vision, no embeddings
# ===========================================================
from openai import OpenAI
import json
import os
from dataclasses import asdict
import re

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
    
from typing import Optional
class EquationBlockExtractionAgent(Agent, AgentLoggerMixin):

    def is_equation_number(self, s: str) -> Optional[int]:
        """
        단독 라인으로 (number) 인 경우만 equation number로 인식
        """
        m = re.fullmatch(r"\((\d+)\)", s.strip())
        return int(m.group(1)) if m else None

    def looks_mathish(self, s: str) -> bool:
        """
        진짜 '수식'으로 보이는지 판단하는 강화된 기준
        텍스트는 최대한 배제한다.
        """
        s = s.strip()
        if not s:
            return False

        # equation-like symbols
        if any(sym in s for sym in ["=", "−", "-", "+", "/", "*", "^", "√", "∂"]):
            return True

        # LaTeX-like structures
        if "\\" in s or re.search(r"\\[A-Za-z]+", s):
            return True

        # variable + number mixtures (common in equations)
        if re.search(r"[A-Za-z]", s) and re.search(r"\d", s):
            return True

        # too long = likely paragraph text
        if len(s) > 80:
            return False

        # if it has few spaces and alpha-only patterns, could still be equation
        if len(s.split()) <= 4:
            return True

        return False

    def extract_blocks(self, text: str):
        lines = text.splitlines()
        n = len(lines)

        blocks = []

        for i, raw_ln in enumerate(lines):

            # -----------------------------
            # STEP 1: 찾은 라인이 equation number인가?
            # -----------------------------
            eq_num = self.is_equation_number(raw_ln)
            if eq_num is None:
                continue  # 단독 라인 (1) 형태 아니면 skip

            # -----------------------------
            # STEP 2: 위쪽 수식 수집
            # -----------------------------
            block_up = []
            k = i - 1

            while k >= 0:
                ln = lines[k].strip()

                # 빈 줄 → STOP
                if not ln:
                    break

                # 다른 equation 번호 발견 → STOP
                if self.is_equation_number(ln):
                    break

                # text이면 STOP
                if not self.looks_mathish(ln):
                    break

                block_up.append(ln)
                k -= 1

            block_up.reverse()  # 위쪽은 위→아래 순서로

            # -----------------------------
            # STEP 3: 아래쪽 수식 수집
            # -----------------------------
            block_down = []
            k = i + 1

            while k < n:
                ln = lines[k].strip()

                # 빈 줄 → STOP
                if not ln:
                    break

                # 다음 번호 등장 → STOP
                if self.is_equation_number(ln):
                    break

                # text면 STOP
                if not self.looks_mathish(ln):
                    break

                block_down.append(ln)
                k += 1

            # -----------------------------
            # STEP 4: 합치기
            # -----------------------------
            block = block_up + block_down
            raw = "\n".join(block).strip()

            if raw:
                blocks.append({
                    "number": str(eq_num),
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
    SYSTEM_PROMPT = """
You are an expert in mathematical equation reconstruction.

You receive raw corrupted equation blocks extracted from a scientific PDF.

Your tasks:
1. Extract ONLY the mathematical content (ignore sentences).
2. Reconstruct ONE complete mathematical equation from broken lines.
3. Fix corrupted characters: ¼ → = , ﬃ → ffi ,  → - , − → -
4. Restore forms:
   - \frac{}{}
   - superscripts ^{}
   - subscripts _{}
   - square roots \sqrt{}
   - exp(), ln(), logs
5. Merge multi-line math into a single LaTeX expression.
6. Remove equation number markers like “(15)”.
7. Output ONLY valid LaTeX. No explanation.
"""

    def __init__(self, llm):
        self.llm = llm


    # -------------------------------------------------------
    # 1) Sanity check: determines whether this is a REAL equation
    # -------------------------------------------------------
    def is_valid_equation(self, latex: str) -> bool:
        if not latex:
            return False

        s = latex.strip()

        # Too short → garbage
        if len(s) < 5:
            return False

        # LLM fallback garbage
        if s.lower().startswith("\\text"):
            return False
        if "nothing" in s.lower():
            return False
        if s.startswith("```"):
            return False

        # OCR corrupted '¼' means '='
        if "=" in s or "¼" in s:
            return True

        # Fraction means valid equation-like structure
        if "\\frac" in s:
            return True

        # Differential equations
        if "\\frac{d" in s or "\\frac{\\partial" in s:
            return True

        # Other algebraic math tags
        math_tokens = ["^", "_", "\\sqrt", "+", "-", "*", "/"]
        if any(tok in s for tok in math_tokens):
            return True

        # If not matching any math structure → not an equation
        return False


    # -------------------------------------------------------
    # 2) LLM reconstruction
    # -------------------------------------------------------
    def reconstruct(self, raw_block: str):
        user_prompt = f"""
Raw equation block:
-------------------------
{raw_block}
-------------------------

Reconstruct into ONE clean LaTeX equation.
Return ONLY the LaTeX expression.
"""

        latex = self.llm.complete(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return latex.strip()


    # -------------------------------------------------------
    # 3) Main run step : extract + filter + store
    # -------------------------------------------------------
    def run(self, ctx):
        out = {}

        for fn, blocks in ctx["equation_blocks"].items():
            eqs = []

            for blk in blocks:
                num = blk["number"]
                raw = blk["raw_text"]

                latex = self.reconstruct(raw)

                # -----------------------------
                # FILTER INVALID EQUATIONS
                # -----------------------------
                if not self.is_valid_equation(latex):
                    # Skip useless garbage
                    continue

                # -----------------------------
                # Append valid equation
                # -----------------------------
                eqs.append(
                    Equation(
                        number=num,
                        raw_text=raw,
                        normalized_text=latex,
                        context=raw,
                    )
                )

            out[fn] = eqs

            # Save log
            self.log(
                "3_Equation_Reconstructed_LaTeX",
                fn,
                [e.__dict__ for e in eqs],
            )

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


# ===========================================================
# Relation Reasoning Agent (JSON-safe)
# ===========================================================
class RelationReasoningAgent(Agent, AgentLoggerMixin):

    SYSTEM_PROMPT = """
You are an expert ALD scientific reasoning engine.

You will be given:
- Mathematical equations extracted from an ALD paper
- Variables and definitions
- Partial text of the paper (the main scientific explanation)

Your job:
Infer ALL scientifically meaningful relationships between variables and equations
using BOTH:
(1) Equation structure (formal mathematical dependencies)
AND
(2) Paper text (semantic causal statements, physical reasoning, ALD chemistry descriptions)

===========================================================
EQUATION-BASED REASONING RULES (STRICT)
===========================================================

1. For EVERY equation:

   LHS variable(s) = target(s)
   RHS variable(s) = source(s)

   You MUST produce at least one relation for every equation:
       (source → target)

2. If equation is differential (dY/dt, ∂Y/∂x):
   - relation_type = "causal"
   - equation governs Y
   - effect direction implied by signs

3. If equation is algebraic:
   - relation_type = "depends_on" or "derived_from"

4. “defines” if equation provides a direct definitional formula for a new variable.

5. “governs” if equation describes evolution, diffusion, transport, or rate.

6. Direction inference:
   - Positive terms → "positive"
   - Negative terms → "negative"
   - Dividing by x → x has negative influence
   - If ambiguous → "unknown"

===========================================================
TEXT-BASED REASONING RULES (MUST EXTRACT)
===========================================================

YOU MUST read the given paper text and extract ALL meaningful semantic relations,
such as:

- “adsorption rate increases with partial pressure”
  (pA → f_ads, causal)

- “desorption is proportional to surface coverage”
  (h → f_des, causal)

- “growth is self-limiting due to surface saturation”
  (h_max limits g)

- “diffusion depth increases with sqrt(D t)”
  (D → penetration_depth, causal)

- “reaction probability decreases with steric hindrance”
  (steric → reaction_rate, negative)

- “surface coverage determines growth per cycle”
  (h → GPC, causal)

You MUST extract such relations EVEN IF they do not appear in an equation.

Patterns you MUST capture when found in text:

1. increase / decrease / promotes / inhibits
2. proportional to / inversely proportional to
3. limits / saturates / controls / dominates
4. grows with time / diffuses with distance
5. “is defined as” → derived_from
6. “is governed by” → governs
7. “initially” → initial_condition
8. “at the surface boundary” → boundary_condition

These are REQUIRED outputs.

===========================================================
RELATION TYPES
===========================================================

- "causal"
- "depends_on"
- "derived_from"
- "defines"
- "governs"
- "boundary_condition"
- "initial_condition"

===========================================================
OUTPUT REQUIREMENTS
===========================================================

For EACH relation you produce:

{
  "type": "...",
  "source": "...",
  "target": "...",
  "equation_id": "...",
  "direction": "...",
  "description": "..."
}

Rules:
- "equation_id" = equation number if relation came from an equation,
  otherwise null.

- "direction" = "positive" | "negative" | "unknown"

- "description" must be short but physically correct.

===========================================================
CRITICAL REQUIREMENTS
===========================================================

1. You MUST use BOTH equations AND text.
2. You MUST include semantic relations even if no equation supports them.
3. You MUST include equation-based dependencies for every equation.
4. You MUST output MANY relations (not a small set).
5. Output ONLY valid JSON. No markdown or commentary.

"""

    def __init__(self, llm):
        self.llm = llm

    # ---------------------------
    # SAFE JSON EXTRACTOR
    # ---------------------------
    def extract_json(self, text: str) -> str:
        """LLM 출력에서 JSON 블록만 추출."""
        # Try {} block first
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return match.group(0)

        # Try list block
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            return match.group(0)

        raise ValueError("No JSON structure found")

    # ---------------------------
    # EQUATION STRUCTURE ANALYZER
    # ---------------------------
    def _analyze_equation(self, latex: str):
        """
        LaTeX 수식에서 lhs, rhs, variables, operations를 단순 추출.
        너무 정교할 필요는 없고, LLM이 참고할 수 있을 정도면 충분.
        """
        if not latex:
            return None, None, [], []

        # ```latex ...``` 제거
        s = latex.strip()
        s = re.sub(r"```(?:latex)?\s*([\s\S]*?)```", r"\1", s).strip()

        # LHS / RHS 추출
        lhs, rhs = None, None
        if "=" in s:
            parts = s.split("=", 1)
            lhs = parts[0].strip() or None
            rhs = parts[1].strip() or None

        # LaTeX 명령어 제거 (\frac, \text 등)
        tmp = re.sub(r"\\[a-zA-Z]+", " ", s)    # \command
        tmp = re.sub(r"\\[^ \t\n]+", " ", tmp)  # 그 외 \something

        # 알파벳 토큰 추출
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*", tmp)
        blacklist = {
            "exp", "ln", "sin", "cos", "tan",
            "sqrt", "text", "begin", "end",
            "frac"
        }
        variables = [t for t in tokens if t not in blacklist]

        operations = []
        if r"\frac" in s or "/" in s:
            operations.append("fraction")
        if "^" in s:
            operations.append("power")
        if "exp" in s:
            operations.append("exp")
        if "ln" in s:
            operations.append("log")
        if r"\partial" in s or "∂" in s:
            operations.append("partial_derivative")
        if r"\frac{d" in s or "d" in s and "/" in s:
            operations.append("derivative")

        variables = sorted(set(variables))
        operations = sorted(set(operations))

        return lhs, rhs, variables, operations

    # ---------------------------
    # MAIN INFERENCE PROCESS
    # ---------------------------
    def infer_relations(self, full_text, equations, var_defs):

        if not equations:
            self.log("5_RelationReasoning", "no_equations", {"msg": "No equations → no relations"})
            return []

        # Build equation payload with structure info
        eq_payload = []
        for eq in equations:
            lhs, rhs, vars_, ops = self._analyze_equation(eq.normalized_text)
            eq_payload.append(
                {
                    "id": eq.number,
                    "latex": eq.normalized_text,
                    "lhs": lhs,
                    "rhs": rhs,
                    "variables": vars_,
                    "operations": ops,
                }
            )

        # Build variable payload
        var_payload = {
            v.name: {
                "definition": v.definition,
                "units": v.units,
                "source_equations": v.source_equations,
            }
            for v in var_defs.values()
        }

        # Build user prompt
        user_prompt = (
            "Equations:\n" + json.dumps(eq_payload, indent=2, ensure_ascii=False) +
            "\n\nVariables:\n" + json.dumps(var_payload, indent=2, ensure_ascii=False) +
            "\n\nPaper Text:\n" + full_text[:8000]   # 너무 길면 잘려서 8k 정도로 제한
        )

        # -------------------------
        # 1st LLM CALL
        # -------------------------
        raw = self.llm.complete(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        self.log("5_RelationReasoning", "raw_output", {"raw": raw})

        # -------------------------
        # FIRST PARSE ATTEMPT
        # -------------------------
        try:
            cleaned = self.extract_json(raw)
            parsed = json.loads(cleaned)

        except Exception as e:
            # Log the failure
            self.log("5_RelationReasoning", "first_parse_fail",
                     {"error": str(e), "raw": raw})

            # -------------------------
            # REPAIR: DO NOT USE `raw` AGAIN
            # -------------------------
            safe_prompt = """
Your previous output was invalid JSON.

Return ONLY valid JSON in the exact schema:

{
  "relations": [
    {
      "type": "...",
      "source": "...",
      "target": "...",
      "equation_id": "...",
      "direction": "...",
      "description": "..."
    }
  ]
}

Do NOT repeat or reuse any previous output text.
Generate NEW valid JSON from scratch.
"""

            fixed = self.llm.complete(
                system_prompt="Fix the JSON.",
                user_prompt=safe_prompt
            )

            # -------------------------
            # FINAL PARSE ATTEMPT
            # -------------------------
            try:
                cleaned = self.extract_json(fixed)
                parsed = json.loads(cleaned)
            except Exception as e2:
                self.log("5_RelationReasoning", "final_parse_fail",
                         {"error": str(e2), "raw_fixed": fixed})
                return []

        # -------------------------
        # EXTRACT RELATIONS
        # -------------------------
        rel_list = parsed.get("relations", [])
        out = []

        for r in rel_list:
            if not r.get("source") or not r.get("target"):
                continue

            out.append(
                Relation(
                    source=r.get("source"),
                    target=r.get("target"),
                    relation_type=r.get("type"),
                    description=r.get("description")
                )
            )

        self.log("5_RelationReasoning", "parsed_relations", [rel.__dict__ for rel in out])
        return out

    # ---------------------------
    # RUN WRAPPER
    # ---------------------------
    def run(self, ctx):
        out = {}

        for fn in ctx["equations"]:
            equations = ctx["equations"][fn]              # list[Equation]
            variables = {v.name: v for v in ctx["variables"][fn]}  # dict[name → Variable]
            full_text = ctx["pdf_texts"][fn]              # 전체 PDF text

            rels = self.infer_relations(full_text, equations, variables)
            out[fn] = rels

        ctx["relations"] = out
        return ctx



# ===========================================================
# Knowledge Graph Builder Agent
# ===========================================================
@dataclass
class KNode:
    id: str
    type: str
    label: str
    metadata: Dict[str, Any]


@dataclass
class KEdge:
    source: str
    target: str
    relation: str
    metadata: Dict[str, Any]


class KnowledgeGraphBuilderAgent(Agent, AgentLoggerMixin):
    def __init__(self, llm=None):
        super().__init__()
        self.llm = llm

    def run(self, ctx):
        graphs = {}

        for fn in ctx["equations"]:
            equations = ctx["equations"][fn]
            variables = ctx["variables"][fn]
            relations = ctx.get("relations", {}).get(fn, [])

            kg = self.build_graph(equations, variables, relations)

            graphs[fn] = {
                "nodes": [asdict(n) for n in kg.nodes],
                "edges": [asdict(e) for e in kg.edges],
            }

            self.log("6_KGBuilder", fn, graphs[fn])

        ctx["knowledge_graphs"] = graphs
        return ctx

    # =====================================================
    # Main KG Construction
    # =====================================================
    def build_graph(self, equations, var_list, relations):
        kg = KnowledgeGraph(nodes=[], edges=[])

        # --------------------------------------
        # 1) Variable Nodes
        # --------------------------------------
        for v in var_list:
            kg.nodes.append(
                KNode(
                    id=v.name,
                    type="variable",
                    label=v.name,
                    metadata={
                        "definition": v.definition,
                        "units": v.units,
                        "source_equations": v.source_equations,
                    },
                )
            )

        # --------------------------------------
        # 2) Equation Nodes
        # --------------------------------------
        eq_nodes = {}
        for eq in equations:
            eq_id = f"Eq{eq.number}"
            eq_nodes[eq_id] = eq
            kg.nodes.append(
                KNode(
                    id=eq_id,
                    type="equation",
                    label=f"Equation {eq.number}",
                    metadata={
                        "latex": eq.normalized_text,
                        "raw": eq.raw_text,
                    },
                )
            )

        # --------------------------------------------------
        # Helper functions for parsing variables from LaTeX
        # --------------------------------------------------
        def extract_var_tokens(latex):
            if not latex:
                return []

            # remove LaTeX commands: \frac, \exp, etc.
            tmp = re.sub(r"\\[a-zA-Z]+", " ", latex)
            tmp = re.sub(r"\\[^ \t\n]+", " ", tmp)

            # pick tokens
            tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*", tmp)

            blacklist = {
                "exp","ln","log","sqrt","frac","text","begin","end",
                "left","right","sin","cos","tan"
            }
            return [t for t in tokens if t not in blacklist]

        def extract_lhs_variable(latex):
            """Get variable on LHS of equation (simple heuristic)."""
            if not latex or "=" not in latex:
                return None
            lhs = latex.split("=", 1)[0]
            lhs_var = re.findall(r"[A-Za-z][A-Za-z0-9_]*", lhs)
            return lhs_var[0] if lhs_var else None

        def get_governed_variable(latex):
            """Detect dX/dt or ∂X/∂t patterns."""
            m = re.search(r"d([A-Za-z][A-Za-z0-9_]*)", latex)
            if m:
                return m.group(1)
            m = re.search(r"∂([A-Za-z][A-Za-z0-9_]*)", latex)
            if m:
                return m.group(1)
            return None

        # --------------------------------------------------
        # 3) Equation-variable dependency edges
        # --------------------------------------------------
        for eq in equations:
            eq_id = f"Eq{eq.number}"
            latex = eq.normalized_text

            # extract all variable tokens used in the equation
            vars_used = extract_var_tokens(latex)

            # (a) variable → equation (usage)
            for v in vars_used:
                kg.edges.append(
                    KEdge(
                        source=v,
                        target=eq_id,
                        relation="appears_in",
                        metadata={"description": f"Variable {v} appears in {eq_id}"}
                    )
                )

            # (b) equation → variable (definition or LHS)
            lhs_var = extract_lhs_variable(latex)
            if lhs_var:
                kg.edges.append(
                    KEdge(
                        source=eq_id,
                        target=lhs_var,
                        relation="defines",
                        metadata={"description": f"{eq_id} defines {lhs_var}"}
                    )
                )

            # (c) equation → variable (governs derivative)
            governed = get_governed_variable(latex)
            if governed:
                kg.edges.append(
                    KEdge(
                        source=eq_id,
                        target=governed,
                        relation="governs",
                        metadata={"description": f"{eq_id} governs evolution of {governed}"}
                    )
                )

        # --------------------------------------------------
        # 4) Add semantic relations from RelationReasoningAgent
        # --------------------------------------------------
        for rel in relations:
            kg.edges.append(
                KEdge(
                    source=rel.source,
                    target=rel.target,
                    relation=rel.relation_type,
                    metadata={"description": rel.description},
                )
            )

        # --------------------------------------------------
        # 5) Autocreate missing nodes (safety)
        # --------------------------------------------------
        node_ids = {n.id for n in kg.nodes}

        for e in kg.edges:
            if e.source not in node_ids:
                kg.nodes.append(
                    KNode(
                        id=e.source,
                        type="variable",
                        label=e.source,
                        metadata={"notes": "auto-created source"}
                    )
                )
                node_ids.add(e.source)

            if e.target not in node_ids:
                kg.nodes.append(
                    KNode(
                        id=e.target,
                        type="variable",
                        label=e.target,
                        metadata={"notes": "auto-created target"}
                    )
                )
                node_ids.add(e.target)

        return kg



# ===========================================================
# Consistency Checker Agent
# ===========================================================
class ConsistencyCheckerAgent(Agent, AgentLoggerMixin):
    def __init__(self, llm=None):
        super().__init__()
        self.llm = llm

    def run(self, ctx):
        reports = {}

        for fn in ctx["equations"]:
            eqs = ctx["equations"][fn]            # list[Equation]
            vars_list = ctx["variables"][fn]      # list[Variable]
            kg = ctx["knowledge_graphs"][fn]      # dict{"nodes":..., "edges":...}

            report = self.check(eqs, vars_list, kg)
            reports[fn] = report

            self.log("7_ConsistencyChecker", fn, report)

        ctx["consistency"] = reports
        return ctx


    def check(self, equations, var_list, kg_dict):
        issues = []

        # ---------------------------------------------------
        # 1) Undefined variables: compare eq-normalized_text with var_list
        # ---------------------------------------------------
        defined = {v.name for v in var_list}
        
        used = set()
        for eq in equations:
            # 변수 토큰 추출
            tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*", eq.normalized_text)
            used.update(tokens)

        undefined = used - defined
        if undefined:
            issues.append(f"Variables used but not defined: {sorted(undefined)}")

        # ---------------------------------------------------
        # 2) Equation sanity check
        # ---------------------------------------------------
        for eq in equations:
            if not eq.normalized_text or "=" not in eq.normalized_text:
                issues.append(f"Equation ({eq.number}) seems malformed: '{eq.normalized_text}'")

        # ---------------------------------------------------
        # 3) Knowledge Graph sanity check
        # ---------------------------------------------------
        node_ids = {n["id"] for n in kg_dict["nodes"]}

        for e in kg_dict["edges"]:
            if e["source"] not in node_ids:
                issues.append(f"Edge source missing: {e['source']}")
            if e["target"] not in node_ids:
                issues.append(f"Edge target missing: {e['target']}")

        return {"issues": issues}



# ===========================================================
# Interpreter Agent
# ===========================================================
class InterpreterAgent(Agent, AgentLoggerMixin):
    SYSTEM_PROMPT = """
You are an expert ALD modeling analyst.

Explain the ALD model clearly using:

- The extracted equations
- Surface chemistry variables
- Reaction steps
- State evolution
- Pulse sequence logic
- Causal relations inferred earlier
- The knowledge graph structure

Output a clean, coherent explanation (no JSON).
"""

    def __init__(self, llm):
        self.llm = llm

    def run(self, ctx, language="en"):
        outputs = {}

        for fn in ctx["equations"]:
            eqs = ctx["equations"][fn]            # list[Equation]
            vars_list = ctx["variables"][fn]      # list[Variable]
            rels = ctx["relations"][fn]           # list[Relation]
            kg = ctx["knowledge_graphs"][fn]      # dict{"nodes":[], "edges":[]}

            # -------------------------
            # Build JSON payload manually
            # -------------------------
            eq_payload = [
                {
                    "number": e.number,
                    "raw_text": e.raw_text,
                    "normalized_text": e.normalized_text,
                }
                for e in eqs
            ]

            var_payload = [
                {
                    "name": v.name,
                    "definition": v.definition,
                    "units": v.units,
                    "role": v.role,
                    "source_equations": v.source_equations,
                }
                for v in vars_list
            ]

            rel_payload = [
                {
                    "source": r.source,
                    "target": r.target,
                    "relation_type": r.relation_type,
                    "description": r.description,
                }
                for r in rels
            ]

            kg_payload = {
                "nodes": kg["nodes"],
                "edges": kg["edges"]
            }

            # -------------------------
            # Final JSON blob
            # -------------------------
            payload = {
                "equations": eq_payload,
                "variables": var_payload,
                "relations": rel_payload,
                "knowledge_graph": kg_payload,
            }

            user_prompt = json.dumps(payload, indent=2, ensure_ascii=False)

            # -------------------------
            # LLM call
            # -------------------------
            explanation = self.llm.complete(
                self.SYSTEM_PROMPT,
                user_prompt,
            )

            # Korean translation if needed
            if language.lower().startswith("ko"):
                explanation = self.llm.complete(
                    "Translate the following into precise, technical Korean.",
                    explanation,
                )

            outputs[fn] = explanation

            self.log("8_Interpreter", fn, {"explanation": explanation})

        ctx["interpretations"] = outputs
        return ctx


# ===========================================================
# Final Orchestrator (Your Architecture)
# ===========================================================
from dataclasses import dataclass
from pathlib import Path
import json
from llm_client import LLMClient


@dataclass
class ALDModelingResult:
    equations: dict
    variables: dict
    relations: dict
    knowledge_graphs: dict
    interpretations: dict


class ALDModelingCoPilot:
    def __init__(self, pdf_dir, llm):
        self.llm = llm

        self.agents = [
            PDFLoaderAgent(pdf_dir),
            EquationBlockExtractionAgent(),
            EquationReconstructionAgent(self.llm),
            VariableDefinitionAgent(),
            RelationReasoningAgent(self.llm),
            KnowledgeGraphBuilderAgent(),
            InterpreterAgent(self.llm),
        ]

    def run(self):
        ctx = {}
        for agent in self.agents:
            ctx = agent.run(ctx)
        return ctx



# ===========================================================
# Main Entry Point
# ===========================================================
from llm_client import LLMClient

if __name__ == "__main__":
    pdf_dir = "/home/ftk3187/github/PSED/aldmodeling_agent/pdfs"

    llm = LLMClient(model="gpt-4o-mini")   # ★ 반드시 필요 ★

    cop = ALDModelingCoPilot(pdf_dir, llm)
    ctx = cop.run()

    out = Path("./outputs")
    out.mkdir(exist_ok=True)

    # Save Knowledge Graphs
    for fn, kg in ctx["knowledge_graphs"].items():
        with open(out / f"{fn}.kg.json", "w", encoding="utf8") as f:
            json.dump(
                {"nodes": kg["nodes"], "edges": kg["edges"]},
                f,
                indent=2,
                ensure_ascii=False
            )

    # Save interpretations
    if "interpretations" in ctx:
        for fn, text in ctx["interpretations"].items():
            with open(out / f"{fn}.interpretation.txt", "w", encoding="utf8") as f:
                f.write(text)

    print("Processing completed.")
