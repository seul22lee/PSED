# 09_normalize_causal_relations.py

import os,json,re,time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import OUTPUT_DIR

MODEL="gemini-2.5-flash"

load_dotenv()
client=genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

PROMPT="""
You are a scientific ontology normalization system.

Task:
Map ONLY cause and effect terms to canonical concepts from the dictionary.

Rules:
- Preserve all original fields.
- Add:
  - cause_raw
  - cause_canonical
  - effect_raw
  - effect_canonical
- cause_canonical and effect_canonical must be arrays.
- One term may map to multiple canonical concepts.
- Use ONLY concepts present in the dictionary.
- If no good match exists return [].
- Do not invent concepts.
- Return JSON only.

Output schema:

{
  "causal_relations":[
    {
      "cause_raw":"",
      "cause_canonical":[],
      "effect_raw":"",
      "effect_canonical":[],

      "cause":"",
      "effect":"",
      "direction":"",
      "condition":"",
      "evidence_text":"",
      "evidence_source":"",
      "figure_id":"",
      "confidence":""
    }
  ]
}
"""

CONFIG=types.GenerateContentConfig(
    temperature=0,
    response_mime_type="application/json"
)

def load_json(path):
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def save_json(obj,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)

def clean_json(txt):
    return txt.replace("```json","").replace("```","").strip()

def run_llm(prompt,max_retry=5):
    for _ in range(max_retry):
        try:
            r=client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=CONFIG
            )
            return json.loads(clean_json(r.text))
        except Exception as e:
            msg=str(e)
            if "RESOURCE_EXHAUSTED" in msg:
                m=re.search(r"retry in (\d+)",msg,re.I)
                wait=int(m.group(1))+5 if m else 60
                print(f"[RATE LIMIT] sleep {wait}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("max retry exceeded")

def build_dictionary_text(dictionary):
    rows=[]
    for item in dictionary:
        rows.append({
            "canonical_name":item["canonical_name"],
            "aliases":item.get("aliases",[])
        })
    return json.dumps(rows,ensure_ascii=False,indent=2)

def process_paper(paper_dir):
    causal_path=paper_dir/"08_causal_relations"/"causal_relations.json"
    dict_path=Path("/home/ftk3187/github/PSED/0604_kg/dictionary/dictionary.json")

    if not causal_path.exists():
        return

    if not dict_path.exists():
        print(f"[SKIP] no dictionary: {paper_dir.name}")
        return

    causal=load_json(causal_path)
    dictionary=load_json(dict_path)

    prompt=f"""
{PROMPT}

DICTIONARY
----------
{build_dictionary_text(dictionary)}

CAUSAL_RELATIONS
----------------
{json.dumps(causal,ensure_ascii=False,indent=2)}
"""

    result=run_llm(prompt)

    out_dir=paper_dir/"09_normalized_causal_relations"
    out_dir.mkdir(parents=True,exist_ok=True)

    save_json(
        result,
        out_dir/"normalized_causal_relations.json"
    )

    print("[OK]",paper_dir.name)

def main():
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():
            process_paper(paper_dir)

if __name__=="__main__":
    main()