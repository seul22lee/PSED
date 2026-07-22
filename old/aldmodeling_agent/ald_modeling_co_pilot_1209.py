"""
Equation & Variable Co-Pilot base (pre-agent utilities).

This module prepares the infrastructure for a multi-agent system that will:
- Read scientific PDFs (e.g., ALD / atomic layer deposition modeling papers),
- Extract variables and equations,
- Build a knowledge graph over variables, equations, and their relations.

This file only contains the "pre-agent" layer:
- RAG helpers (PDF/TXT ingestion and chunking)
- Simple in-memory vector store with OpenAI embeddings
- Logging helpers
- Shared helpers to call text LLMs and vision LLMs
"""

import os
import json
import base64
import mimetypes
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# Optional PDF parser for ingestion; not required for the core workflow.
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# The client expects the environment variable OPENAI_API_KEY to be set.
load_dotenv()
client = OpenAI()

COMMUNICATION_LOG_PATH = "agent_communication_log.txt"
FINAL_ANSWER_PATH = "final_answer.txt"

# RAG upload folders (same idea as manufacturing co-pilot)
RAG_ROOT = Path(__file__).resolve().parent / "rags"
PDF_DIR = RAG_ROOT / "pdf"
TXT_DIR = RAG_ROOT / "txt"


# --------------------------------------------------------------------
# Data containers, RAG helpers, vector store, and RAG retriever
# --------------------------------------------------------------------


@dataclass
class Document:
    """
    Simple container for a single knowledge item.

    Parameters
    ----------
    text
        Natural language content of the document
        (can also contain LaTeX equations, variable tables, etc.).
    metadata
        Optional dictionary with additional information, for example
        source filename, page number, chunk index, or document type.
    """

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def ensure_rag_dirs() -> Tuple[Path, Path]:
    """
    Create the RAG upload folders if they do not exist.

    Returns
    -------
    Tuple[Path, Path]
        Paths to the PDF and TXT upload directories.
    """
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    return PDF_DIR, TXT_DIR


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    """
    Read a PDF as raw text.

    Note
    ----
    This uses pypdf's text extraction which is layout-agnostic and can
    lose some formatting, especially for equations. This is still useful
    for textual context. For high-quality equation / table extraction
    you will typically also use a vision model on rendered page images.
    """
    if PdfReader is None:
        raise RuntimeError(
            "PDF ingestion requires the 'pypdf' package. Install with `pip install pypdf`."
        )
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def chunk_text(text: str, max_tokens: int = 2000) -> List[str]:
    """
    Simple text chunker to ensure documents stay below the
    embedding model's maximum context length (~8192 tokens).

    Here we approximate tokens with word count, which is enough for
    prototyping.

    Splits long text into smaller chunks so each can be embedded safely.
    """
    words = text.split()
    chunks: List[str] = []
    current_words: List[str] = []

    for w in words:
        current_words.append(w)
        # crude heuristic token count = #words
        if len(current_words) >= max_tokens:
            chunks.append(" ".join(current_words))
            current_words = []

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def load_rag_documents() -> List[Document]:
    """
    Load all TXT and PDF files from the RAG upload folders into Document objects.

    This forms the base RAG corpus. Later agents (Variable/Equation extractors,
    Relation Reasoning, etc.) can:
    - query this corpus via the vector store,
    - and add more specialized Documents (variable definitions, equation
      summaries, etc.) on top.

    Returns
    -------
    List[Document]
        Documents with text content and simple metadata (filename and source type).

    Raises
    ------
    RuntimeError
        If PDF files are present but the pypdf dependency is missing.
    """
    ensure_rag_dirs()

    docs: List[Document] = []

    # TXT files
    for txt_path in sorted(TXT_DIR.glob("*.txt")):
        docs.append(
            Document(
                text=_read_txt(txt_path),
                metadata={
                    "filename": txt_path.name,
                    "source_type": "txt",
                },
            )
        )

    # PDF files
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if pdf_files and PdfReader is None:
        raise RuntimeError(
            "PDF files detected, but 'pypdf' is not installed. "
            "Install it with `pip install pypdf` to ingest PDFs."
        )

    for pdf_path in pdf_files:
        full_text = _read_pdf(pdf_path)
        chunks = chunk_text(full_text, max_tokens=2000)

        for i, ch in enumerate(chunks):
            docs.append(
                Document(
                    text=ch,
                    metadata={
                        "filename": pdf_path.name,
                        "chunk_index": i,
                        "source_type": "pdf",
                    },
                )
            )

    return docs


class SimpleVectorStore:
    """
    Very small in memory vector store.

    This class is only meant for prototyping. It stores all document
    embeddings in memory and uses cosine similarity for retrieval.

    In your equation/variable co-pilot, you can use this store for:
    - raw text chunks from PDFs,
    - variable definition snippets,
    - equation summaries (LaTeX + context),
    - any other derived knowledge you want to retrieve via RAG.

    Parameters
    ----------
    embedding_model
        Name of the OpenAI embedding model to use.
    """

    def __init__(self, embedding_model: str = "text-embedding-3-large"):
        self.embedding_model = embedding_model
        self.docs: List[Document] = []
        self.embeddings: Optional[np.ndarray] = None

    # --------------- internal helpers ---------------

    def _embed(self, texts: List[str]) -> np.ndarray:
        """
        Compute embeddings for a list of texts using the chosen OpenAI model.
        """
        response = client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        vectors = [item.embedding for item in response.data]
        return np.array(vectors, dtype="float32")

    # --------------- public API ---------------

    def add_documents(self, docs: List[Document]) -> None:
        """
        Add a list of documents to the store and build their embeddings.
        """
        if not docs:
            return

        self.docs.extend(docs)
        new_emb = self._embed([d.text for d in docs])

        if self.embeddings is None:
            self.embeddings = new_emb
        else:
            self.embeddings = np.vstack([self.embeddings, new_emb])

    def search(self, query: str, k: int = 5) -> List[Document]:
        """
        Retrieve the top k most similar documents to the query text.

        Similarity is measured using cosine similarity in the embedding space.

        Later, you can query this with:
        - variable symbols (e.g. "D[Kn]", "theta[eq]"),
        - equation fragments or LaTeX,
        - natural language queries ("Knudsen diffusion equation").
        """
        if not self.docs or self.embeddings is None:
            return []

        q_vec = self._embed([query])[0]

        # Cosine similarity between query and all stored vectors
        sims = (self.embeddings @ q_vec) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(q_vec) + 1e-8
        )

        indices = np.argsort(-sims)[:k]
        return [self.docs[i] for i in indices]


