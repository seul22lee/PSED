You are analyzing a scientific paper on **Atomic Layer Deposition (ALD) conformality modeling**.

Your task is to extract the **Geometry Model** from the paper and fill the provided **JSON schema template**.

The geometry model describes the **physical structure and dimensions of the feature where ALD deposition occurs**.

Examples of structures include:

• trenches  
• holes  
• LHAR channels  
• porous particles  
• planar surfaces

The extracted information will be used to construct a **knowledge graph of ALD conformality models**.

------------------------------------------------------------
ALD Conformality Model Structure
------------------------------------------------------------

ALD Conformality Model

    = Transport Model
    + Reaction Model
    + Geometry Model

This task focuses ONLY on the **Geometry Model**.

Ignore reaction kinetics and diffusion physics unless they explicitly define geometric quantities.

------------------------------------------------------------
Schema Description
------------------------------------------------------------

The following Markdown document defines the **Geometry Model Schema**.

Use it to understand the meaning of each field and how variables should be normalized.

Important concepts include:

• feature definitions  
• geometric dimensions  
• derived geometry quantities  
• coordinate systems  
• geometry assumptions  
• interfaces with transport and reaction models

Use the schema description to correctly interpret canonical variable names.

------------------------------------------------------------
SCHEMA DOCUMENT
------------------------------------------------------------

{SCHEMA_MD}

------------------------------------------------------------
JSON TEMPLATE
------------------------------------------------------------

You must fill the following JSON template.

Important rules:

• DO NOT change the JSON structure  
• DO NOT remove fields  
• ONLY fill values  

If the paper does not contain the information, leave the field empty.

------------------------------------------------------------

{JSON_TEMPLATE}

------------------------------------------------------------
Evidence Segments
------------------------------------------------------------

The following segments were extracted from the paper and identified as relevant to the geometry model.

Each segment has an ID.

Use the segment ID when filling the **annotation.evidence** field.

Example:

annotation {
  "evidence": "S015",
  "confidence": "high",
  "uncertainty_note": ""
}

Segments:

{EVIDENCE_SEGMENTS}

------------------------------------------------------------
Extraction Guidelines
------------------------------------------------------------

1. Fill the JSON template using information from the evidence segments.

2. When a geometric variable appears:

Extract

• canonical_name  
• paper_symbol  
• physical_meaning  
• units  
• definition  
• equation_context  

3. Map the **paper symbol** used in the paper to the correct **canonical_name** defined in the schema.

Example:

paper symbol → canonical concept

H → feature_height  
W → feature_width  
AR → aspect_ratio  
r → pore_radius  

4. Every canonical variable must include annotation metadata:

annotation {
  evidence
  confidence
  uncertainty_note
}

5. Confidence levels:

high
    explicitly stated in evidence

medium
    strongly implied but not explicit

low
    uncertain interpretation

6. If multiple segments support a value, include multiple IDs.

Example:

"evidence": "S021, S034"

7. If a field is not mentioned in the evidence, leave it empty.

Do not guess.

------------------------------------------------------------
Handling Equations
------------------------------------------------------------

Equations may define geometric relationships.

Examples:

AR = H / W  
A = 2πrL  

If an equation defines a geometric quantity:

• extract the variable  
• record the equation_context  
• include the segment ID as evidence

------------------------------------------------------------
Important Fields
------------------------------------------------------------

The most important fields for geometry extraction are:

• feature_definition  
• geometry_parameters  
• derived_parameters  
• geometry_assumptions  

These capture most geometry-model differences across ALD conformality literature.

------------------------------------------------------------
Output Format
------------------------------------------------------------

Return **valid JSON only**.

The output must follow the provided JSON template exactly.

Do NOT include explanations.

Return JSON only.