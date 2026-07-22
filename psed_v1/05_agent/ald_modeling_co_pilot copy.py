#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JSON-SAFE VERSION (Enhanced, Stable)
ALD Modeling Co-Pilot – Robust Version
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()


# ===========================================================
# Logging (DEBUG + INFO both visible)
# ===========================================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ALDModelingCoPilot")


# ===========================================================
# JSON Extractor (Robust)
# ===========================================================
def extract_json(text: str) -> str:
    """
    Extract FIRST valid JSON object or array from LLM output.
    Works even if extra text, comments, citations exist.
    """
    # remove code fences
    text = text.replace("```json", "").replace("```", "")

    # Find JSON object {...}
    obj = re.search(r'\{.*\}', text, re.DOTALL)
    arr = re.search(r'\[.*\]', text, re.DOTALL)

    if arr:
        return arr.group(0)
    if obj:
        return obj.group(0)

    raise ValueError("No JSON array/object found in LLM output.")


# ===========================================================
# LLM Client Wrapper (Stable JSON mode)
# ===========================================================
class LLMClient:
    def __init__(self, model: str = "gpt-5.1", max_tokens: int = 4000):
        self.model = model
        self.max_tokens = max_tokens

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found in .env")

        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        resp = self._client.responses.create(
            model=self.model,
            max_output_tokens=self.max_tokens,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        # 🔥 여기부터가 핵심: Response 객체에서 순수 텍스트만 안전하게 뽑기
        try:
            # 보통 구조: resp.output[0].content[0].text (이미 str)
            msg = resp.output[0]
            part = msg.content[0]

            # part.text가 str인지 / 객체인지 모두 처리
            txt = getattr(part, "text", None)
            if isinstance(txt, str):
                return txt
            if hasattr(txt, "value"):  # 예전 스타일 대비
                return txt.value

            # 혹시 몰라서 fallback
            return str(txt)

        except Exception:
            # 그래도 안되면 마지막 fallback: resp.text 또는 그냥 에러
            t = getattr(resp, "text", None)
            if isinstance(t, str):
                return t
            # 진짜 마지막: str(resp) (이건 거의 안 타게)
            return str(resp)


# ===========================================================
# BaseAgent
# ===========================================================
class BaseAgent:
    def __init__(self, llm: Optional[LLMClient]):
        self.llm = llm

    def log(self, msg: str, level=logging.INFO):
        logger.log(level, f"[{self.__class__.__name__}] {msg}")


# ===========================================================
# Data Models
# ===========================================================
@dataclass
class Equation:
    id: str
    latex: str
    context: str
    lhs: Optional[str] = None
    rhs: Optional[str] = None
    variables: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)


@dataclass
class VariableInfo:
    name: str
    meaning: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None


@dataclass
class Relation:
    type: str
    source: str
    target: str
    equation_id: Optional[str] = None
    direction: Optional[str] = None
    description: Optional[str] = None


@dataclass
class KNode:
    id: str
    type: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KEdge:
    source: str
    target: str
    relation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeGraph:
    nodes: List[KNode] = field(default_factory=list)
    edges: List[KEdge] = field(default_factory=list)

    def to_json(self):
        return json.dumps(
            {
                "nodes": [asdict(n) for n in self.nodes],
                "edges": [asdict(e) for e in self.edges],
            },
            indent=2,
            ensure_ascii=False,
        )


# ===========================================================
# PDF Loader (Two-column aware + Equation block extractor)
# ===========================================================

import fitz
import re
from pathlib import Path
from typing import Dict, Any, List

