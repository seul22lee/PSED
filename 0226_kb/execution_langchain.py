import os
import json
from typing import List, Optional, Union, Dict
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from docling.document_converter import DocumentConverter

load_dotenv()

# --- 1. 정밀 스키마 (전문가용 6-Layer) ---
class DataPoint(BaseModel):
    label: str = Field(..., description="데이터 포인트 (예: Center, 2-in edge, 4-in edge)")
    l3_value: str = Field(..., description="L3: 독립 변수의 구체적 수치 (예: 0mm, 25mm, 50mm)")
    l4_measurements: Dict[str, Union[float, str]] = Field(..., description="L4: 모든 측정값 (Tc, rho0, jsw, delta-T, RRR, Grain size, FWHM, Lattice constant 등)")
    l5_derived: Dict[str, Union[float, str]] = Field(default_factory=dict, description="L5: 계산된 값 (Inhomogeneity %, Change % 등)")

class ExperimentBlock(BaseModel):
    experiment_id: str
    objective: str = Field(..., description="해당 섹션/실험의 구체적 목표")
    l1_process_context: Dict[str, Union[float, str]] = Field(..., description="L1: 공정 조건 (Temp, Power, Precursor, Pressure 등)")
    l2_physical_entity: Dict[str, Union[float, str]] = Field(..., description="L2: 물리 객체 (Material, Nominal Thickness, Geometry 등)")
    l3_independent_variable_name: str = Field(..., description="L3: 조절 변수명 (wafer_position, thickness_variation 등)")
    points: List[DataPoint] = Field(..., description="Table 및 본문에서 발견된 모든 데이터 포인트 (전수 추출)")
    l6_interpretations: List[str] = Field(default_factory=list, description="L6: 물리적 해석 및 인과관계")
    source_anchors: List[str] = Field(..., description="근거 Figure/Table/Section 번호")

class ComparisonBlock(BaseModel):
    comparison_id: str
    source_experiments: List[str]
    logic: str = Field(..., description="실험 간 대조 논리 (예: 두께는 고정되었으나 조성 변화로 특성 저하)")

class FinalKB(BaseModel):
    paper_title: str
    experiment_blocks: List[ExperimentBlock]
    comparison_blocks: List[ComparisonBlock]

# --- 2. Line-by-Line 해부 에이전트 ---
class LineByLineDissector:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=8000 
        ).with_structured_output(FinalKB)
        self.converter = DocumentConverter()
        
        self.system_guideline = """
        너는 반도체 공정 데이터를 한 줄도 놓치지 않고 분석하는 수석 감사 연구원이야. 
        부분적인 요약은 절대 금지하며, 다음 지침에 따라 논문을 '전수 해부'하라.

        [해부 프로토콜: Line-by-Line Analysis]
        1. 문장 단위 스캔: Introduction 이후 모든 문장을 순차적으로 읽으며, 새로운 공정 수치(L1), 샘플 조건(L2), 독립 변수(L3)가 등장할 때마다 이를 기록하라.
        2. 표(Table) 전수 조사: 모든 표의 행(Row)과 열(Column)을 교차 분석하여 단 하나의 수치 데이터 포인트도 누락하지 마라. (특히 Table II의 위치별 모든 물성값 필수 추출)
        3. 변수 상태 추적: 실험의 흐름을 따라가며 '무엇이 변했고(L3) 무엇이 고정되었는지(L1/L2)'를 매 순간 파악하여 ExperimentBlock을 생성하라.
        4. 논리 복원: 저자가 각 실험 결과를 비교하며 도출하는 인과관계(L6)와 비교 논리(ComparisonBlock)를 문장에서 찾아 그대로 보존하라.
        5. 데이터 무결성: 모든 수치는 단위를 포함하고, 텍스트와 표의 정보가 충돌할 경우 표의 수치를 우선하라.

        정보를 생략하거나 압축하지 말고, 전문가가 논문을 읽고 머릿속에 그리는 지식의 지도를 그대로 JSON으로 옮겨라.
        """

    def dissect(self, file_path: str):
        print(f"[*] {os.path.basename(file_path)} 전수 해부 시작...")
        result = self.converter.convert(file_path)
        markdown_text = result.document.export_to_markdown()
        tables_md = "\n".join([t.export_to_markdown(doc=result.document) for t in result.document.tables])

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_guideline),
            ("user", "Introduction 이후부터 결론까지 모든 내용을 6-Layer 구조에 맞춰 빈틈없이 분석하라. 특히 표 데이터와 본문의 모든 수치적 변화를 찾아라. \n\n[Full Text]\n{context}\n\n[All Tables]\n{tables}")
        ])
        
        # Groq 모델에 넉넉한 컨텍스트 전달 (약 12,000자)
        return (prompt | self.llm).invoke({"context": markdown_text[:12000], "tables": tables_md})

if __name__ == "__main__":
    dissector = LineByLineDissector()
    pdf_path = "pdf/052401_1_online.pdf" 
    
    if os.path.exists(pdf_path):
        kb_output = dissector.dissect(pdf_path)
        with open(f"kb_full_dissection.json", "w", encoding="utf-8") as f:
            f.write(kb_output.model_dump_json(indent=2))
        print(f"[+] 해부 완료: kb_full_dissection.json")