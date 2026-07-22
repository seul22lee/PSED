import os,json,time
from pathlib import Path
from dotenv import load_dotenv
from config import OUTPUT_DIR,STEP

from google import genai
from google.genai import types
MODEL="gemini-2.5-flash"

load_dotenv()
client=genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def load_json(p):
    with open(p,"r",encoding="utf-8") as f:return json.load(f)

def save_json(obj,p):
    p.parent.mkdir(parents=True,exist_ok=True)
    with open(p,"w",encoding="utf-8") as f:json.dump(obj,f,indent=2,ensure_ascii=False)

def clean_json(t):
    return t.replace("```json","").replace("```","").strip()

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

def build_prompt(sections,figures):

    payload={
        "abstract":sections.get("abstract",""),
        "conclusion":sections.get("conclusion",""),
        "figures":[
            {
                "figure_id":f.get("figure_id"),
                "caption":f.get("caption"),
                "contexts":f.get("figure_contexts",[])
            }
            for f in figures
        ]
    }

    return f"""{PROMPT}

INPUT
-----
{json.dumps(payload,ensure_ascii=False,indent=2)}
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
    return json.loads(clean_json(response.text))

def process_paper(paper_dir):

    sections_path=paper_dir/STEP["01"]/"sections.json"
    fig_dir=paper_dir/STEP["06"]
    out_dir=paper_dir/"08_causal_relations"

    if not sections_path.exists():
        return

    sections=load_json(sections_path)

    figures=[]
    if fig_dir.exists():
        for p in sorted(fig_dir.glob("figure-*.json")):
            figures.append(load_json(p))

    prompt=build_prompt(sections,figures)

    result=run_llm(prompt)

    save_json(
        result,
        out_dir/"causal_relations.json"
    )

    print("[OK]",paper_dir.name)

    time.sleep(1)

def main():
    for paper_dir in sorted(OUTPUT_DIR.iterdir()):
        if paper_dir.is_dir():
            process_paper(paper_dir)

if __name__=="__main__":
    main()