class PDFLoaderAgent(BaseAgent):
    """
    Two-column PDF extraction + robust equation block detection.
    Handles:
      - inline equation numbers (24)
      - equations preceding numbers
      - multi-line equations ending with ; , ) or nothing
    """

    # ========================================================
    # Column-split extractor
    # ========================================================
    def extract_two_column_text(self, pdf_path: str | Path) -> List[str]:
        import fitz
        doc = fitz.open(pdf_path)
        pages_text = []

        for page in doc:
            blocks = page.get_text("blocks")
            left_col, right_col = [], []
            mid_x = page.rect.width / 2

            for b in blocks:
                x0, y0, x1, y1, text, *_ = b
                if not text.strip():
                    continue

                if x1 < mid_x:
                    left_col.append((y0, text))
                elif x0 > mid_x:
                    right_col.append((y0, text))
                else:  # ambiguous
                    if abs(x0) < abs(x1 - page.rect.width):
                        left_col.append((y0, text))
                    else:
                        right_col.append((y0, text))

            left_col.sort(key=lambda x: x[0])
            right_col.sort(key=lambda x: x[0])

            page_text = (
                "\n".join(t for _, t in left_col)
                + "\n"
                + "\n".join(t for _, t in right_col)
            )
            pages_text.append(page_text)

        doc.close()
        return pages_text

    # ========================================================
    # Helpers
    # ========================================================
    def find_inline_eq_number(self, line: str):
        """detect (24) even if inline"""
        m = re.search(r'\((\d{1,4})\)', line)
        return m.group(1) if m else None

    def is_unit_only(self, line: str):
        return bool(re.match(r'^[A-Za-z0-9_{}\-\.\+\\]+?\s*[\[\(].*[\]\)]\s*$', line))

    def is_math_line(self, line: str):
        L = line.strip()
        if len(L) < 2:
            return False

        math_tokens = [
            '=', '≈', '~', '≃', '≅', '≥', '≤', '/', '∂', '^', '_',
            'exp', 'sqrt', 'sin', 'cos', 'tan'
        ]
        if any(tok in L for tok in math_tokens):
            return True

        # pA(x,t) 형태
        if re.match(r'^[A-Za-z]\w*\(.*\)$', L):
            return True

        # 끝이 세미콜론/콤마도 수식임
        if re.search(r'[;,]\s*$', L):
            return True

        return False

    # ========================================================
    # Main loader: ROBUST eq detection (backward capture)
    # ========================================================
    def load_pdf(self, pdf_path: str | Path) -> Dict[str, Any]:
        import re

        full_pages = self.extract_two_column_text(pdf_path)

        equation_candidates = []

        # ---- scan pages ----
        for page_idx, txt in enumerate(full_pages):
            lines = txt.split("\n")

            for i, raw in enumerate(lines):
                line = raw.strip()
                if not line:
                    continue

                # (A) detect inline (24)
                eq_no = self.find_inline_eq_number(line)
                if eq_no:
                    # 역으로 backward scan하여 식 block 수집
                    eq_block = []
                    j = i - 1

                    while j >= 0:
                        L = lines[j].strip()
                        if self.is_math_line(L):
                            eq_block.insert(0, L)
                            j -= 1
                        else:
                            break

                    # store
                    if eq_block:
                        equation_candidates.append({
                            "page": page_idx + 1,
                            "text": " ".join(eq_block).strip(),
                            "eq_no": eq_no,
                        })

                    continue

                # (B) detect lines that are math but no eq number (standalone)
                if self.is_math_line(line):
                    equation_candidates.append({
                        "page": page_idx + 1,
                        "text": line,
                        "eq_no": None,
                    })

        self.log(
            f"[PDFLoader] Pages={len(full_pages)}, Eq candidates={len(equation_candidates)}",
            logging.INFO
        )

        return {
            "pages": full_pages,
            "full_text": "\n\n".join(full_pages),
            "equation_candidates": equation_candidates,
        }






