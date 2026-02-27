import os
import instructor
import json
import hashlib
from openai import OpenAI
from docling.document_converter import DocumentConverter
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- 1. 데이터 모델 정의 (Meta-Inference용 고도화) ---
# L3 변수들을 표준화하기 위한 Enum
L3_TYPE = Literal[
    "wafer_position", "thickness", "substrate_temp", 
    "plasma_power", "gas_flow_rate", "cycle_time", "unknown"
]

class ExperimentBatch(BaseModel):
    batch_id: str
    target_entity: str = Field(..., description="L2: 물질명 및 기본 상태 (예: NbN 6.1nm film)")
    independent_variable: L3_TYPE = Field(..., description="L3: 의도적으로 변화시킨 핵심 변수")
    measurements: List[str] = Field(..., description="L4: 측정 항목 리스트 (Tc, jsw, Rq 등)")
    fixed_conditions_hash: Optional[str] = Field(None, description="L1 조건들의 해시값")

class FinalKB(BaseModel):
    paper_title: str
    batches: List[ExperimentBatch]

# --- 2. 자가 수정 에이전트 클래스 ---
class KBSelfCorrector:
    def __init__(self, api_key: str):
        self.client = instructor.from_openai(OpenAI(api_key=api_key))
        self.converter = DocumentConverter()

    def _generate_context_hash(self, text: str) -> str:
        """L1 공정 조건(온도, 전구체 등)을 찾아 해싱합니다."""
        # 실제 구현시에는 LLM으로 L1만 따로 뽑아 정렬 후 해싱하는 것이 정확합니다.
        return hashlib.md5(text[:500].encode()).hexdigest()

    def process_paper(self, pdf_path: str):
        print(f"[*] 단계 1: Docling을 이용한 PDF 구조 분석 시작...")
        result = self.converter.convert(pdf_path)
        markdown_text = result.document.export_to_markdown()
        
        # 표 데이터를 마크다운 문자열로 변환하여 LLM 전달용으로 준비
        tables_md = ""
        for i, table in enumerate(result.document.tables):
            tables_md += f"\n[Table {i+1}]\n{table.export_to_markdown()}\n"

        print(f"[*] 단계 2: 텍스트 기반 초기 실험 구조 파악 중...")
        initial_kb = self.get_initial_structure(markdown_text)

        print(f"[*] 단계 3: 표 데이터를 바탕으로 구조 자가 수정 및 확정...")
        final_kb = self.verify_and_refine(initial_kb, tables_md, markdown_text)
        
        # 공정 해시 추가 (간이 구현)
        for batch in final_kb.batches:
            batch.fixed_conditions_hash = self._generate_context_hash(markdown_text)
            
        return final_kb

    def get_initial_structure(self, text: str):
        return self.client.chat.completions.create(
            model="gpt-4o",
            response_model=FinalKB,
            messages=[{
                "role": "user", 
                "content": f"논문의 제목과 초록/실험 섹션을 보고 실험군(Batch) 구조 초안을 잡아줘. L3 변수를 주의 깊게 봐:\n\n{text[:5000]}"
            }]
        )

    def verify_and_refine(self, draft_kb: FinalKB, tables_md: str, text: str):
        return self.client.chat.completions.create(
            model="gpt-4o",
            response_model=FinalKB,
            messages=[
                {"role": "system", "content": "너는 반도체 공정 데이터 검증 전문가야. 초안과 실제 표(Table)를 비교해. 만약 표의 열(Column) 헤더가 초안의 독립변수(L3)와 다르면, 표를 '진실의 근거'로 삼아 구조를 완전히 재수정해."},
                {"role": "user", "content": f"초안 구조: {draft_kb.json()}\n\n추출된 표 데이터:\n{tables_md}\n\n결론부 맥락:\n{text[-2000:]}"}
            ]
        )

# --- 3. 실행 및 결과 확인 ---
if __name__ == "__main__":
    # 환경 변수나 직접 입력으로 API KEY 설정
    MY_API_KEY = "your-api-key-here"
    
    corrector = KBSelfCorrector(api_key=MY_API_KEY)
    
    # 실제 파일 경로 확인
    pdf_file = "/home/ftk3187/github/PSED/0226_kb/pdf/052401_1_online.pdf"
    
    if os.path.exists(pdf_file):
        kb_result = corrector.process_paper(pdf_file)
        print("\n" + "="*50)
        print("최종 도출된 Knowledge Base 구조:")
        print(kb_result.json(indent=2, ensure_ascii=False))
        print("="*50)
        
        # 결과 저장
        with open("kb_result.json", "w", encoding="utf-8") as f:
            f.write(kb_result.json(indent=2, ensure_ascii=False))
    else:
        print(f"에러: {pdf_file} 파일이 없습니다.")