# --------------------------------------------------------------------
# Logging helpers
# --------------------------------------------------------------------


def reset_communication_log(path: str = COMMUNICATION_LOG_PATH) -> None:
    header = (
        "Equation & Variable Co-Pilot agent communication log\n"
        f"Started: {datetime.utcnow().isoformat()}Z\n\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)


def log_agent_message(
    agent: str,
    message: Any,
    path: str = COMMUNICATION_LOG_PATH,
) -> None:
    """
    Simple append-only log for debugging / traceability of multi-agent runs.
    """
    if isinstance(message, (dict, list)):
        body = json.dumps(message, indent=2, ensure_ascii=False)
    else:
        body = str(message)

    entry = f"[{datetime.utcnow().isoformat()}Z] {agent}\n{body}\n\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


def write_final_answer(text: str, path: str = FINAL_ANSWER_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# --------------------------------------------------------------------
# Shared helper for calling text models
# --------------------------------------------------------------------


def call_text_model(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-5.1",
    json_only: bool = False,
) -> Any:
    """
    Helper around the Responses API for text-only interactions.

    This is the generic text LLM caller. Later, your agents such as
    - Variable Extractor,
    - Equation Extractor,
    - Relation Reasoning Agent,
    will build their own system_prompt + user_prompt and call this helper.

    Parameters
    ----------
    system_prompt
        Instructions for the assistant.
    user_prompt
        Content that describes the task or question.
    model
        OpenAI model name. Uses GPT-5.1 by default.
    json_only
        When True, the function asks the model to return valid JSON and
        parses the result before returning it.

    Returns
    -------
    Either a plain string (for free-form text) or a Python object parsed from JSON.
    """
    if json_only:
        user_prompt = user_prompt + "\n\nReturn only valid JSON, no extra text."

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = response.output_text

    if json_only:
        return json.loads(text)
    return text


# --------------------------------------------------------------------
# Generic Vision Model Caller (for variable extraction, equations, etc)
# --------------------------------------------------------------------

def call_vision_model_generic(
    image_path_or_url: str,
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-5.1",
    json_only: bool = True,
):
    """
    Generic wrapper to call Vision LLM with custom system/user prompts.

    This version is not CAD-specific and is suited for scientific parsing tasks
    such as:
    - nomenclature extraction
    - equation extraction
    - variable recognition
    - diagram reading
    """

    # prepare the image as base64 data URL or passthrough URL
    def _prepare_image_url(image_path_or_url: str) -> str:
        if image_path_or_url.startswith(("http://", "https://", "data:")):
            return image_path_or_url

        if os.path.exists(image_path_or_url):
            mime, _ = mimetypes.guess_type(image_path_or_url)
            mime = mime or "image/png"
            with open(image_path_or_url, "rb") as f:
                data_b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime};base64,{data_b64}"

        raise ValueError(f"Image path or URL is invalid: {image_path_or_url}")

    img_url = _prepare_image_url(image_path_or_url)

    content = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": user_prompt},
                {"type": "input_image", "image_url": img_url},
            ],
        },
    ]

    if json_only:
        content.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": "Return only valid JSON."}],
            }
        )

    response = client.responses.create(
        model=model,
        input=content,
    )
    text = response.output_text
    return json.loads(text) if json_only else text




# --------------------------------------------------------------------
# Vision Variable Extractor Agent
# --------------------------------------------------------------------

def vision_variable_extractor_agent(
    nomenclature_image_path: str,
    vector_store: SimpleVectorStore,
    model: str = "gpt-5.1",
) -> List[Dict[str, Any]]:
    """
    Extract variables, canonical symbols, descriptions, and units
    from a nomenclature image using Vision LLM.

    Parameters
    ----------
    nomenclature_image_path : str
        Path to nomenclature.png inside the pdfs folder.
    vector_store : SimpleVectorStore
        Vector store to save variable documents into.
    model : str
        OpenAI model supporting vision inputs.

    Returns
    -------
    List[Dict[str, Any]]
        A list of variable dictionaries:
        {
            "symbol_raw": ...,
            "canonical_symbol": ...,
            "description": ...,
            "unit": ...,
            "source": "nomenclature"
        }
    """

    # Vision LLM prompt
    system_prompt = """
You are a scientific document parsing agent.
You read nomenclature tables from research papers.

Your job:
1. Read the image of the nomenclature (variable dictionary).
2. Identify all variables EXACTLY as they appear, preserving subscripts.
3. For each variable, extract:
   - symbol_raw: the exact symbol as seen in the image
   - canonical_symbol: a normalized form using only ASCII characters
       Examples:
       d_A → d[A]
       D_Kn → D[Kn]
       θ_eq → theta[eq]
       p_A0 → p[A0]
       g_PC → g[PC]
   - description: the meaning of the variable
   - unit: physical unit (if present), otherwise null
4. Output strictly JSON list of objects.
"""

    user_prompt = """
Please extract all variables from this nomenclature image.

Guidelines:
- Preserve Greek letters if possible (e.g., θ → theta).
- ALWAYS produce canonical_symbol using only ASCII a–z, A–Z, 0–9, and [].
- NEVER invent variables; only extract what appears in the image.

Return output as:
[
  { "{ \"symbol_raw\": string, \"canonical_symbol\": string, \"description\": string, \"unit\": string or null }" },
  ...
]

Image of nomenclature is provided below.
"""

    # Run vision model
    result = call_vision_model_generic(
        image_path_or_url=nomenclature_image_path,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        json_only=True,
    )

    # Example result:
    # [
    #   { "symbol_raw": "D_eff", "canonical_symbol": "D[eff]", "description": "Effective diffusion coefficient", "unit": "m^2/s" },
    #   ...
    # ]

    variable_list = result

    # ---------------------------------------------------------
    # Save each variable as a Document into vector_store
    # ---------------------------------------------------------
    documents_to_add = []

    for var in variable_list:
        symbol_raw = var.get("symbol_raw")
        canonical = var.get("canonical_symbol")
        desc = var.get("description", "")
        unit = var.get("unit", None)

        # Build a text block representing this variable knowledge
        doc_text = (
            f"Variable: {canonical}\n"
            f"Raw symbol: {symbol_raw}\n"
            f"Description: {desc}\n"
            f"Unit: {unit}\n"
            f"Source: nomenclature image\n"
        )

        doc = Document(
            text=doc_text,
            metadata={
                "type": "variable_definition",
                "symbol_raw": symbol_raw,
                "canonical_symbol": canonical,
                "unit": unit,
                "description": desc,
                "source": "nomenclature",
            },
        )

        documents_to_add.append(doc)

    # Store all variable definitions in vector store
    vector_store.add_documents(documents_to_add)

    return variable_list