# ===========================================================
# Equation Extraction Agent (JSON-safe)
# ===========================================================
class EquationExtractionAgent(BaseAgent):
    SYSTEM_PROMPT = """
You are an equation extraction agent. 
You must detect ANY mathematical expressions, even if they look rough or not perfect LaTeX.

A snippet MUST be treated as an equation if it contains:
- =, ≈, ∝
- fractions like a/b
- ∂, d/dt, derivatives
- variables with subscripts (x1, p_A)
- any algebraic structure

Your task for EACH snippet:
1. If it contains ANY mathematical pattern, treat it as an equation.
2. Convert it into clean LaTeX (you may rewrite or fix syntax).
3. Split into LHS and RHS (if there is '=')
4. Extract variable names (letters, subscripts)
5. Output an object:

{
  "id": "Eq1",
  "latex": "...",
  "lhs": "...",
  "rhs": "...",
  "variables": [...],
  "operations": [...]
}

IMPORTANT:
- DO NOT SKIP equations unless the snippet is pure English text.
- When in doubt, treat it as an equation.
- It is OK if the snippet has text around the equation; extract the equation part.

Your ENTIRE response MUST be a JSON array ONLY.
No explanation. No markdown. No comments.
Start with '[' and end with ']'.
"""

    def extract_equations(self, raw_data: Dict[str, Any]) -> List[Equation]:
        eq_candidates = raw_data.get("equation_candidates", [])

        if not eq_candidates:
            self.log("No equation candidates found in PDF", logging.WARNING)
            return []

        CHUNK_SIZE = 10
        chunks = [
            eq_candidates[i: i + CHUNK_SIZE]
            for i in range(0, len(eq_candidates), CHUNK_SIZE)
        ]

        all_equations = []
        global_eq_idx = 1

        for chunk_idx, chunk in enumerate(chunks, start=1):
            snippets = []
            for idx, item in enumerate(chunk, start=1):
                snippets.append(
                    f"Snippet {idx} (page {item['page']}):\n{item['text']}"
                )

            user_prompt = (
                f"Process these snippets (chunk {chunk_idx}/{len(chunks)}).\n"
                "Return ONLY the JSON array.\n\n"
                + "\n\n".join(snippets)
            )

            raw_json = self.llm.complete(self.SYSTEM_PROMPT, user_prompt)

            try:
                cleaned = extract_json(raw_json)
                parsed = json.loads(cleaned)
            except Exception as e:
                self.log(f"[EquationExtraction] JSON parse error in chunk {chunk_idx}: {e}", logging.ERROR)
                continue

            for obj in parsed:
                eq = Equation(
                    id=f"Eq{global_eq_idx}",
                    latex=obj.get("latex", ""),
                    context="",
                    lhs=obj.get("lhs"),
                    rhs=obj.get("rhs"),
                    variables=obj.get("variables", []) or [],
                    operations=obj.get("operations", []) or [],
                )
                all_equations.append(eq)
                global_eq_idx += 1

        self.log(f"Extracted {len(all_equations)} equations after merging chunks", logging.INFO)
        return all_equations



