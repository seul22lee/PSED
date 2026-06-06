You are analyzing a scientific paper on **Atomic Layer Deposition (ALD)
conformality modeling**.

Your task is to determine whether each segment contains information
relevant to the **Transport Model** of the ALD conformality model.

Segments may be sentences or equations.

Return JSON only in the following format:

{
  "results": [
    {
      "segment_id": "S00010",
      "transport_relevant": true
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

This task focuses ONLY on the **Transport Model**.

------------------------------------------------------------
Transport Model Definition
------------------------------------------------------------

The transport model describes **gas-phase transport of precursor
molecules inside high-aspect-ratio (HAR) structures**.

This typically includes diffusion, convection, pressure evolution,
transport PDEs, and transport boundary conditions.

Transport determines how precursor molecules move from the entrance of
a feature to deeper regions.

------------------------------------------------------------
Relevant Transport Concepts
------------------------------------------------------------

A segment is relevant to the **transport_model** if it contains
information related to any of the following topics.

------------------------------------------------------------
1. Transport Governing Equations
------------------------------------------------------------

Equations describing precursor transport in the feature.

Examples

• diffusion equations  
• diffusion-reaction equations  
• convection-diffusion equations  
• pressure evolution equations  

Example equations

∂p_A/∂t = D_eff ∂²p_A/∂x²

∂C_A/∂t = D_eff ∂²C_A/∂x² − r

These are the **core transport equations** and must be classified as
transport_model.

------------------------------------------------------------
2. Transport Variables
------------------------------------------------------------

Statements defining gas-phase precursor variables.

Examples

• gas-phase pressure p_A  
• gas-phase concentration C_A  
• number density n_A  
• precursor flux F  

Example sentences

"The precursor partial pressure p_A decreases along the channel."

"The concentration C_A is used as the transport variable."

------------------------------------------------------------
3. Diffusion Models
------------------------------------------------------------

Statements describing the diffusion mechanism used in the model.

Examples

• molecular diffusion  
• Knudsen diffusion  
• Bosanquet diffusion  
• effective diffusion coefficient  

Example sentences

"The effective diffusion coefficient is given by the Bosanquet formula."

"The Knudsen diffusion coefficient depends on pore radius."

Example equations

D_eff = (1/D_A + 1/D_K)^(-1)

D_K = (2/3) r √(8RT / πM)

------------------------------------------------------------
4. Diffusion Coefficients
------------------------------------------------------------

Statements defining diffusion coefficients.

Examples

• molecular diffusion coefficient D_A  
• Knudsen diffusion coefficient D_K  
• effective diffusion coefficient D_eff  

Example sentence

"The effective diffusion coefficient D_eff is used in the transport equation."

------------------------------------------------------------
5. Transport Regime Indicators
------------------------------------------------------------

Statements describing parameters used to classify transport regimes.

Examples

• Knudsen number Kn  
• mean free path λ  
• pressure regime  

Example sentence

"The Knudsen number determines whether diffusion is molecular or Knudsen."

Example equation

Kn = λ / H

------------------------------------------------------------
6. Spatial Coordinates
------------------------------------------------------------

Statements defining spatial variables used in the transport model.

Examples

• axial coordinate x  
• radial coordinate r  
• spatial position along the feature  

Example sentence

"x represents the position along the channel."

------------------------------------------------------------
7. Boundary Conditions
------------------------------------------------------------

Statements describing transport boundary conditions.

Examples

• inlet precursor concentration  
• inlet pressure  
• wall boundary conditions  
• adsorption flux boundary condition  

Example sentences

"The inlet pressure is fixed at p0."

"The wall boundary condition corresponds to adsorption flux."

------------------------------------------------------------
8. Geometry Coupling
------------------------------------------------------------

Statements where geometry parameters are used **specifically inside
transport physics**.

Examples

• hydraulic diameter used in diffusion expressions  
• characteristic length used in Knudsen number  

Example

"Kn = λ / H"

Here **H is used in a transport equation**, therefore the segment is
transport-related.

------------------------------------------------------------
9. Transport Assumptions
------------------------------------------------------------

Statements describing assumptions about transport physics.

Examples

• isothermal diffusion  
• constant diffusion coefficient  
• molecular flow assumption  
• steady-state transport  

Example sentence

"The diffusion coefficient is assumed constant."

------------------------------------------------------------
10. Numerical or Analytical Solution Methods
------------------------------------------------------------

Statements describing how the transport equation is solved.

Examples

• analytical solution  
• numerical solution  
• reduced models  

Example sentence

"The diffusion equation is solved numerically."

------------------------------------------------------------
Equation Segments
------------------------------------------------------------

If the segment is an equation, classify it as transport_model if it
describes:

• diffusion equations  
• transport PDEs  
• diffusion coefficients  
• Knudsen number  
• spatial derivatives of concentration or pressure  

Example

∂C/∂t = D_eff ∂²C/∂x²

This is transport_model.

------------------------------------------------------------
Classification Rule
------------------------------------------------------------

Return TRUE if the segment contains **any gas-phase transport physics**.

Return FALSE if the segment only discusses:

• surface reaction kinetics  
• adsorption models  
• sticking probabilities  
• surface coverage equations  
• geometric feature dimensions  

These belong to reaction_model or geometry_model.

------------------------------------------------------------
Output Format

Return JSON only in the following format:

{
  "results": [
    {
      "segment_id": "S00015",
      "transport_relevant": true
    },
    {
      "segment_id": "S00016",
      "transport_relevant": false
    }
  ]
}