# ============================================================
# Equation Extraction Agent (Vision 기반, 번호 있는 식만)
# ============================================================

import re
import fitz  # PyMuPDF for page rendering


def render_pdf_pages_to_images(pdf_path: Path, dpi: int = 200) -> List[Path]:
    """
    PDF를 페이지별 PNG 이미지로 렌더링한다.

    Parameters
    ----------
    pdf_path : Path
        ./document 안의 PDF 경로
    dpi : int
        렌더링 해상도

    Returns
    -------
    List[Path]
        각 페이지의 PNG 파일 경로 리스트
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))

    pages_dir = pdf_path.parent / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    image_paths: List[Path] = []

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(dpi=dpi)
        out_path = pages_dir / f"{pdf_path.stem}_p{page_index+1}.png"
        pix.save(str(out_path))
        image_paths.append(out_path)

    return image_paths


def vision_equation_extractor_agent(
    pdf_path: str,
    vector_store: SimpleVectorStore,
    model: str = "gpt-5.1",
    max_equations: int = 5,
) -> List[Dict[str, Any]]:
    """
    Vision LLM을 사용해서 PDF에서 '번호가 붙은' block equations만 추출한다.

    흐름
    ----
    1. PDF → 페이지 이미지 렌더링
    2. 각 페이지를 Vision LLM에 보내서:
       - display-style equation + 번호 (예: (1), (8), (45))만 추출
       - inline reference "Eq. (1)" 같은 것은 무시
    3. 전체 식을 번호 기준으로 정렬 후, 앞 max_equations개만 선택
    4. 선택된 식들을 vector_store에 Document로 저장

    Parameters
    ----------
    pdf_path : str
        ./document 안에 있는 PDF 파일 경로
    vector_store : SimpleVectorStore
        식 정보를 저장할 vector store
    model : str
        Vision을 지원하는 OpenAI 모델 이름 (예: gpt-5.1)
    max_equations : int
        최종적으로 상위 몇 개 식까지만 사용할지 (테스트용 5개 등)

    Returns
    -------
    List[Dict[str, Any]]
        [
          {
            "eq_number": 1,
            "number_str": "(1)",
            "latex": "...",
            "page_index": 0,
            "page_image": "..."
          },
          ...
        ]
    """

    pdf_path = Path(pdf_path)

    # 1) PDF → page images
    page_images = render_pdf_pages_to_images(pdf_path, dpi=200)

    all_equations: List[Dict[str, Any]] = []

    # 2) 각 페이지별 Vision 호출
    system_prompt = """
You are a scientific equation extraction engine.

You receive a full page image from a scientific article.

Your task:

1. Find ONLY display-style equations that have an explicit equation number
   like (1), (8), (23), normally printed to the right of the equation.
   - Ignore any text citations like "Eq. (1)" inside paragraphs.
   - Ignore inline math inside sentences.

2. For each such numbered equation, extract:
   - number_str: the number exactly as printed, e.g. "(1)"
   - eq_number: the integer index, e.g. 1
   - latex: a clean LaTeX representation of the equation body
            (do NOT include the number in LaTeX).

3. If there are no numbered equations on the page, return an empty list.

Output MUST be STRICT JSON of the form:

{
  "equations": [
    {
      "number_str": "(1)",
      "eq_number": 1,
      "latex": "..."
    }
  ]
}
"""

    user_prompt = """
Extract all DISPLAY-STYLE numbered equations from this page.

Constraints:
- Only equations that are visually separated from text (block equations).
- The equation must have a number like (n) printed near it.
- Ignore references like "Eq. (1)" or "(see 10)" inside text paragraphs.

Return STRICT JSON as described.
"""

    for page_index, img_path in enumerate(page_images):
        try:
            result = call_vision_model_generic(
                image_path_or_url=str(img_path),
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                json_only=True,
            )
        except Exception as e:
            print(f"[WARN] Vision call failed on page {page_index+1}: {e}")
            continue

        eq_list = result.get("equations", [])
        if not isinstance(eq_list, list):
            continue

        for eq in eq_list:
            number_str = eq.get("number_str") or eq.get("number") or ""
            # eq_number 보정: number_str에서 숫자만 추출
            eq_number = eq.get("eq_number", None)
            if eq_number is None:
                m = re.search(r"\d+", str(number_str))
                if m:
                    eq_number = int(m.group(0))
                else:
                    # 번호를 못 읽으면 skip
                    continue

            latex = eq.get("latex", "").strip()
            if not latex:
                continue

            all_equations.append(
                {
                    "eq_number": int(eq_number),
                    "number_str": str(number_str),
                    "latex": latex,
                    "page_index": page_index,
                    "page_image": str(img_path),
                    "source_pdf": pdf_path.name,
                }
            )

    if not all_equations:
        print("[INFO] No numbered equations found.")
        return []

    # 3) 번호 기준 정렬 후 앞 max_equations개만 사용
    all_equations.sort(key=lambda e: e["eq_number"])
    selected = all_equations[:max_equations]

    # 4) vector_store에 Document로 저장
    docs_to_add: List[Document] = []
    for eq in selected:
        text_block = (
            f"Equation ({eq['eq_number']}) from {eq['source_pdf']}, "
            f"page {eq['page_index']+1}.\n"
            f"LaTeX: {eq['latex']}\n"
        )
        doc = Document(
            text=text_block,
            metadata={
                "type": "equation",
                "eq_number": eq["eq_number"],
                "number_str": eq["number_str"],
                "latex": eq["latex"],
                "page_index": eq["page_index"],
                "source_pdf": eq["source_pdf"],
                "page_image": eq["page_image"],
            },
        )
        docs_to_add.append(doc)

    vector_store.add_documents(docs_to_add)

    return selected



# ===========================================================
#  Equation → Variable Mapping Agent (Agent #4)
# ===========================================================

class AgentLoggerMixin:
    def log(self, agent_name: str, filename: str, data: Any):
        out = Path("./outputs/agent_logs")
        out.mkdir(parents=True, exist_ok=True)
        fp = out / f"{agent_name}__{filename}.json"
        with open(fp, "w", encoding="utf8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class Agent(AgentLoggerMixin):
    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


import re
import json
from typing import Dict, Any, List

class EquationVariableMappingAgent(Agent, AgentLoggerMixin):

    SYSTEM_PROMPT = """