# ===========================================================
# Variable Definition Agent (JSON-safe)
# ===========================================================
class VariableDefinitionAgent(BaseAgent):
    SYSTEM_PROMPT = """
You are an expert in ALD physics and modeling, acting as a Variable Definition Agent.

Input:
- A list of variable names.
- The full paper text (possibly truncated).

For EACH variable, output:
{
  "name": "C",
  "meaning": "... or null",
  "unit": "... or null",
  "notes": "...",
  "location": "page/section info if known, else null"
}

If you cannot find a definition in the text, set:
- "meaning": null
- "unit": null
- "notes": "definition not found"

Output format:
{
  "variables": [
    { ... },
    { ... }
  ]
}

VERY IMPORTANT:
- Output MUST be valid JSON only.
- No explanations, no markdown, no comments.
- Start directly with '{' and end with '}'.
"""

    def __init__(self, llm: LLMClient):
        super().__init__(llm)

    def define_variables(
        self,
        full_text: str,
        equations: List[Equation],
    ) -> Dict[str, VariableInfo]:

        vars_set = set()
        for eq in equations:
            for v in eq.variables:
                if v:
                    vars_set.add(v)

        if not vars_set:
            self.log("No variables to define", logging.WARNING)
            return {}

        var_list = sorted(vars_set)
        self.log(f"Defining {len(var_list)} variables", logging.INFO)

        user_prompt = (
            "Variables:\n" + ", ".join(var_list) +
            "\n\nFull paper text (may be truncated):\n" + full_text[:15000]
        )

        raw_json = self.llm.complete(self.SYSTEM_PROMPT, user_prompt)
        self.log("=== RAW LLM OUTPUT (VariableDefinition) ===", logging.INFO)
        self.log(raw_json, logging.INFO)

        try:
            cleaned = extract_json(raw_json)
            parsed = json.loads(cleaned)
        except Exception as e:
            self.log(f"Variable definition JSON parse failed: {e}", logging.ERROR)
            return {}

        result: Dict[str, VariableInfo] = {}

        # -----------------------------
        # JSON root 형태 자동 처리
        # -----------------------------
        if isinstance(parsed, dict):
            # 정상적인 {"variables": [...]}
            var_objs = parsed.get("variables", [])
        elif isinstance(parsed, list):
            # LLM이 바로 리스트를 반환한 경우
            var_objs = parsed
        else:
            self.log(f"Unexpected JSON root type: {type(parsed)}", logging.ERROR)
            return {}

        # -----------------------------
        # 변수 정보 생성
        # -----------------------------
        for obj in var_objs:
            name = obj.get("name")
            if not name:
                continue
            info = VariableInfo(
                name=name,
                meaning=obj.get("meaning"),
                unit=obj.get("unit"),
                notes=obj.get("notes"),
                location=obj.get("location"),
            )
            result[name] = info

        self.log(f"Defined {len(result)} variables", logging.INFO)
        return result


# ===========================================================
# Relation Reasoning Agent (JSON-safe)
# ===========================================================
class RelationReasoningAgent(BaseAgent):
    SYSTEM_PROMPT = """
You are a scientific causal-reasoning agent for ALD modeling.

You receive:
- Equations (id, latex, lhs, rhs, variables, operations)
- Variable definitions
- Part of the paper text

Goal:
Produce a list of relations of the form:

{
  "relations": [
    {
      "type": "causal" | "depends_on" | "derived_from" |
               "boundary_condition" | "initial_condition",
      "source": "<variable or equation id>",
      "target": "<variable or equation id>",
      "equation_id": "<EqID or null>",
      "direction": "positive" | "negative" | "unknown" | null,
      "description": "short explanation"
    },
    ...
  ]
}

Rules:
- Use equation structure + variable roles.
- Capture cause-effect links and dependencies.
- If you are unsure about direction, use "unknown".

VERY IMPORTANT:
- Output MUST be valid JSON only.
- No extra text, no markdown, no commentary.
- Start directly with '{' and end with '}'.
"""

    def __init__(self, llm: LLMClient):
        super().__init__(llm)

    def infer_relations(
        self,
        full_text: str,
        equations: List[Equation],
        var_defs: Dict[str, VariableInfo],
    ) -> List[Relation]:

        if not equations:
            self.log("No equations → no relations", logging.WARNING)
            return []

        eq_payload = [
            {
                "id": eq.id,
                "latex": eq.latex,
                "lhs": eq.lhs,
                "rhs": eq.rhs,
                "variables": eq.variables,
                "operations": eq.operations,
            }
            for eq in equations
        ]

        var_payload = {
            name: {
                "meaning": v.meaning,
                "unit": v.unit,
                "notes": v.notes,
                "location": v.location,
            }
            for name, v in var_defs.items()
        }

        user_prompt = (
            "Equations:\n" + json.dumps(eq_payload, indent=2, ensure_ascii=False) +
            "\n\nVariable Definitions:\n" + json.dumps(var_payload, indent=2, ensure_ascii=False) +
            "\n\nPaper Text (may be truncated):\n" + full_text[:15000]
        )

        raw_json = self.llm.complete(self.SYSTEM_PROMPT, user_prompt)
        self.log("=== RAW LLM OUTPUT (RelationReasoning) ===", logging.INFO)
        self.log(raw_json, logging.INFO)

        try:
            cleaned = extract_json(raw_json)
            parsed = json.loads(cleaned)
        except Exception as e:
            self.log(f"Relation JSON parse failed: {e}", logging.ERROR)
            return []

        relations: List[Relation] = []

        # -----------------------------
        # JSON root 자동 판별
        # -----------------------------
        if isinstance(parsed, dict):
            # 정상 형태: {"relations": [...]}
            rel_objs = parsed.get("relations", [])
        elif isinstance(parsed, list):
            # LLM이 relations만 담은 리스트를 바로 반환한 경우
            rel_objs = parsed
        else:
            self.log(f"Unexpected JSON root type: {type(parsed)}", logging.ERROR)
            return []

        # -----------------------------
        # relation 객체 생성
        # -----------------------------
        for obj in rel_objs:
            rel = Relation(
                type=obj.get("type", ""),
                source=obj.get("source", ""),
                target=obj.get("target", ""),
                equation_id=obj.get("equation_id"),
                direction=obj.get("direction"),
                description=obj.get("description"),
            )
            if rel.source and rel.target and rel.type:
                relations.append(rel)

        self.log(f"Inferred {len(relations)} relations")
        return relations



