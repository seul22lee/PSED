You are analyzing a scientific paper on **Atomic Layer Deposition (ALD) conformality modeling**.

Your task is to extract the **Reaction Model** from the paper and fill the provided **JSON schema template**.

The reaction model describes the **surface reaction kinetics governing adsorption and growth during ALD**.

Examples include:

• Langmuir adsorption kinetics  
• sticking probability models  
• adsorption/desorption rate equations  
• surface site balance  
• growth-per-cycle relations  

The extracted information will be used to construct a **knowledge graph of ALD conformality models**.

------------------------------------------------------------
ALD Conformality Model Structure
------------------------------------------------------------

ALD Conformality Model

    = Transport Model
    + Reaction Model
    + Geometry Model

This task focuses ONLY on the **Reaction Model**.

Ignore geometry descriptions and transport diffusion equations unless they directly appear inside reaction expressions.

------------------------------------------------------------
Schema Description
------------------------------------------------------------

The following Markdown document defines the **Reaction Model Schema**.

Use it to understand:

• the meaning of each field  
• how reaction variables are normalized  
• the structure of adsorption and desorption models  
• how reaction coefficients should be stored  

Important reaction concepts include:

• adsorption rate expressions  
• surface coverage variables  
• sticking coefficients  
• reaction rate constants  
• site balance relations  
• growth-per-cycle relations  

------------------------------------------------------------
SCHEMA DOCUMENT
------------------------------------------------------------

{SCHEMA_MD}

------------------------------------------------------------
JSON TEMPLATE
------------------------------------------------------------

Fill the following JSON template.

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

The following segments were extracted from the paper and identified as relevant to the reaction model.

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

2. When extracting a reaction variable, record:

• canonical_name  
• paper_symbol  
• physical_meaning  
• units  
• definition  
• equation_context  

3. Always map the **paper symbol** used in the paper to the correct **canonical_name** defined in the schema.

Example mappings:

θ → surface_coverage  
s, β, c → sticking_probability  
k_ads → adsorption_rate_constant  
k_des → desorption_rate_constant  

4. Every canonical variable must include annotation metadata:

annotation {
  evidence
  confidence
  uncertainty_note
}

5. Confidence levels:

high  
    explicitly defined in text or equation

medium  
    strongly implied but not explicitly defined

low  
    uncertain interpretation

6. If multiple segments support the same variable, include multiple IDs.

Example:

"evidence": "S021, S034"

7. If a field is not mentioned in the evidence, leave it empty.

Do not guess.

------------------------------------------------------------
Handling Reaction Equations
------------------------------------------------------------

Reaction equations often define adsorption or surface reaction rates.

Examples:

dθ/dt = k_ads p_A (1 − θ)

r = s F (1 − θ)

When an equation appears:

• record the equation in reaction_equation.equation  
• identify adsorption and desorption terms  
• extract coefficients used in the equation  

------------------------------------------------------------
Important Fields
------------------------------------------------------------

The most important reaction-model fields are:

• kinetics_type  
• adsorption_rate_expression  
• coverage_variable  
• sticking_coefficient  
• assumptions  

These capture most of the scientifically meaningful variation across ALD reaction models.

------------------------------------------------------------
Output Format
------------------------------------------------------------

Return **valid JSON only**.

The output must follow the provided JSON template exactly.

Do NOT include explanations.

Return JSON only.