You are an ALD scientific equation variable-mapping engine.

You will receive:
1. A LaTeX equation string
2. A list of raw variable candidates extracted with regex
3. A nomenclature dictionary giving canonical variable forms

Your tasks:
1. Remove false positives (exp, ln, sin, cos, sqrt, log, min, max, etc.)
2. Identify which of the candidates are REAL scientific variables
3. Map each real variable to canonical form using the nomenclature
4. Extract the LHS-defined variable if the equation is of form "X = ..."

Rules:
- Variables may include subscripts (e.g., D_A, p_A0, x_s)
- Greek letters such as θ must map to canonical form (theta)
- If the symbol is not in the nomenclature, include it but mark canonical as null
- Return strict JSON only.

JSON schema:
{
  "variables": [
      { "symbol_raw": "...", "canonical": "...", "is_valid": true }
  ],
  "defines": "target_variable_or_null"
}
"""

    def __init__(self, model: str = "gpt-5.1"):
        self.model = model   # using Responses API model name

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:

        eqs_by_pdf = ctx.get("equations", {})
        vars_by_pdf = ctx.get("variables_nomenclature", {})  # MUST exist
        out = {}

        for pdf_name, eq_list in eqs_by_pdf.items():

            mapped_results = []
            nomenclature_dict = vars_by_pdf.get(pdf_name, {})

            for eq in eq_list:

                latex = eq.get("latex", "")
                eq_id = eq.get("id")

                # --------------------------------------
                # 1) Regex candidate extraction
                # --------------------------------------
                candidates = re.findall(r"[A-Za-z][A-Za-z0-9,_]*", latex)

                # --------------------------------------
                # 2) Build prompt
                # --------------------------------------
                user_payload = {
                    "latex": latex,
                    "candidates": candidates,
                    "nomenclature": nomenclature_dict
                }
                user_prompt = json.dumps(user_payload, indent=2)

                # --------------------------------------
                # 3) LLM call via call_text_model()
                # --------------------------------------
                raw = call_text_model(
                    system_prompt=self.SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model=self.model,
                    json_only=False  # because we will manually parse
                )

                # --------------------------------------
                # 4) JSON extraction
                # --------------------------------------
                m = re.search(r"\{[\s\S]*\}", raw)
                if not m:
                    self.log("EqVarMap_raw_fail", eq_id, raw)
                    continue

                try:
                    data = json.loads(m.group(0))
                except Exception as e:
                    self.log("EqVarMap_json_error", eq_id, {"error": str(e), "raw": raw})
                    continue

                # --------------------------------------
                # 5) Merge results
                # --------------------------------------
                mapped_results.append({
                    "eq_id": eq_id,
                    "latex": latex,
                    "page": eq.get("page"),
                    "variables": data.get("variables", []),
                    "defines": data.get("defines")
                })

                self.log("EqVarMap", eq_id, mapped_results[-1])

            out[pdf_name] = mapped_results

        ctx["equation_variable_mapping"] = out
        return ctx




# ===========================================================
#   Text Knowledge Extraction Agent
# ===========================================================

class TextKnowledgeExtractionAgent(Agent, AgentLoggerMixin):

    SYSTEM_PROMPT = """
You are an ALD scientific knowledge extraction engine.

Input: A single sentence from a research paper + a list of known variables.

Your tasks:
1. Detect all variable mentions (raw form).
2. Map each mention to canonical form using the provided list.
3. Determine if the sentence DEFINES a variable.
4. Determine if the sentence expresses a RELATION between variables.
   Relations include:
   - increases_with
   - decreases_with
   - proportional
   - inverse_proportional
   - approaches
   - equals
   - affects