# ===========================================================
# Knowledge Graph Builder Agent
# ===========================================================
class KnowledgeGraphBuilderAgent(BaseAgent):
    def __init__(self, llm=None):
        super().__init__(llm)

    def build_graph(
        self,
        equations: List[Equation],
        var_defs: Dict[str, VariableInfo],
        relations: List[Relation],
    ) -> KnowledgeGraph:

        kg = KnowledgeGraph()

        # --------------------------
        # 1) Variable nodes
        # --------------------------
        for name, v in var_defs.items():
            kg.nodes.append(
                KNode(
                    id=name,
                    type="variable",
                    label=name,
                    metadata={
                        "meaning": v.meaning,
                        "unit": v.unit,
                        "notes": v.notes,
                        "location": v.location,
                    },
                )
            )

        # Include variables not appearing in var_defs
        defined = set(var_defs.keys())
        for eq in equations:
            for v in eq.variables:
                if v not in defined:
                    kg.nodes.append(
                        KNode(
                            id=v,
                            type="variable",
                            label=v,
                            metadata={
                                "meaning": None,
                                "unit": None,
                                "notes": "not defined in text"
                            },
                        )
                    )
                    defined.add(v)

        # --------------------------
        # 2) Equation nodes
        # --------------------------
        for eq in equations:
            kg.nodes.append(
                KNode(
                    id=eq.id,
                    type="equation",
                    label=eq.id,
                    metadata={
                        "latex": eq.latex,
                        "lhs": eq.lhs,
                        "rhs": eq.rhs,
                        "variables": eq.variables,
                        "operations": eq.operations,
                    },
                )
            )

        # --------------------------
        # 3) Relation edges
        # --------------------------
        for rel in relations:
            kg.edges.append(
                KEdge(
                    source=rel.source,
                    target=rel.target,
                    relation=rel.type,
                    metadata={
                        "equation_id": rel.equation_id,
                        "direction": rel.direction,
                        "description": rel.description,
                    },
                )
            )

        # After all variable and equation nodes are created:

        # --------------------------------------------------
        # 4) Ensure all relation nodes exist
        # --------------------------------------------------
        node_ids = {n.id for n in kg.nodes}

        for rel in relations:
            # add missing source
            if rel.source not in node_ids:
                kg.nodes.append(
                    KNode(
                        id=rel.source,
                        type="variable",
                        label=rel.source,
                        metadata={"notes": "generated from relation (undefined in equations/variables)"}
                    )
                )
                node_ids.add(rel.source)

            # add missing target
            if rel.target not in node_ids:
                kg.nodes.append(
                    KNode(
                        id=rel.target,
                        type="variable",
                        label=rel.target,
                        metadata={"notes": "generated from relation (undefined in equations/variables)"}
                    )
                )
                node_ids.add(rel.target)


        self.log(f"Knowledge Graph built: {len(kg.nodes)} nodes, {len(kg.edges)} edges")
        return kg


