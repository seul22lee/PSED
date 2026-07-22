#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ALD Modeling Co-Pilot (Enhanced SOP Version):
- Input: ALD-related scientific PDF (process / modeling paper)
- Output:
  * Structured equations
  * Variable definitions (meaning, units, role)
  * Quantitative & qualitative relations
  * Knowledge Graph JSON
  * Human-readable explanation of the model structure

Multi-agent pipeline:
  PDFLoaderAgent
    -> EquationExtractionAgent
    -> VariableDefinitionAgent
    -> RelationReasoningAgent
    -> KnowledgeGraphBuilderAgent
    -> ConsistencyCheckerAgent
    -> InterpreterAgent
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
load_dotenv()  # .env 파일 자동 로드


# ---------------------------------------------------------------------------
# Logging config
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ALDModelingCoPilot")


# ---------------------------------------------------------------------------
# LLM Client Wrapper (OpenAI or pluggable)
# ---------------------------------------------------------------------------

class LLMClient:
    """
    Thin wrapper around an LLM (e.g., OpenAI) so you can swap it easily.
    """

    def __init__(self, model: str = "gpt-5.1", max_tokens: int = 4000):
        self.model = model
        self.max_tokens = max_tokens

        # Load API key from environment (.env)
        openai_key = os.getenv("OPENAI_API_KEY")

        if not openai_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found. "
                "Please create a .env file or export the variable."
            )

        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=openai_key)
        except Exception as e:
            self._client = None
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise e

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if self._client is None:
            raise RuntimeError("LLM client not initialized. Check API key.")

        resp = self._client.responses.create(
            model=self.model,
            max_output_tokens=self.max_tokens,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        try:
            out = resp.output[0].content[0].text.value
        except Exception:
            out = str(resp)
        return out



# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

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

    def to_json(self) -> str:
        return json.dumps(
            {
                "nodes": [asdict(n) for n in self.nodes],
                "edges": [asdict(e) for e in self.edges],
            },
            indent=2,
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Base Agent
# ---------------------------------------------------------------------------

class BaseAgent:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def log(self, msg: str, level=logging.INFO):
        logger.log(level, f"[{self.__class__.__name__}] {msg}")


# ---------------------------------------------------------------------------
# PDF Loader Agent
# ---------------------------------------------------------------------------

class PDFLoaderAgent(BaseAgent):
    """
    PDF Loader Agent (low-level extractor)

    목표(이상적인 역할):
      - PDF에서 텍스트 / 수식 / 그림 캡션 / 섹션 구조를 모두 추출
      - 문단/섹션/그림/표 단위로 구조화
      - LaTeX/수식 번호까지 인식하여 equation candidate로 넘기기

    현재 구현(미니멀 버전):
      - PyMuPDF를 사용해서:
        * 페이지별 plain text 추출
        * '=' 가 포함된 짧은 블록을 "수식 후보"로 수집
      - 향후 확장 시:
        * figure/caption, table caption, section heading 등도 구조화 가능
    """

    def load_pdf(self, pdf_path: str | Path) -> Dict[str, Any]:
        pdf_path = Path(pdf_path)
        self.log(f"Loading PDF: {pdf_path}")
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise RuntimeError(
                "PyMuPDF (`pymupdf`) is required for PDF parsing. "
                "Install it via `pip install pymupdf`."
            )

        doc = fitz.open(pdf_path)
        text_pages: List[str] = []
        equations_raw: List[Dict[str, str]] = []

        for page_index, page in enumerate(doc):
            text_pages.append(page.get_text("text"))

            # ---- 매우 단순한 수식 후보 heuristic ----
            blocks = page.get_text("blocks")
            for b in blocks:
                s = b[4]
                line = s.strip()
                # '=' 포함 + 길이 제한 → 수식일 가능성
                if "=" in line and 3 < len(line) < 200:
                    equations_raw.append(
                        {
                            "page": page_index + 1,
                            "text": line,
                        }
                    )

        doc.close()

        full_text = "\n\n".join(text_pages)

        self.log(
            f"Loaded {len(text_pages)} pages, found ~{len(equations_raw)} equation candidates"
        )

        return {
            "pages": text_pages,
            "full_text": full_text,
            # 향후 섹션/그림/캡션을 넣고 싶으면 여기 key를 확장
            "equation_candidates": equations_raw,
        }


# ---------------------------------------------------------------------------
# Equation Extraction Agent
# ---------------------------------------------------------------------------
import re

def extract_json(text: str) -> str:
    """
    Extract the first JSON array/object substring from LLM output.
    Prevents JSON parsing errors when the model adds extra text.
    """
    match = re.search(r'(\{.*\}|\[.*\])', text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object/array found in LLM output.")
    return match.group(1)


class EquationExtractionAgent(BaseAgent):
    """
    Equation Extraction / Parsing Agent.

    역할(설계 상):
      - PDF에서 온 수식 후보 텍스트를 해석
      - 실제 수식인지 판별 (텍스트 설명/레퍼런스 제외)
      - 가능한 경우 LaTeX 형태로 정규화
      - 좌변(LHS)/우변(RHS) 분리
      - 사용된 변수/상수/연산자 추출
      - 미분/적분/지수/로그/경계조건/초기조건 등 연산 태그화
      - ODE/PDE/대수식/경계조건/초기조건 등 수식의 역할 분류
      - 좌변-우변 dependency 정보도 operations tag로 encoding

    구현 상 제약:
      - dataclass `Equation` 구조를 유지하기 위해
        세부 AST는 단일 필드로 두지 않고,
        operations 리스트에 태그 형태로 encode:
          예: ["diff:dC/dt", "ode", "boundary_condition", "exp", "multiplication"]
      - 수식 번호가 보이면 id에 반영:
          "(1)" → "Eq1" 등 (LLM에게 맡김)
    """

    SYSTEM_PROMPT = """
You are a **scientific equation extraction and parsing assistant** specialized in
atomic layer deposition (ALD) process / modeling papers.

You receive multiple short text snippets that may contain equations
copied from a PDF (often with missing formatting).

Your job is to perform the following, for **each snippet**:

1. **Decide if it is a real equation** (ignore pure text, references like "see Eq. (2)", etc.).
2. If it is NOT a usable equation, **skip it** (do not include it in the JSON output).
3. If it IS an equation, do ALL of the following:

   3-1. **Clean LaTeX reconstruction**
        - Reconstruct the equation as a clean, compilable LaTeX string.
        - If the snippet already looks like LaTeX, normalize spacing and symbols.
        - Ensure that fractions, exponents, subscripts, superscripts, and derivatives
          are clearly expressed, e.g., \frac{d\theta}{dt}, \partial C / \partial z, etc.

   3-2. **LHS / RHS separation**
        - Identify the left-hand side (LHS) and right-hand side (RHS) of the main equation.
        - If there is more than one '=', pick the one that best corresponds to the main
          mathematical statement. If ambiguous, choose the outermost / main equality.
        - Return LHS and RHS as plain strings (no need for full LaTeX, but they may contain LaTeX).

   3-3. **Variable symbol list**
        - Extract all **distinct variable symbols** appearing in the equation.
        - Symbols include:
            * scalar variables (C, T, t, z, k_ads, k_des, P_A, etc.)
            * vector/tensor symbols if any
            * parameters such as k_1, k_2, E_a, R, etc.
        - DO NOT include:
            * pure numbers
            * standard math constants like e, π
            * common function names like log, exp (those are operations, not variables).
        - Return them as a flat array of strings: ["C", "t", "k_ads", "k_des", "P_A", ...].

   3-4. **Operation / structure tagging (very important)**
        For each equation, analyze its mathematical structure and encode it as tags in
        the `operations` array. Use a combination of the following:

        - Basic operations:
            * "addition"
            * "subtraction"
            * "multiplication"
            * "division"
            * "exponent"
            * "log"
            * "exp"
            * "integral"
            * "diff" (for derivatives, both d/dt and partial)

        - Derivative structure:
            * If the equation contains time derivative d(...)/dt:
                - add "time_derivative"
                - and optionally a more specific tag like "diff:dC/dt"
            * If it contains spatial derivative (e.g., ∂C/∂z, ∂²T/∂z², etc.):
                - add "spatial_derivative"
                - and optionally "diff:d2T/dz2" or similar.

        - Equation type (ALD modeling relevant classification):
            * "ode"              : time-dependent ODE
            * "pde"              : PDE with time and/or space
            * "algebraic"        : purely algebraic (no derivative)
            * "boundary_condition"
            * "initial_condition"
            * "source_term"      : if it defines a source/sink term explicitly
            * "rate_expression"  : rate law (e.g., reaction rate, adsorption rate)
            * "constitutive"     : constitutive relation (e.g., flux law, kinetic law)

        - Dependency hints (optional but helpful):
            * For example, if the main unknown on LHS is dθ/dt and RHS depends on P_A and T,
              you may include:
                - "depends_on:P_A"
                - "depends_on:T"
              in the operations array.

   3-5. **Equation ID assignment**
        - Assign a stable ID:
            * If the snippet hints at an equation number "(1)", "(2)", etc., map it to:
                "Eq1", "Eq2", ...
            * Otherwise, use a generic ID like "Eq1", "Eq2", ... in the order you process.
        - IDs must be unique across all returned objects.

4. **Output format (very strict)**

Return ONLY a JSON array of objects, e.g.:

[
  {
    "id": "Eq1",
    "latex": "...",
    "lhs": "...",
    "rhs": "...",
    "variables": ["C", "t", "k_ads", "k_des"],
    "operations": ["diff", "time_derivative", "ode", "multiplication", "subtraction", "rate_expression"]
  },
  ...
]

- Do NOT include any fields other than: id, latex, lhs, rhs, variables, operations.
- Do NOT wrap in additional keys.
- If **no valid equations** exist in the snippets, return: []
"""

    def extract_equations(self, raw_data: Dict[str, Any]) -> List[Equation]:
        eq_candidates = raw_data.get("equation_candidates", [])
        if not eq_candidates:
            self.log("No equation candidates found in PDF", logging.WARNING)
            return []

        # 모든 snippet을 하나의 프롬프트로 묶어서 한 번에 처리
        candidate_strs: List[str] = []
        for idx, item in enumerate(eq_candidates, start=1):
            candidate_strs.append(
                f"Snippet {idx} (page {item['page']}):\n{item['text']}"
            )

        user_prompt = (
            "Below are text snippets from a PDF that may contain equations.\n"
            "Process ALL snippets and return JSON as instructed.\n\n"
            + "\n\n".join(candidate_strs)
        )

        raw_json = self.llm.complete(self.SYSTEM_PROMPT, user_prompt)

        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            self.log("LLM equation JSON parse failed; returning empty list", logging.ERROR)
            self.log(raw_json, logging.DEBUG)
            return []

        equations: List[Equation] = []
        for obj in parsed:
            eq = Equation(
                id=obj.get("id", ""),
                latex=obj.get("latex", ""),
                context="",  # TODO: 필요 시 page/문단 정보 attach
                lhs=obj.get("lhs"),
                rhs=obj.get("rhs"),
                variables=obj.get("variables", []),
                operations=obj.get("operations", []),
            )
            equations.append(eq)

        self.log(f"Extracted {len(equations)} structured equations")
        return equations


# ---------------------------------------------------------------------------
# Variable Definition Agent
# ---------------------------------------------------------------------------

class VariableDefinitionAgent(BaseAgent):
    """
    Variable Definition Agent.
    수식 변수들을 ALD 논문 전체 문맥에서 탐색하여:
      - 물리적 의미
      - 단위
      - 역할 (상태변수, 파라미터, 입력변수 등)
      - 정의가 등장한 문단/섹션
      - 정의 불명 시 inferred 라벨링

    특징:
      * 단순 “검색”이 아니라, 전체 문맥에서 semantic reasoning 수행
      * 식에서만 등장하는 심볼이라도 물리 시스템을 추론해 의미 부여
      * ALD domain-knowledge 기반 의미도 추정
    """

    SYSTEM_PROMPT = """
You are an **expert in ALD (Atomic Layer Deposition) physics and modeling**, acting as a
*Variable Definition & Semantic Extraction Agent*.

You will be given:
- Full raw text from an ALD scientific paper (up to ~15k characters).
- A list of variable names extracted from equations.

Your mission:
For **each variable**, produce the **best possible definition** from the paper context.

Rules & Capabilities:
1. SEARCH
   - Find explicit definitions in the text (e.g., “θ denotes surface coverage”, 
     “P_A is precursor partial pressure”, “k_ads is adsorption rate constant”).
   - Identify occurrences in body text, figure captions, tables, descriptions of models.

2. INFER
   - If not explicitly defined, infer meaning based on:
        * ALD kinetics (adsorption, desorption, transport)
        * Reactor models (plug flow, diffusion, ALD half-reactions)
        * Typical variables in ALD literature
   - Tag inferred meanings clearly with: "notes": "inferred from context"

3. UNITS
   - If units are described anywhere, extract them.
   - If unstated, infer reasonable units (e.g., “Pa”, “mol/m²”, “s⁻¹”, “nm/cycle”)
     and tag as inferred.

4. ROLE CLASSIFICATION
   - Identify whether the variable is:
        * "state_variable" (e.g., θ(t), coverage)
        * "input" (e.g., P_A, pulse time)
        * "parameter" (e.g., k_ads, E_a, sticking coefficient)
        * "intermediate" (derived variable)
        * "constant" (physical constants)
   - Add this info in “notes”.

5. LOCATION
   - Provide the approximate location (page # or section) of where the variable 
     appears or is defined if detectable from the text snippet.

Strict Output Format:
{
  "variables": [
    {
      "name": "C",
      "meaning": "...",
      "unit": "...",
      "notes": "...",
      "location": "page 3, paragraph mentioning Eq. (2)"
    },
    ...
  ]
}

If meaning not found → meaning: null & notes: "definition not found".
"""

    def define_variables(
        self,
        full_text: str,
        equations: List[Equation],
    ) -> Dict[str, VariableInfo]:

        # unique variable names
        vars_set = set()
        for eq in equations:
            for v in eq.variables:
                vars_set.add(v)
        var_list = sorted(vars_set)

        if not var_list:
            self.log("No variables to define", logging.WARNING)
            return {}

        user_prompt = (
            "Variables:\n" + ", ".join(var_list) +
            "\n\nFull paper text:\n" + full_text[:15000]
        )

        raw_json = self.llm.complete(self.SYSTEM_PROMPT, user_prompt)

        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            self.log("Variable definition JSON parse failed", logging.ERROR)
            self.log(raw_json, logging.DEBUG)
            return {}

        result: Dict[str, VariableInfo] = {}
        for obj in parsed.get("variables", []):
            info = VariableInfo(
                name=obj.get("name", ""),
                meaning=obj.get("meaning"),
                unit=obj.get("unit"),
                notes=obj.get("notes"),
                location=obj.get("location"),
            )
            if info.name:
                result[info.name] = info

        self.log(f"Defined {len(result)} variables")
        return result


# ---------------------------------------------------------------------------
# Relation Reasoning Agent
# ---------------------------------------------------------------------------

class RelationReasoningAgent(BaseAgent):
    """
    Relation Reasoning Agent.
    목적:
      - 모든 수식 간의 연결 구조를 분석하여 인과 관계 도출
      - 각 변수의 정성적 영향(positive/negative) 해석
      - 수식의 역할(ODE/PDE/경계조건/반응속도식/소스텀 등) 파악
      - system-level ALD process flow 추론:
            Inputs → Transport/Adsorption → Surface States → Growth

    강화된 기능:
      * 미분 형태를 보고 time-evolution, space-evolution 자동 분류
      * adsorption / desorption / reaction rate form 인식
      * Arrhenius law 형태 인식하여 T 영향성 판단
      * ALD half-cycle 구조까지 reasoning
    """

    SYSTEM_PROMPT = """
You are a **scientific causal-reasoning agent specializing in ALD (Atomic Layer Deposition)
modeling**. 

You receive:
- A list of structured equations (with LHS, RHS, variables, operations).
- Variable definitions (meaning, unit, notes).
- Relevant portions of the paper text.

Your tasks:

1. **Equation Role Identification**
   For each equation:
     - Determine whether it is:
         * "ode"                   (d/dt)
         * "pde"                   (∂/∂z, ∂/∂x)
         * "algebraic"
         * "rate_expression"
         * "constitutive"
         * "boundary_condition"
         * "initial_condition"
     - Determine the main solved quantity (e.g., dθ/dt, C(z), T(t)).

2. **Qualitative Influence**
   For each equation, examine how each variable affects the LHS variable.
     Example:
       dθ/dt = k_ads * P_A * (1 − θ) − k_des * θ
       → P_A : positive influence on dθ/dt
       → θ   : negative influence
       → k_ads: positive
       → k_des: negative

3. **Causal Dependencies**
   Produce relations of the form:
   {
     "type": "causal" | "depends_on" | "derived_from" |
             "boundary_condition" | "initial_condition",
     "source": "<variable or equation id>",
     "target": "<variable or equation id>",
     "equation_id": "<EqID>",
     "direction": "positive" | "negative" | "unknown",
     "description": "..."
   }

4. **Cross-Equation Linking**
   - If Eq1 outputs θ(t) and Eq2 uses θ, then Eq2 depends_on Eq1.
   - Detect chain relationships:
       P_A → θ(t) → GPC
       T → k_ads → θ(t)
       Transport → surface concentration → growth

5. **ALD-System Flow Reasoning**
   Using equations + definitions:
     - Identify input → state → output flow:
         Inputs:
           precursor pressure, pulse time, flow rate, temperature
         State variables:
           coverage θ, concentration C, surface species densities
         Outputs:
           GPC, film thickness, uniformity
     - Identify kinetic/transport bottlenecks.

Output Format (strict):
{
  "relations": [
    {
      "type": "...",
      "source": "...",
      "target": "...",
      "equation_id": "...",
      "direction": "...",
      "description": "..."
    },
    ...
  ]
}
"""

    def infer_relations(
        self,
        full_text: str,
        equations: List[Equation],
        var_defs: Dict[str, VariableInfo],
    ) -> List[Relation]:

        equations_payload = [
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
            "Equations:\n" + json.dumps(equations_payload, indent=2) +
            "\n\nVariable Definitions:\n" + json.dumps(var_payload, indent=2, ensure_ascii=False) +
            "\n\nPaper Text:\n" + full_text[:15000]
        )

        raw_json = self.llm.complete(self.SYSTEM_PROMPT, user_prompt)

        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            self.log("Relation JSON parse failed", logging.ERROR)
            self.log(raw_json, logging.DEBUG)
            return []

        relations: List[Relation] = []
        for obj in parsed.get("relations", []):
            relations.append(
                Relation(
                    type=obj.get("type", ""),
                    source=obj.get("source", ""),
                    target=obj.get("target", ""),
                    equation_id=obj.get("equation_id"),
                    direction=obj.get("direction"),
                    description=obj.get("description"),
                )
            )

        self.log(f"Inferred {len(relations)} relations")
        return relations


# ---------------------------------------------------------------------------
# Knowledge Graph Builder Agent
# ---------------------------------------------------------------------------

class KnowledgeGraphBuilderAgent(BaseAgent):
    """
    Knowledge Graph Builder.
    노드 종류:
      - variable
      - equation
      - parameter
      - concept (미래 확장용)
    엣지 종류:
      - causal
      - depends_on
      - derived_from
      - boundary_condition
      - initial_condition

    목적:
      * 단방향 directed graph 구축
      * 시각화/Neo4j/JSON-LD export 가능한 구조
    """

    def build_graph(
        self,
        equations: List[Equation],
        var_defs: Dict[str, VariableInfo],
        relations: List[Relation],
    ) -> KnowledgeGraph:

        kg = KnowledgeGraph()

        # ---- variable nodes ----
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

        # include variables not defined in text
        defined_names = set(var_defs.keys())
        for eq in equations:
            for v in eq.variables:
                if v not in defined_names:
                    kg.nodes.append(
                        KNode(
                            id=v,
                            type="variable",
                            label=v,
                            metadata={"meaning": None, "unit": None, "notes": "not defined in text"},
                        )
                    )
                    defined_names.add(v)

        # ---- equation nodes ----
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

        # ---- edges from relations ----
        for rel in relations:
            if rel.source and rel.target:
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

        self.log(
            f"Built Knowledge Graph with {len(kg.nodes)} nodes and {len(kg.edges)} edges"
        )
        return kg


# ---------------------------------------------------------------------------
# Consistency Checker Agent
# ---------------------------------------------------------------------------

class ConsistencyCheckerAgent(BaseAgent):
    """
    Consistency Checker.
    점검 리스트:
      - 정의되지 않은 변수 존재?
      - 변수 이름 충돌?
      - 수식에 변수 없음?
      - KG edge가 유효한 node 참조?
      - 시간/공간 파생항 있는데 초기/경계 조건 빠짐?
      - ALD 모델 폐포성(closure) 문제?
    """

    def check(
        self,
        equations: List[Equation],
        var_defs: Dict[str, VariableInfo],
        kg: KnowledgeGraph,
    ) -> Dict[str, Any]:

        issues: List[str] = []

        used_vars = set()
        for eq in equations:
            used_vars.update(eq.variables)

        defined_vars = set(var_defs.keys())
        undefined = used_vars - defined_vars
        if undefined:
            issues.append(f"Warning: Variables used but not defined: {sorted(undefined)}")

        # equation with no variables
        for eq in equations:
            if not eq.variables:
                issues.append(f"Equation {eq.id} contains no variables.")

        # broken edges
        node_ids = {n.id for n in kg.nodes}
        for e in kg.edges:
            if e.source not in node_ids:
                issues.append(f"Edge source {e.source} not found.")
            if e.target not in node_ids:
                issues.append(f"Edge target {e.target} not found.")

        self.log(f"Consistency check found {len(issues)} issues.")
        return {"issues": issues}


# ---------------------------------------------------------------------------
# Interpreter Agent
# ---------------------------------------------------------------------------

class InterpreterAgent(BaseAgent):
    """
    Interpreter Agent.
    목적:
      - Knowledge graph + equations를 기반으로
        ALD 모델의 핵심 구조를 설명하는 narrative 생성
      - 사용자 친화적 설계:
         * State / Input / Parameter 분리
         * 식 간 연결 구조 설명
         * Growth per cycle (GPC) 등 output로의 흐름 설명
         * Gradient-based simulation 가능 부분 표시
    """

    SYSTEM_PROMPT = """
You are an **expert ALD modeling analyst**. Your job is to turn a structured model
(knowledge graph + equations + variable definitions) into a clean, engineering-level
explanation.

Your explanation should cover:

1. **State Variables**
   - e.g., surface coverage θ(t), species concentration C(t,z), temperature field T(z,t)

2. **Inputs / Controls**
   - precursor partial pressure, pulse time, flow rate, substrate temperature,
     carrier gas flow, reactor geometry assumptions.

3. **Parameters**
   - kinetic rate constants, sticking coefficients, activation energy, diffusion coefficients.

4. **Equation Roles**
   - which equations describe:
       * adsorption kinetics
       * desorption kinetics
       * ligand-exchange reactions
       * transport equations
       * PDE/ODE structure
       * boundary/initial conditions
   - describe the ALD half-cycle if derivable:
       A-pulse → purge → B-pulse → purge

5. **Causal Flow**
   - Inputs → intermediate kinetics → surface coverage evolution → GPC → film thickness

6. **Differentiability / Simulation**
   - which components are differentiable
   - which parts enable gradient-based optimization
   - chain of derivatives (e.g., dGPC/dP_A via θ(t)).

Format:
- Use bullet points.
- Keep paragraphs short.
- Be precise and domain-correct.
"""

    def interpret(
        self,
        equations: List[Equation],
        var_defs: Dict[str, VariableInfo],
        relations: List[Relation],
        kg: KnowledgeGraph,
        language: str = "en",
    ) -> str:

        payload = {
            "equations": [
                {
                    "id": eq.id,
                    "latex": eq.latex,
                    "lhs": eq.lhs,
                    "rhs": eq.rhs,
                    "variables": eq.variables,
                }
                for eq in equations
            ],
            "variables": {
                name: {
                    "meaning": v.meaning,
                    "unit": v.unit,
                    "notes": v.notes,
                    "location": v.location,
                }
                for name, v in var_defs.items()
            },
            "relations": [asdict(r) for r in relations],
            "knowledge_graph": {
                "nodes": [asdict(n) for n in kg.nodes],
                "edges": [asdict(e) for e in kg.edges],
            },
        }

        user_prompt = (
            "ALD Model JSON:\n\n" +
            json.dumps(payload, indent=2, ensure_ascii=False)
        )

        explanation_en = self.llm.complete(self.SYSTEM_PROMPT, user_prompt)

        if language.lower().startswith("ko"):
            translator_system = "Translate this ALD model explanation into technical Korean."
            explanation_ko = self.llm.complete(translator_system, explanation_en)
            return explanation_ko

        return explanation_en


# ---------------------------------------------------------------------------
# Orchestrator: ALDModelingCoPilot
# ---------------------------------------------------------------------------

@dataclass
class ALDModelingResult:
    equations: List[Equation]
    variables: Dict[str, VariableInfo]
    relations: List[Relation]
    knowledge_graph: KnowledgeGraph
    consistency_report: Dict[str, Any]
    explanation: str


class ALDModelingCoPilot:
    """
    ALD Modeling Co-Pilot
    ------------------------------------------------------
    멀티에이전트 파이프라인 전체를 orchestration하는 상위 클래스.

    Pipeline:
      1) PDFLoaderAgent          - PDF → raw text, equation candidates
      2) EquationExtractionAgent  - equation candidates → structured LaTeX eqs
      3) VariableDefinitionAgent  - variables semantic extraction
      4) RelationReasoningAgent   - causal relation inference
      5) KnowledgeGraphBuilder    - graph construction
      6) ConsistencyChecker       - static analysis
      7) InterpreterAgent         - final narrative explanation
    """

    def __init__(self, model: str = "gpt-5.1", max_tokens: int = 4000):
        llm = LLMClient(model=model, max_tokens=max_tokens)

        self.pdf_loader = PDFLoaderAgent(llm=None)   # no LLM needed
        self.eq_extractor = EquationExtractionAgent(llm=llm)
        self.var_def_agent = VariableDefinitionAgent(llm=llm)
        self.rel_agent = RelationReasoningAgent(llm=llm)
        self.kg_builder = KnowledgeGraphBuilderAgent(llm=None)
        self.consistency_checker = ConsistencyCheckerAgent(llm=None)
        self.interpreter = InterpreterAgent(llm=llm)

    def run(self, pdf_path: str | Path, language: str = "en") -> ALDModelingResult:
        """
        Execute the full multi-agent pipeline.
        """

        # 1) PDF Load
        raw_pdf = self.pdf_loader.load_pdf(pdf_path)
        full_text = raw_pdf["full_text"]

        # 2) Extract equations
        equations = self.eq_extractor.extract_equations(raw_pdf)

        # 3) Variable definitions
        var_defs = self.var_def_agent.define_variables(full_text, equations)

        # 4) Relation inference
        relations = self.rel_agent.infer_relations(full_text, equations, var_defs)

        # 5) Knowledge graph
        kg = self.kg_builder.build_graph(equations, var_defs, relations)

        # 6) Consistency check
        consistency = self.consistency_checker.check(equations, var_defs, kg)

        # 7) Interpretation (English or Korean)
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


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ALD Modeling Co-Pilot: Auto-scan ./pdfs and build knowledge graphs."
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5.1",
        help="LLM model name"
    )

    parser.add_argument(
        "--language",
        type=str,
        default="ko",
        choices=["en", "ko"],
        help="Output language"
    )

    parser.add_argument(
        "--outdir",
        type=str,
        default="ald_modeling_outputs",
        help="Output directory"
    )

    args = parser.parse_args()

    # --- 자동으로 스크립트 기준 ./pdfs 폴더를 읽는다 ---
    script_dir = Path(__file__).resolve().parent
    pdfdir = script_dir / "pdfs"

    if not pdfdir.exists():
        raise RuntimeError(f"PDF directory not found: {pdfdir}")

    pdf_files = list(pdfdir.glob("*.pdf"))
    if not pdf_files:
        raise RuntimeError(f"No PDF files found in {pdfdir}")

    copilot = ALDModelingCoPilot(model=args.model)

    for pdf in pdf_files:
        print(f"\n=== Processing {pdf.name} ===")
        result = copilot.run(pdf, language=args.language)

        sub_out = Path(args.outdir) / pdf.stem
        sub_out.mkdir(parents=True, exist_ok=True)

        (sub_out / "equations.json").write_text(
            json.dumps([asdict(eq) for eq in result.equations], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        (sub_out / "variables.json").write_text(
            json.dumps({k: asdict(v) for k, v in result.variables.items()}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        (sub_out / "relations.json").write_text(
            json.dumps([asdict(r) for r in result.relations], indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        (sub_out / "knowledge_graph.json").write_text(
            result.knowledge_graph.to_json(),
            encoding="utf-8"
        )
        (sub_out / "consistency_report.json").write_text(
            json.dumps(result.consistency_report, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        (sub_out / "explanation.txt").write_text(
            result.explanation,
            encoding="utf-8"
        )

        print(f"Saved output → {sub_out}")


if __name__ == "__main__":
    main()