5. Produce strict JSON:
{
  "variable_mentions": [...],
  "variable_definitions": [...],
  "relationships": [...]
}
IMPORTANT:
- Output JSON ONLY.
- If nothing found, output empty lists.
"""

    def __init__(self, model="gpt-5.1"):
        self.model = model

    def _llm_extract(self, sentence: str, canonical_list: List[str]):
        user_prompt = json.dumps({
            "sentence": sentence,
            "variables": canonical_list
        }, indent=2)

        raw = call_text_model(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=self.model,
            json_only=False
        )

        # extract JSON safely
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return {
                "variable_mentions": [],
                "variable_definitions": [],
                "relationships": []
            }

        try:
            return json.loads(m.group(0))
        except:
            return {
                "variable_mentions": [],
                "variable_definitions": [],
                "relationships": []
            }

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:

        sentences_by_pdf = ctx.get("text_sentences", {})
        variables_by_pdf = ctx.get("variables_nomenclature", {})

        outputs = {}

        for pdf_name, sentences in sentences_by_pdf.items():

            # Prepare canonical list
            nom = variables_by_pdf.get(pdf_name, {})
            canonical_list = list(nom.values())

            pdf_results = []

            for sent in sentences:
                result = self._llm_extract(sent, canonical_list)

                if (result["variable_mentions"] or
                    result["variable_definitions"] or
                    result["relationships"]):
                    pdf_results.append({
                        "sentence": sent,
                        "result": result
                    })

            outputs[pdf_name] = pdf_results

        ctx["text_knowledge"] = outputs
        return ctx






# ===========================================================
#  Relation Reasoning Agent
#  - equation ↔ variable
#  - variable ↔ variable
#  - equation ↔ equation (via shared variables)
#  - text 기반 관계 통합
# ===========================================================

class RelationReasoningAgent(Agent, AgentLoggerMixin):
    """
    입력으로 사용하는 ctx 구조

    ctx["equation_variable_mapping"] = {
        "test.pdf": [
            {
                "eq_id": "eq1",
                "latex": "D_A = \\frac{n_A}{p_{A0}} + \\theta",
                "page": 3,
                "variables": [
                    {"symbol_raw": "D_A", "canonical": "D[A]", "is_valid": true},
                    ...
                ],
                "defines": "D[A]"
            },
            ...
        ]
    }

    ctx["text_knowledge"] = {
        "test.pdf": [
            {
                "sentence": "...",
                "result": {
                    "variable_mentions": [...],
                    "variable_definitions": [...],
                    "relationships": [...]
                }
            },
            ...
        ]
    }

    출력:

    ctx["relations"] = {
        "test.pdf": [
            {
                "source": "D[A]",
                "target": "D[eff]",
                "type": "equation_depends_on",
                "direction": "unknown",
                "equation_id": "eq3",
                "evidence_type": "equation",
                "evidence": "D_eff = ..."
            },
            {
                "source": "theta",
                "target": "p[A]",
                "type": "text_increases_with",
                "direction": "positive",
                "evidence_type": "text",
                "evidence": "The surface coverage θ increases when p_A increases."
            },
            {
                "source": "eq1",
                "target": "eq3",
                "type": "equation_to_equation",
                "direction": "unknown",
                "via_variable": "D[A]",
                "evidence_type": "equation_dependency"
            },
            ...
        ]
    }
    """

    # -------------------------------------------------------
    # 🔥 Text 관계 타입 정규화를 위한 keyword 테이블
    #    - TextKnowledgeExtractionAgent가 반환하는 r["type"]
    #      값을 더 표준적인 label로 매핑할 때 사용
    #    - 필요하면 여기에 계속 추가해 나가면 됨
    # -------------------------------------------------------
    RELATION_KEYWORDS = {
        "increase":       "positive_correlation",
        "increases":      "positive_correlation",
        "decrease":       "negative_correlation",
        "decreases":      "negative_correlation",
        "proportional":   "proportional",
        "inversely":      "inverse_proportional",
        "dependent":      "dependency",
        "depends":        "dependency",
        "ratio":          "ratio_relation",
        "limited":        "limiting_factor",
        "governed":       "governing_relation",
        "controlled":     "control_relation",
        "correlates":     "correlation",
        "dominates":      "dominant_factor",
        "dominant":       "dominant_factor",
        "defined":        "definition",
        "denotes":        "definition",
        "is":             "statement"
    }

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        eq_maps_by_pdf = ctx.get("equation_variable_mapping", {})
        text_knowledge_by_pdf = ctx.get("text_knowledge", {})

        relations_by_pdf: Dict[str, List[Dict[str, Any]]] = {}

        # equations가 없는 pdf라도 text_knowledge만 있을 수 있으니 합집합 사용
        all_pdf_names = set(eq_maps_by_pdf.keys()) | set(text_knowledge_by_pdf.keys())

        for pdf_name in all_pdf_names:
            eq_maps = eq_maps_by_pdf.get(pdf_name, [])
            text_k = text_knowledge_by_pdf.get(pdf_name, [])

            rels: List[Dict[str, Any]] = []

            # ------------------------------------
            # 1) Equation 기반 관계 생성
            # ------------------------------------
            #   - var_defined_by_eq : var → {eq_id, ...}
            #   - var_used_in_eqs  : var → {eq_id, ...}
            var_defined_by_eq: Dict[str, set] = {}
            var_used_in_eqs: Dict[str, set] = {}

            for eq_map in eq_maps:
                eq_id = eq_map.get("eq_id")
                latex = eq_map.get("latex", "")
                defined_var = eq_map.get("defines")  # canonical 로 들어있다고 가정
                vars_list = eq_map.get("variables", [])

                # 사용 변수 canonical 리스트
                used_canonicals: List[str] = []

                for v in vars_list:
                    # vision/텍스트에 따라 key 이름이 다를 수도 있어서 두 개 다 체크
                    can = (
                        v.get("canonical")
                        or v.get("canonical_symbol")
                        or v.get("canonical_name")
                    )
                    if not can:
                        continue

                    used_canonicals.append(can)
                    var_used_in_eqs.setdefault(can, set()).add(eq_id)

                # 정의된 변수 기록
                if defined_var:
                    var_defined_by_eq.setdefault(defined_var, set()).add(eq_id)

                    # "정의된 변수"가 있다면,
                    # 그 변수는 나머지 used_canonicals에 의존하는 것으로 본다.
                    for can in used_canonicals:
                        if can == defined_var:
                            continue
                        rels.append(
                            {
                                "source": can,
                                "target": defined_var,
                                "type": "equation_depends_on",
                                "direction": "unknown",
                                "equation_id": eq_id,
                                "evidence_type": "equation",
                                "evidence": latex,
                            }
                        )

                # 같은 식 안에서 같이 등장하는 변수들 사이의 co-appearance edge
                for i in range(len(used_canonicals)):
                    for j in range(i + 1, len(used_canonicals)):
                        v1 = used_canonicals[i]
                        v2 = used_canonicals[j]
                        if v1 == v2:
                            continue
                        rels.append(
                            {
                                "source": v1,
                                "target": v2,
                                "type": "co_appears_in_equation",
                                "direction": "undirected",
                                "equation_id": eq_id,
                                "evidence_type": "equation",
                                "evidence": latex,
                            }
                        )

            # ------------------------------------
            # 2) Equation ↔ Equation 관계
            #   - 어떤 변수 V를 정의하는 식 eq_def
            #   - 그 변수를 사용하는 식 eq_use
            #   → eq_def → eq_use
            # ------------------------------------
            for var, def_eqs in var_defined_by_eq.items():
                uses = var_used_in_eqs.get(var, set())
                for def_eq in def_eqs:
                    for use_eq in uses:
                        if def_eq == use_eq:
                            continue
                        rels.append(
                            {
                                "source": def_eq,
                                "target": use_eq,
                                "type": "equation_to_equation",
                                "direction": "unknown",
                                "via_variable": var,
                                "evidence_type": "equation_dependency",
                            }
                        )

            # ------------------------------------
            # 3) TextKnowledgeExtractionAgent 결과 병합
            # ------------------------------------
            for sent_record in text_k:
                sentence = sent_record.get("sentence", "")
                result = sent_record.get("result", {})

                # (a) relationships
                for r in result.get("relationships", []):
                    src = r.get("from")
                    tgt = r.get("to")
                    r_type = r.get("type", "text_relation")
                    direction = r.get("direction", "unknown")

                    # --- r_type을 keyword 테이블로 정규화 ---
                    r_type_l = str(r_type).lower()
                    for kw, mapped_type in self.RELATION_KEYWORDS.items():
                        if kw in r_type_l:
                            r_type = mapped_type
                            break

                    # from / to 가 dict 형식일 수도 있고, 문자열일 수도 있음
                    if isinstance(src, dict):
                        src_can = src.get("canonical") or src.get("raw")
                    else:
                        src_can = src
                    if isinstance(tgt, dict):
                        tgt_can = tgt.get("canonical") or tgt.get("raw")
                    else:
                        tgt_can = tgt

                    if not src_can or not tgt_can:
                        continue

                    rels.append(
                        {
                            "source": src_can,
                            "target": tgt_can,
                            "type": f"text_{r_type}",
                            "direction": direction,
                            "equation_id": None,
                            "evidence_type": "text",
                            "evidence": sentence,
                        }
                    )

                # (b) variable_definitions → 자기 자신 정의 관계 추가
                var_defs = result.get("variable_definitions", [])
                for vd in var_defs:
                    if isinstance(vd, dict):
                        v_can = vd.get("canonical") or vd.get("raw")
                    else:
                        v_can = str(vd)

                    if not v_can:
                        continue

                    rels.append(
                        {
                            "source": v_can,
                            "target": v_can,
                            "type": "self_definition",
                            "direction": "none",
                            "equation_id": None,
                            "evidence_type": "text_definition",
                            "evidence": sentence,
                        }
                    )

            # ------------------------------------
            # 4) 중복 제거
            # ------------------------------------
            dedup: List[Dict[str, Any]] = []
            seen = set()
            for r in rels:
                key = json.dumps(r, sort_keys=True, ensure_ascii=False)
                if key in seen:
                    continue
                seen.add(key)
                dedup.append(r)

            relations_by_pdf[pdf_name] = dedup
            self.log("RelationReasoning", pdf_name, dedup)

        ctx["relations"] = relations_by_pdf
        return ctx




# ===========================================================
#  KNOWLEDGE GRAPH BUILDER (final Agent)
# ===========================================================

from dataclasses import dataclass, asdict

@dataclass
class KNode:
    id: str
    type: str           # "variable" | "equation" | ...
    label: str
    metadata: Dict[str, Any]


@dataclass
class KEdge:
    source: str
    target: str
    relation: str       # e.g. "appears_in", "defines", "text_increases_with"
    metadata: Dict[str, Any]


class KnowledgeGraphBuilderAgent(Agent, AgentLoggerMixin):
    """
    Build a unified knowledge graph from:
      - equations
      - equation→variable mapping
      - text knowledge
      - relation reasoning result
    """

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        eqs_by_pdf = ctx.get("equations", {})                     # pdf_name -> [ {id, latex, ...}, ... ]
        eq_var_map_by_pdf = ctx.get("equation_variable_mapping", {})  # pdf_name -> [ {eq_id, variables, defines}, ... ]
        nomenclature_by_pdf = ctx.get("variables_nomenclature", {})   # pdf_name -> { raw_symbol -> canonical }
        relations_by_pdf = ctx.get("relations", {})               # pdf_name -> [ {source, target, type, ...}, ... ]

        knowledge_graphs: Dict[str, Dict[str, Any]] = {}

        for pdf_name, eq_list in eqs_by_pdf.items():

            nodes: List[Dict[str, Any]] = []
            edges: List[Dict[str, Any]] = []
            node_ids = set()

            # -------------- helper: add node --------------
            def add_node(node_id: str, node_type: str, label: str, metadata: Dict[str, Any]):
                if isinstance(node_id, list):
                    node_id = "_".join(str(x) for x in node_id)
                    
                if node_id in node_ids:
                    return
                node_ids.add(node_id)
                nodes.append(
                    asdict(
                        KNode(
                            id=node_id,
                            type=node_type,
                            label=label,
                            metadata=metadata,
                        )
                    )
                )

            # -------------- 1) Variable nodes: nomenclature --------------
            raw2canon = nomenclature_by_pdf.get(pdf_name, {})

            # canonical -> [raw symbols]
            canon2raws: Dict[str, List[str]] = {}
            for raw, canon in raw2canon.items():
                if canon is None:
                    continue
                canon2raws.setdefault(canon, []).append(raw)

            for canon, raw_list in canon2raws.items():
                add_node(
                    node_id=canon,
                    node_type="variable",
                    label=canon,
                    metadata={"raw_symbols": raw_list, "source": "nomenclature"},
                )

            # -------------- 2) Equation nodes --------------
            for eq in eq_list:
                eq_id = eq.get("id")
                if not eq_id:
                    continue
                label = f"Eq {eq.get('number') or eq_id}"
                meta = {
                    "latex": eq.get("latex"),
                    "number": eq.get("number"),
                    "page": eq.get("page"),
                    "image_bbox": eq.get("image_bbox"),
                    "image_path": eq.get("image_path"),
                }
                add_node(eq_id, "equation", label, meta)

            # -------------- 3) Equation-variable edges (appears_in / defines) --------------
            eq_var_maps = eq_var_map_by_pdf.get(pdf_name, [])

            for m in eq_var_maps:
                eq_id = m.get("eq_id")
                if not eq_id:
                    continue

                # appears_in edges
                for v in m.get("variables", []):
                    if not v.get("is_valid", True):
                        continue
                    raw_sym = v.get("symbol_raw")
                    canon = v.get("canonical") or raw2canon.get(raw_sym) or raw_sym
                    # ensure variable node
                    add_node(
                        node_id=canon,
                        node_type="variable",
                        label=canon,
                        metadata={"raw_symbols": [raw_sym], "source": "equation_mapping"},
                    )
                    # edge var -> eq
                    edges.append(
                        asdict(
                            KEdge(
                                source=canon,
                                target=eq_id,
                                relation="appears_in",
                                metadata={"raw_symbol": raw_sym, "equation_id": eq_id},
                            )
                        )
                    )

                # defines edge: eq -> lhs variable
                defines_raw = m.get("defines")
                if defines_raw:
                    defines_canon = raw2canon.get(defines_raw) or defines_raw
                    add_node(
                        node_id=defines_canon,
                        node_type="variable",
                        label=defines_canon,
                        metadata={"raw_symbols": [defines_raw], "source": "equation_mapping_defines"},
                    )
                    edges.append(
                        asdict(
                            KEdge(
                                source=eq_id,
                                target=defines_canon,
                                relation="defines",
                                metadata={"raw_symbol": defines_raw, "equation_id": eq_id},
                            )
                        )
                    )

            # -------------- 4) RelationReasoningAgent edges --------------
            rel_list = relations_by_pdf.get(pdf_name, [])
            for r in rel_list:
                src = r.get("source")
                tgt = r.get("target")
                if not src or not tgt:
                    continue

                # 노드 자동 생성 (없으면)
                add_node(
                    node_id=src,
                    node_type="variable",
                    label=src,
                    metadata={"source": "relation_reasoning"},
                )
                add_node(
                    node_id=tgt,
                    node_type="variable",
                    label=tgt,
                    metadata={"source": "relation_reasoning"},
                )

                edges.append(
                    asdict(
                        KEdge(
                            source=src,
                            target=tgt,
                            relation=r.get("type", "related_to"),
                            metadata={
                                "direction": r.get("direction"),
                                "equation_id": r.get("equation_id"),
                                "evidence_type": r.get("evidence_type"),
                                "evidence": r.get("evidence"),
                            },
                        )
                    )
                )

            # -------------- finalize graph for this pdf --------------
            kg = {"nodes": nodes, "edges": edges}
            knowledge_graphs[pdf_name] = kg
            self.log("KnowledgeGraph", pdf_name, kg)

        ctx["knowledge_graphs"] = knowledge_graphs
        return ctx



# ===========================================================
#  PDF → Text Agent
# ===========================================================

class PDFTextExtractionAgent(Agent, AgentLoggerMixin):
    """
    ./document 폴더에 있는 모든 PDF를 읽어서
    ctx["pdf_texts"][filename] = full_text 형태로 저장
    """

    def __init__(self, pdf_dir: str = "./document"):
        self.pdf_dir = Path(pdf_dir)

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        pdf_texts: Dict[str, str] = {}

        for pdf_path in sorted(self.pdf_dir.glob("*.pdf")):
            try:
                text = _read_pdf(pdf_path)
            except Exception as e:
                self.log("PDFTextExtraction_error", pdf_path.name, {"error": str(e)})
                continue

            pdf_texts[pdf_path.name] = text
            # 앞부분만 로그
            self.log(
                "PDFTextExtraction",
                pdf_path.name,
                {"excerpt": text[:2000]}
            )

        ctx["pdf_texts"] = pdf_texts
        return ctx


# ===========================================================
#  Text Sentence Selection Agent (for TextKnowledgeExtraction)
# ===========================================================

class TextSentenceExtractionAgent(Agent, AgentLoggerMixin):
    """
    PDF 전체 텍스트에서, 변수 이름이 포함된 문장만 뽑아서
    ctx["text_sentences"][filename] = [sentence, ...] 형태로 저장
    """

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        pdf_texts: Dict[str, str] = ctx.get("pdf_texts", {})
        vars_by_pdf: Dict[str, Dict[str, str]] = ctx.get("variables_nomenclature", {})

        text_sentences: Dict[str, List[str]] = {}

        for fn, text in pdf_texts.items():
            if not text:
                continue

            raw2canon = vars_by_pdf.get(fn, {})
            variable_tokens = list(raw2canon.keys()) + [v for v in raw2canon.values() if v]

            # 아주 단순한 문장 split (., ?, ! 기준)
            import re
            rough_sentences = re.split(r'(?<=[\.\?\!])\s+', text)
            filtered: List[str] = []

            if variable_tokens:
                for s in rough_sentences:
                    if any(tok in s for tok in variable_tokens):
                        filtered.append(s.strip())
            else:
                # 변수 정보가 없으면 전체 사용
                filtered = [s.strip() for s in rough_sentences if s.strip()]

            text_sentences[fn] = filtered
            self.log(
                "TextSentenceSelection",
                fn,
                {"count": len(filtered)}
            )

        ctx["text_sentences"] = text_sentences
        return ctx


# ===========================================================
#  Interpretation Agent (최종 설명)
# ===========================================================

class InterpretationAgent(Agent, AgentLoggerMixin):

    SYSTEM_PROMPT = """