# ===========================================================
# Consistency Checker Agent
# ===========================================================
class ConsistencyCheckerAgent(BaseAgent):
    def __init__(self, llm=None):
        super().__init__(llm)

    def check(
        self,
        equations: List[Equation],
        var_defs: Dict[str, VariableInfo],
        kg: KnowledgeGraph,
    ) -> Dict[str, Any]:

        issues = []

        # undefined variables
        used_vars = set()
        for eq in equations:
            used_vars.update(eq.variables)

        defined_vars = set(var_defs.keys())
        undefined = used_vars - defined_vars
        if undefined:
            issues.append(f"Variables used but not defined: {sorted(list(undefined))}")

        # equation sanity
        for eq in equations:
            if not eq.lhs or not eq.rhs:
                issues.append(f"{eq.id} has missing LHS or RHS")

        # graph sanity
        node_ids = {n.id for n in kg.nodes}
        for e in kg.edges:
            if e.source not in node_ids:
                issues.append(f"Edge source missing in graph: {e.source}")
            if e.target not in node_ids:
                issues.append(f"Edge target missing in graph: {e.target}")

        self.log(f"Consistency check found {len(issues)} issues", logging.INFO)

        return {"issues": issues}


# ===========================================================
# Interpreter Agent
# ===========================================================
class InterpreterAgent(BaseAgent):
    SYSTEM_PROMPT = """
You are an expert ALD modeling analyst.
Convert the given structured ALD model into a clean explanation.

Include:
- State variables
- Inputs / controls
- Parameters
- Equation roles (adsorption, desorption, kinetics, transport, etc.)
- Half-cycle reasoning (A-pulse → purge → B-pulse → purge)
- Causal flow: inputs → kinetics → surface coverage → GPC
- Differentiability and simulation structure

Format:
- Bullet points
- Short paragraphs
"""

    def __init__(self, llm: LLMClient):
        super().__init__(llm)

    def interpret(
        self,
        equations: List[Equation],
        var_defs: Dict[str, VariableInfo],
        relations: List[Relation],
        kg: KnowledgeGraph,
        language: str = "en",
    ) -> str:

        payload = {
            "equations": [asdict(eq) for eq in equations],
            "variables": {name: asdict(info) for name, info in var_defs.items()},
            "relations": [asdict(r) for r in relations],
            "knowledge_graph": {
                "nodes": [asdict(n) for n in kg.nodes],
                "edges": [asdict(e) for e in kg.edges],
            },
        }

        user_prompt = "ALD model JSON:\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)

        explanation_en = self.llm.complete(self.SYSTEM_PROMPT, user_prompt)

        if language.lower().startswith("ko"):
            translator_prompt = "Translate the text below into technical Korean:\n\n" + explanation_en
            return self.llm.complete("Translate to Korean.", translator_prompt)

        return explanation_en


# ===========================================================
# ALDModelingCoPilot (Orchestrator)
# ===========================================================
@dataclass
class ALDModelingResult:
    equations: List[Equation]
    variables: Dict[str, VariableInfo]
    relations: List[Relation]
    knowledge_graph: KnowledgeGraph
    consistency_report: Dict[str, Any]
    explanation: str


