import os,json,time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import OUTPUT_DIR,STEP,PAPER_SCHEMA_PROMPT

MODEL="gemini-2.5-flash"

load_dotenv()
api_key=os.getenv("GOOGLE_API_KEY")
if not api_key:raise ValueError("GOOGLE_API_KEY not found")
client=genai.Client(api_key=api_key)

def load_json(path):
    with open(path,"r",encoding="utf-8") as f:return json.load(f)

def save_json(data,path):
    with open(path,"w",encoding="utf-8") as f:json.dump(data,f,indent=2,ensure_ascii=False)

def load_text(path):
    with open(path,"r",encoding="utf-8") as f:return f.read()

def clean_json(text):
    return text.replace("```json","").replace("```","").strip()

def build_prompt(prompt_text,sections):
    abstract=sections.get("abstract","")
    conclusion=sections.get("conclusion","")
    return f"""{prompt_text}

ABSTRACT
---------
{abstract}

CONCLUSION
---------
{conclusion}
"""

def run_llm(prompt):
    response=client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json"
        )
    )
    return response.text

def process_paper(paper_stem):
    step01=OUTPUT_DIR/paper_stem/STEP["01"]
    step05=OUTPUT_DIR/paper_stem/STEP["05"]

    sections_path=step01/"sections.json"

    if not sections_path.exists():
        print(f"[SKIP] {paper_stem} sections.json missing")
        return

    step05.mkdir(parents=True,exist_ok=True)

    sections=load_json(sections_path)
    prompt_text=load_text(PAPER_SCHEMA_PROMPT)

    prompt=build_prompt(prompt_text,sections)

    try:
        result=run_llm(prompt)
        result_json=json.loads(clean_json(result))
        save_json(result_json,step05/"paper_schema.json")
        print(f"[OK] {paper_stem}")
    except Exception as e:
        print(f"[FAIL] {paper_stem}: {e}")

    time.sleep(1)

def main():
    papers=sorted([p.name for p in OUTPUT_DIR.iterdir() if p.is_dir()])
    for paper_stem in papers:
        process_paper(paper_stem)

if __name__=="__main__":
    main()