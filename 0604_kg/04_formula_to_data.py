import os,json,time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key=os.getenv("GOOGLE_API_KEY")
if not api_key:raise ValueError("GOOGLE_API_KEY not found")
client=genai.Client(api_key=api_key)

MODEL_ID="gemini-2.5-flash"

PROMPT="""
You are a scientific equation analysis system.

Analyze the equation image and extract variable dependency information.

Rules:

- Extract variables exactly as written.
- Preserve subscripts and superscripts when visible.
- Ignore numbers, constants, and operators when listing variables.
- lhs contains variables being defined.
- rhs_symbols contains variables appearing on the right side.
- dependency_edges are [source,target].
- dependency_relations describe how a source variable affects a target variable based ONLY on the mathematical structure of the equation.
- Do NOT use scientific background knowledge.
- Do NOT guess.
- If the relationship cannot be determined confidently, use "unknown".

Allowed dependency relation types:

- proportional
    target is directly proportional to source
    examples:
    y = kx
    y = AxB

- inverse
    target is inversely proportional to source
    examples:
    y = k/x
    y = A/B

- positive
    source has a positive influence on target but exact proportionality is unclear
    examples:
    y = exp(x)
    y = x²

- negative
    source has a negative influence on target but exact inverse proportionality is unclear
    examples:
    y = exp(-x)
    y = 1/x²

- unknown
    relationship cannot be determined confidently

equation_role examples:

- definition
- diffusion
- transport
- adsorption
- reaction_rate
- conservation
- geometry
- probability
- empirical
- unknown

Return JSON only.

{
  "lhs":[
    {
      "symbol":"",
      "original":""
    }
  ],

  "rhs_symbols":[
    {
      "symbol":"",
      "original":""
    }
  ],

  "dependency_edges":[
    ["source","target"]
  ],

  "dependency_relations":[
    {
      "source":"",
      "target":"",
      "effect":"proportional|inverse|positive|negative|unknown",
      "reason":""
    }
  ],

  "equation_type":"",
  "equation_role":""
}
"""

CONFIG=types.GenerateContentConfig(temperature=0,response_mime_type="application/json")

def process_equations(paper_stem,output_dir):
    image_dir=Path(output_dir)/paper_stem/"01_docling"/"formulas"
    out_dir=Path(output_dir)/paper_stem/"04_formula_to_data"
    out_dir.mkdir(parents=True,exist_ok=True)
    image_files=sorted(image_dir.glob("equation-*.png")) ##################
    if not image_files:return
    results=[]
    for img_path in image_files:
        try:
            with open(img_path,"rb") as f:image_bytes=f.read()
            response=client.models.generate_content(model=MODEL_ID,contents=[PROMPT,types.Part.from_bytes(data=image_bytes,mime_type="image/png")],config=CONFIG)
            try:eq_json=json.loads(response.text)
            except:eq_json={"raw_response":response.text}
            eq_json["equation_image"]=img_path.name
            results.append(eq_json)
            time.sleep(2)
        except Exception as e:
            print(f"Failed {img_path.name}: {e}")
    with open(out_dir/"equations.json","w",encoding="utf-8") as f:json.dump(results,f,indent=2,ensure_ascii=False)

def main():
    from config import OUTPUT_DIR
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():process_equations(paper_dir.name,OUTPUT_DIR)

if __name__=="__main__":
    main()