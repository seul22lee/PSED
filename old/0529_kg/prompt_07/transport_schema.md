You are analyzing a scientific paper on **Atomic Layer Deposition (ALD)
conformality modeling**.

Your task is to extract the **Transport Model** from the paper and fill
the provided **JSON schema template**.

The transport model describes the **gas-phase transport of precursor
molecules inside micro/nano-scale features** during ALD.

Examples include:

• diffusion equations
• diffusion-reaction equations
• convection-diffusion equations
• Knudsen diffusion
• Bosanquet diffusion
• effective diffusion coefficients
• transport boundary conditions

------------------------------------------------------------
ALD Conformality Model Structure
------------------------------------------------------------

ALD Conformality Model

    = Transport Model
    + Reaction Model
    + Geometry Model

This task focuses ONLY on the **Transport Model**.

Ignore reaction kinetics unless they appear as **sink terms in the
transport equation**.

Ignore geometry descriptions unless they define **transport length
scales**.

------------------------------------------------------------
Transport Model Definition
------------------------------------------------------------

The transport model describes how precursor molecules move through
high-aspect-ratio structures during ALD.

Typical physics includes:

• molecular diffusion
• Knudsen diffusion
• Bosanquet diffusion
• pressure-driven flow
• diffusion-reaction coupling

Typical governing equation:

∂C/∂t = D_eff ∂²C/∂x² − reaction_sink

------------------------------------------------------------
SCHEMA DOCUMENT
------------------------------------------------------------

The following Markdown document defines the **Transport Model Schema**.

Use this schema to understand:

• the meaning of each field
• how diffusion models are defined
• how canonical variables are normalized
• how transport equations should be interpreted

SCHEMA:

{SCHEMA_MD}

------------------------------------------------------------
JSON TEMPLATE
------------------------------------------------------------

Fill the following JSON template.

Important rules:

• DO NOT modify the JSON structure
• DO NOT remove fields
• ONLY fill values

If the paper does not contain the information,
leave the field empty.

TEMPLATE:

{JSON_TEMPLATE}

------------------------------------------------------------
Evidence Segments
------------------------------------------------------------

The following segments were extracted from the paper and identified as
relevant to the **transport model**.

Each segment contains an ID.

Use the segment ID when filling the annotation.evidence field.

Example:

annotation {
  "evidence": "S032",
  "confidence": "high",
  "uncertainty_note": ""
}

Segments:

{EVIDENCE_SEGMENTS}

------------------------------------------------------------
Extraction Guidelines
------------------------------------------------------------

Fill the JSON template using only the provided evidence segments.

Do NOT hallucinate information.

When extracting variables, identify:

• canonical_name
• paper_symbol
• physical_meaning
• units
• definition
• equation_context

Always map the **paper symbol used in the paper** to the **canonical
name defined in the schema**.

Examples:

D, D_eff → effective_diffusion_coefficient

D_K → knudsen_diffusion_coefficient

p_A → gas_phase_pressure

C_A → gas_phase_concentration

F → gas_phase_flux

Kn → knudsen_number

------------------------------------------------------------
Equation Extraction
------------------------------------------------------------

If a segment contains a transport equation, record it under:

diffusion_model.equation

Examples:

D_eff = (1/D_A + 1/D_K)^(-1)

D_K = (2/3) r sqrt(8RT / πM)

If multiple equations appear, record the one used for the **transport
model definition**.

------------------------------------------------------------
Transport Equation Structure
------------------------------------------------------------

Identify the structure of the governing equation.

Possible forms:

diffusion

diffusion_reaction

convection_diffusion

convection_diffusion_reaction

Example:

∂p/∂t = D_eff ∂²p/∂x² − reaction_term

→ form: diffusion_reaction

------------------------------------------------------------
Diffusion Model Identification
------------------------------------------------------------

Identify which diffusion model is used.

Possible types:

molecular_diffusion

knudsen_diffusion

bosanquet_diffusion

effective_pore_diffusion

pressure_dependent_diffusion

Example:

D_eff = (1/D_A + 1/D_K)^(-1)

→ bosanquet_diffusion

------------------------------------------------------------
Evidence Annotation
------------------------------------------------------------

Every canonical variable must include annotation metadata.

Example:

annotation {
  "evidence": "S045",
  "confidence": "high",
  "uncertainty_note": ""
}

Confidence levels:

high
    explicitly defined in equation or text

medium
    strongly implied

low
    uncertain interpretation

If multiple segments support the same variable:

"evidence": "S021, S028"

------------------------------------------------------------
Important Fields
------------------------------------------------------------

The most important fields in the transport model are:

• equation_structure
• diffusion_model
• transport_variable
• assumptions

These fields capture most transport-model differences across ALD
conformality literature.

------------------------------------------------------------
Output Format
------------------------------------------------------------

Return **valid JSON only**.

The output must follow the provided JSON template exactly.

Do NOT include explanations.

Return JSON only.