You are an expert in ALD transport modeling and thin film growth kinetics.

Using:
- Extracted equations (with LaTeX)
- Variable nomenclature and mappings
- Equation→variable relations
- Text-derived physical relations (e.g., increases_with, inverse_proportional)
- The unified knowledge graph structure (nodes + edges)

Explain the ALD model with focus on:
- Diffusion (gas-phase, Knudsen, effective diffusion)
- Langmuir adsorption / desorption / equilibrium coverage
- Penetration depth and saturation behavior
- Geometry effects (H, W, aspect ratio a, length L)
- Difference between parameters like D, D_A, D_Kn, D_eff, g_pc, K, etc.

Requirements:
- Be technically precise but readable.
- Explain how variables and equations connect (who depends on whom).
- Highlight how changes in p_A, d_A, sticking coefficient, etc. affect growth.
- No JSON, pure explanatory text.
"""

    def __init__(self, model: str = "gpt-5.1", language: str = "en"):
        self.model = model
        self.language = language

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        eqs_by_pdf = ctx.get("equations", {})
        nomenclature_by_pdf = ctx.get("variables_nomenclature", {})
        eq_var_map_by_pdf = ctx.get("equation_variable_mapping", {})
        relations_by_pdf = ctx.get("relations", {})
        kg_by_pdf = ctx.get("knowledge_graphs", {})
        text_knowledge_by_pdf = ctx.get("text_knowledge", {})

        interpretations: Dict[str, str] = {}

        for fn in kg_by_pdf.keys():
            payload = {
                "equations": eqs_by_pdf.get(fn, []),
                "nomenclature": nomenclature_by_pdf.get(fn, {}),
                "equation_variable_mapping": eq_var_map_by_pdf.get(fn, []),
                "relations": relations_by_pdf.get(fn, []),
                "text_knowledge": text_knowledge_by_pdf.get(fn, []),
                "knowledge_graph": kg_by_pdf.get(fn, {}),
            }

            user_prompt = json.dumps(payload, indent=2, ensure_ascii=False)

            explanation = call_text_model(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=self.model,
                json_only=False,
            )

            # 옵션: 한국어로 보고 싶으면 language="ko" 로 설정
            if self.language.lower().startswith("ko"):
                explanation = call_text_model(
                    system_prompt="Translate the following technical ALD modeling explanation into precise Korean.",
                    user_prompt=explanation,
                    model=self.model,
                    json_only=False,
                )

            interpretations[fn] = explanation
            self.log("Interpretation", fn, {"text": explanation})

        ctx["interpretations"] = interpretations
        return ctx



# ===========================================================
#  Orchestrator: 전체 파이프라인 자동 실행
# ===========================================================

class ALDModelingOrchestrator:
    """
    전체 파이프라인:

    1) PDF → Text                         (PDFTextExtractionAgent)
    2) Nomenclature (이미지) → 변수 리스트 (vision_variable_extractor_agent)
    3) PDF → Equations                    (vision_equation_extractor_agent)
    4) Equation → Variable Mapping        (EquationVariableMappingAgent)
    5) Text Sentence Selection            (TextSentenceExtractionAgent)
    6) Text Knowledge Extraction          (TextKnowledgeExtractionAgent)
    7) Relation Reasoning                 (RelationReasoningAgent)
    8) Knowledge Graph Builder            (KnowledgeGraphBuilderAgent)
    9) Interpretation                     (InterpretationAgent)
    """

    def __init__(
        self,
        pdf_dir: str = "./document",
        nomenclature_image_path: str = "./document/nomenclature.png",
        model: str = "gpt-5.1",
        language: str = "en",
    ):
        self.pdf_dir = Path(pdf_dir)
        self.nomenclature_image_path = Path(nomenclature_image_path)
        self.model = model
        self.language = language

        # Vector store (원하면 나중에 text/equation도 넣어서 RAG로 쓸 수 있음)
        self.vector_store = SimpleVectorStore()

        # Agents
        self.pdf_text_agent = PDFTextExtractionAgent(pdf_dir=pdf_dir)
        self.eq_var_mapper = EquationVariableMappingAgent(model=model)
        self.text_sentence_agent = TextSentenceExtractionAgent()
        self.text_knowledge_agent = TextKnowledgeExtractionAgent()
        self.relation_agent = RelationReasoningAgent()
        self.kg_agent = KnowledgeGraphBuilderAgent()
        self.interpreter_agent = InterpretationAgent(model=model, language=language)

    def run(self) -> Dict[str, Any]:
        # 로그 초기화 (원하면)
        reset_communication_log()

        # 0) RAG 폴더 ingest (선택적)
        ensure_rag_dirs()
        base_docs = load_rag_documents()
        if base_docs:
            self.vector_store.add_documents(base_docs)

        ctx: Dict[str, Any] = {}

        # 1) PDF → Text
        ctx = self.pdf_text_agent.run(ctx)
        pdf_texts = ctx.get("pdf_texts", {})
        pdf_names = sorted(pdf_texts.keys())

        if not pdf_names:
            print("[WARNING] No PDFs found in ./document. Nothing to process.")
            return ctx

        # 2) Nomenclature 이미지 → 변수 리스트
        if not self.nomenclature_image_path.exists():
            print(f"[WARNING] Nomenclature image not found at {self.nomenclature_image_path}. Skipping nomenclature.")
            ctx["variables_nomenclature"] = {fn: {} for fn in pdf_names}
        else:
            print(f"Using nomenclature image: {self.nomenclature_image_path}")
            nomenclature_vars = vision_variable_extractor_agent(
                nomenclature_image_path=str(self.nomenclature_image_path),
                vector_store=self.vector_store,
                model=self.model,
            )
            # list → dict (raw → canonical)
            nomenclature_dict = {
                v["symbol_raw"]: v["canonical_symbol"]
                for v in nomenclature_vars
            }
            # 단일 논문 기준: 모든 pdf에 같은 nomenclature를 쓴다고 가정
            ctx["variables_nomenclature"] = {
                fn: dict(nomenclature_dict) for fn in pdf_names
            }

        # 3) PDF → Equations (vision)
        eqs_by_pdf: Dict[str, List[Dict[str, Any]]] = {}
        for fn in pdf_names:
            pdf_path = self.pdf_dir / fn
            if not pdf_path.exists():
                print(f"[WARNING] PDF not found for equation extraction: {pdf_path}")
                eqs_by_pdf[fn] = []
                continue

            print(f"Extracting equations from {pdf_path.name} ...")
            eqs = vision_equation_extractor_agent(
                pdf_path=str(pdf_path),
                vector_store=self.vector_store,
                model=self.model,
                max_equations=None  # None이면 전부, 테스트시 5처럼 줄여도 됨
            )
            eqs_by_pdf[fn] = eqs
            print(f"  -> {len(eqs)} equations extracted.")

        ctx["equations"] = eqs_by_pdf

        # 4) Equation → Variable Mapping
        ctx = self.eq_var_mapper.run(ctx)

        # 5) Text Sentence Selection
        ctx = self.text_sentence_agent.run(ctx)

        # 6) Text Knowledge Extraction
        ctx = self.text_knowledge_agent.run(ctx)

        # 7) Relation Reasoning
        ctx = self.relation_agent.run(ctx)

        # 8) Knowledge Graph Builder
        ctx = self.kg_agent.run(ctx)

        # 9) Interpretation
        ctx = self.interpreter_agent.run(ctx)

        return ctx


# ===========================================================
#  MAIN: 전체 파이프라인 실행 & 결과 저장
# ===========================================================

if __name__ == "__main__":
    print("\n=== ALD Modeling Co-Pilot: FULL PIPELINE RUN ===\n")

    orchestrator = ALDModelingOrchestrator(
        pdf_dir="./document",
        nomenclature_image_path="./document/nomenclature.png",
        model="gpt-5.1",
        language="en",   # "ko" 로 바꾸면 최종 설명을 한국어로 번역함
    )

    ctx = orchestrator.run()

    out_dir = Path("./outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Knowledge graph 저장
    for fn, kg in ctx.get("knowledge_graphs", {}).items():
        with open(out_dir / f"{fn}.knowledge_graph.json", "w", encoding="utf-8") as f:
            json.dump(kg, f, indent=2, ensure_ascii=False)

    # Interpretation 저장
    for fn, expl in ctx.get("interpretations", {}).items():
        with open(out_dir / f"{fn}.interpretation.txt", "w", encoding="utf-8") as f:
            f.write(expl)

    print("\n=== FULL PIPELINE COMPLETED ===")
    print("Knowledge graphs and interpretations are saved under ./outputs\n")
