You are analyzing a scientific paper on **Atomic Layer Deposition (ALD)
conformality modeling**.

Your task is to determine whether each segment contains information
relevant to the **Reaction Model** of the ALD conformality model.

Segments may be sentences or equations.

Return JSON only in the following format:

{
  "results": [
    {
      "segment_id": "S00010",
      "reaction_relevant": true
    }
  ]
}

------------------------------------------------------------
ALD Conformality Model Structure
------------------------------------------------------------

ALD Conformality Model

    = Transport Model
    + Reaction Model
    + Geometry Model

This task focuses ONLY on the **Reaction Model**.

------------------------------------------------------------
Reaction Model Definition
------------------------------------------------------------

The reaction model describes the **surface-reaction physics controlling
adsorption, desorption, and film growth during ALD**.

It includes surface coverage dynamics, sticking probability, reaction
rate equations, and adsorption/desorption kinetics.

------------------------------------------------------------
Relevant Reaction Concepts
------------------------------------------------------------

A segment is relevant to the **reaction_model** if it contains information
related to any of the following topics.

------------------------------------------------------------
1. Reaction Equations
------------------------------------------------------------

Equations describing surface kinetics.

Examples

• adsorption rate equations  
• surface coverage evolution equations  
• Langmuir kinetics  
• adsorption–desorption balance  

Example equations

dθ/dt = k_ads C (1 − θ)

r = s F (1 − θ)

These must be classified as reaction_model.

------------------------------------------------------------
2. Surface Species
------------------------------------------------------------

Statements describing surface-state variables.

Examples

• surface coverage θ  
• adsorbed species density  
• occupied surface sites  

Example sentences

"The surface coverage θ represents the fraction of occupied sites."

------------------------------------------------------------
3. Adsorption Models
------------------------------------------------------------

Statements describing adsorption mechanisms.

Examples

• Langmuir adsorption  
• sticking probability models  
• probabilistic adsorption  

Example sentences

"Adsorption follows Langmuir kinetics."

"The sticking probability c describes adsorption upon collision."

------------------------------------------------------------
4. Desorption Models
------------------------------------------------------------

Statements describing desorption processes.

Examples

• desorption rate constants  
• reversible adsorption  
• desorption rate expressions  

Example sentence

"The desorption rate is expressed as k_des θ."

------------------------------------------------------------
5. Reaction Coefficients
------------------------------------------------------------

Statements defining reaction parameters.

Examples

• sticking probability (s, β, c)  
• adsorption rate constant k_ads  
• desorption rate constant k_des  
• reaction probability  

Example sentence

"The sticking probability c is used in the adsorption rate."

------------------------------------------------------------
6. Site Balance
------------------------------------------------------------

Statements describing conservation of adsorption sites.

Examples

• site density  
• maximum coverage  
• site balance equations  

Example equation

θ + θ_vacant = 1

------------------------------------------------------------
7. Growth Relation
------------------------------------------------------------

Statements connecting surface reactions to film growth.

Examples

• growth per cycle (GPC)  
• growth rate expressions  
• surface coverage determining growth  

Example

"GPC = q θ"

------------------------------------------------------------
8. Reaction Dependencies
------------------------------------------------------------

Statements describing variables affecting reaction rate.

Examples

• dependence on precursor pressure  
• dependence on surface coverage  
• temperature-dependent reaction constants  

------------------------------------------------------------
9. Reaction Regime
------------------------------------------------------------

Statements describing the kinetic regime.

Examples

• adsorption-limited regime  
• reaction-limited growth  
• coverage-dependent sticking  

------------------------------------------------------------
10. Boundary Coupling
------------------------------------------------------------

Statements linking reaction to transport through surface flux.

Examples

• surface adsorption flux  
• reaction rate used as transport boundary condition  

Example sentence

"The adsorption rate is used as the wall boundary flux."

------------------------------------------------------------
Equation Segments
------------------------------------------------------------

If the segment is an equation, classify it as reaction_model if it
describes **surface kinetics or surface coverage dynamics**.

Examples

dθ/dt = k_ads C (1 − θ)

r = s F (1 − θ)

These equations represent reaction_model information.

------------------------------------------------------------
Classification Rule
------------------------------------------------------------

Return TRUE if the segment contains **any surface-reaction physics**.

Return FALSE if the segment only discusses:

• diffusion equations  
• transport PDEs  
• precursor pressure evolution  
• geometric feature dimensions  

These belong to transport_model or geometry_model.

------------------------------------------------------------
Output Format

Return JSON only in the following format:

{
  "results": [
    {
      "segment_id": "S00015",
      "reaction_relevant": true
    },
    {
      "segment_id": "S00016",
      "reaction_relevant": false
    }
  ]
}