class ALDModelingCoPilot:
    def __init__(self, model: str = "gpt-5.1", max_tokens: int = 4000):
        llm = LLMClient(model=model, max_tokens=max_tokens)

        self.pdf_loader = PDFLoaderAgent(llm=None)
        self.eq_extractor = EquationExtractionAgent(llm=llm)
        self.var_def_agent = VariableDefinitionAgent(llm=llm)
        self.rel_agent = RelationReasoningAgent(llm=llm)
        self.kg_builder = KnowledgeGraphBuilderAgent(llm=None)
        self.consistency_checker = ConsistencyCheckerAgent(llm=None)
        self.interpreter = InterpreterAgent(llm=llm)

    def run(self, pdf_path: str | Path, language: str = "en") -> ALDModelingResult:

        raw_pdf = self.pdf_loader.load_pdf(pdf_path)
        full_text = raw_pdf["full_text"]

        equations = self.eq_extractor.extract_equations(raw_pdf)
        var_defs = self.var_def_agent.define_variables(full_text, equations)
        relations = self.rel_agent.infer_relations(full_text, equations, var_defs)
        kg = self.kg_builder.build_graph(equations, var_defs, relations)
        consistency = self.consistency_checker.check(equations, var_defs, kg)
        explanation = self.interpreter.interpret(
            equations, var_defs, relations, kg, language=language
        )

        return ALDModelingResult(
            equations=equations,
            variables=var_defs,
            relations=relations,
            knowledge_graph=kg,
            consistency_report=consistency,
            explanation=explanation,
        )



def test_two_column_dump(pdf_path: str, out_path: str = "two_column_debug.txt"):
    loader = PDFLoaderAgent(llm=None)
    text = loader.extract_two_column_text(pdf_path)
    Path(out_path).write_text(text, encoding="utf-8")
    print(f"[OK] Two-column dump saved to {out_path}")


# ===========================================================
# CLI Entry Point
# ===========================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ALD Modeling Co-Pilot (Robust JSON Version)"
    )

    parser.add_argument("--model", type=str, default="gpt-5.1")
    parser.add_argument("--language", type=str, default="ko", choices=["en", "ko"])
    parser.add_argument("--outdir", type=str, default="ald_modeling_outputs")

    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    pdfdir = script_dir / "pdfs"

    if not pdfdir.exists():
        raise RuntimeError(f"PDF directory not found: {pdfdir}")

    pdf_files = list(pdfdir.glob("*.pdf"))
    if not pdf_files:
        raise RuntimeError("No PDF files in ./pdfs")

    copilot = ALDModelingCoPilot(model=args.model)

    for pdf in pdf_files:
        print(f"\n=== Processing {pdf.name} ===")
        result = copilot.run(pdf, language=args.language)

        outdir = Path(args.outdir) / pdf.stem
        outdir.mkdir(parents=True, exist_ok=True)

        (outdir / "equations.json").write_text(
            json.dumps([asdict(eq) for eq in result.equations], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        (outdir / "variables.json").write_text(
            json.dumps({k: asdict(v) for k, v in result.variables.items()}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        (outdir / "relations.json").write_text(
            json.dumps([asdict(r) for r in result.relations], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        (outdir / "knowledge_graph.json").write_text(
            result.knowledge_graph.to_json(),
            encoding="utf-8"
        )
        (outdir / "consistency_report.json").write_text(
            json.dumps(result.consistency_report, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        (outdir / "explanation.txt").write_text(
            result.explanation,
            encoding="utf-8"
        )

        print(f"Saved to {outdir}")

if __name__ == "__main__":
    # === TEMP TEST 2: equation candidate extraction ===
    pdf_path = "pdfs/205301_1_online.pdf"
    loader = PDFLoaderAgent(llm=None)

    # ✅ NEW: extract equation candidates via load_pdf()
    raw_data = loader.load_pdf(pdf_path)
    eqs = raw_data.get("equation_candidates", [])

    out_path = "debug_equation_candidates.txt"
    from pathlib import Path
    Path(out_path).write_text(
        "\n\n".join(f"[p{e['page']}] (Eq {e['eq_no']}) {e['text']}" 
                    for e in eqs),
        encoding="utf-8"
    )

    print(f"[OK] Equation candidates saved to {out_path}")
