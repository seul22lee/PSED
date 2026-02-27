import os
import instructor
import hashlib
from groq import Groq
from docling.document_converter import DocumentConverter
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict

# --- 1. 가이드라인에 기반한 데이터 모델 정의 ---

class DataPoint(BaseModel):
    label: str = Field(..., description="데이터 포인트 명칭 (예: Center, Edge)")
    l3_value: Union[float, str] = Field(..., description="L3: 의도적으로 변화시킨 독립 변수의 구체적 수치")
    l4_measurements: Dict[str, Union[float, str]] = Field(..., description="L4: 원시 측정값 (Tc, jsw, Rq, FWHM, RRR 등)")
    l5_derived: Dict[str, Union[float, str]] = Field(default_factory=dict, description="L5: 계산된 값 (Inhomogeneity %, Growth rate, Slope 등)")

class ExperimentBatch(BaseModel):
    batch_id: str
    l2_physical_entity: Dict[str, str] = Field(..., description="L2: 물질(NbN, Al 등), 구조, 기하학적 정의")
    l3_independent_variable_name: str = Field(..., description="L3: 이 실험의 핵심 변수 (Thickness, Wafer position 등)")
    l1_process_context: Dict[str, str] = Field(..., description="L1: 고정된 공정 조건 (Method, Precursor, Temp 등)")
    points: List[DataPoint] = Field(..., description="추출된 개별 데이터 포인트들")
    l6_interpretations: List[str] = Field(default_factory=list, description="L6: Discussion에서 도출된 인과관계 및 메커니즘")
    context_hash: Optional[str] = None

class FinalKB(BaseModel):
    paper_title: str
    batches: List[ExperimentBatch]

# --- 2. 6-Layer 마스터 에이전트 클래스 ---

class KBMasterExtractor:
    def __init__(self, api_key: str):
        self.client = instructor.from_groq(Groq(api_key=api_key))
        self.converter = DocumentConverter()

    def generate_hash(self, l1_dict: Dict) -> str:
        # L1 변수들을 정렬하여 고유한 공정 해시 생성
        sorted_str = str(sorted(l1_dict.items()))
        return hashlib.md5(sorted_str.encode()).hexdigest()

    def process_paper(self, pdf_path: str):
        print(f"[*] 단계 1: Docling 분석 및 상세 표(Table) 추출 중...")
        result = self.converter.convert(pdf_path)
        markdown_text = result.document.export_to_markdown()
        
        tables_md = ""
        for i, table in enumerate(result.document.tables):
            tables_md += f"\n[Table {i+1}]\n{table.export_to_markdown(doc=result.document)}\n"

        # 사용자 제공 6-Layer 가이드라인 주입
        SYSTEM_GUIDELINE = """
        너는 반도체 공정 논문 데이터 추출 전문가야. 아래 6개 레이어 분류 체계를 엄격히 준수해:

        L1 (Process): 항상 고정된 값 (Deposition method, Precursor, Plasma power/pressure, Temp, Cycle time, Substrate type 등)
        L2 (Physical Entity): 실제 객체 정보 (Material, Thickness, Stack, Geometry, Dimensions 등)
        L3 (Independent - 중요): 의도적으로 변화시킨 것 (Thickness variation, Position, Annealing temp 등). 여기서 혼동하면 구조가 무너짐.
        L4 (Measurement): 측정한 물리량 (Tc, jsw, Rq, Grain size, Atomic ratio, FWHM, Lattice parameter, RRR, Q, T1 등)
        L5 (Derived): 계산/해석된 값 (Growth rate, Inhomogeneity %, Relative change, Slope, Fitted parameters 등)
        L6 (Interpretation): Discussion의 가치 있는 정보 (Causal relationship, Mechanism, Substrate effect 등)

        표(Table)의 수치를 최우선 근거로 삼아 데이터를 매핑하라.
        """

        print(f"[*] 단계 2: 6-Layer 가이드라인에 따른 데이터 정밀 매핑 및 자가 수정...")
        kb = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_model=FinalKB,
            messages=[
                {"role": "system", "content": SYSTEM_GUIDELINE},
                {"role": "user", "content": f"본문: {markdown_text[:5000]}\n\n표 데이터:\n{tables_md}"}
            ]
        )

        # 공정 해시 부여
        for batch in kb.batches:
            batch.context_hash = self.generate_hash(batch.l1_process_context)
            
        return kb

# --- 3. 실행 ---
if __name__ == "__main__":
    FREE_KEY = "" # Groq API Key 입력
    extractor = KBMasterExtractor(api_key=FREE_KEY)
    
    pdf_file = "/home/ftk3187/github/PSED/0226_kb/pdf/052401_1_online.pdf"
    if os.path.exists(pdf_file):
        final_kb = extractor.process_paper(pdf_file)
        print("\n[+] 6-Layer Knowledge Base 생성 완료:")
        print(final_kb.model_dump_json(indent=2))
        
        with open("kb_final_output.json", "w", encoding="utf-8") as f:
            f.write(final_kb.model_dump_json(indent=2))